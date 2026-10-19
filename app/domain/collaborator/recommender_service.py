from app.dao.collaborator_dao import CollaboratorDAO
from app.dao.advertiser_dao import AdvertiserDAO
from app.dao.ad_tasks_dao import AdTasksDAO
from app.dao.collaboration_requests_dao import CollaborationRequestsDAO
import random
import math

class CollaboratorRecommenderService:
    """合作者的广告任务推荐服务"""
    
    def __init__(self):
        self.collaborator_dao = CollaboratorDAO()
        self.advertiser_dao = AdvertiserDAO()
        self.ad_tasks_dao = AdTasksDAO()
        self.collaboration_requests_dao = CollaborationRequestsDAO()
        
        # 推荐算法权重参数
        self.weights = {
            'budget': 0.30,           # 预算权重
            'recency': 0.20,          # 发布时间新鲜度权重
            'domain_match': 0.25,     # 领域匹配度权重
            'format_match': 0.15,     # 内容格式匹配度权重
            'style_match': 0.10,      # 内容风格匹配度权重
        }
    
    def get_recommended_tasks(self, collaborator_id, limit=10):
        """
        为合作者推荐合适的广告任务
        
        推荐算法基于加权和模型，考虑以下几个因素：
        1. 内容领域匹配度（合作者的内容领域与任务要求的目标受众匹配）
        2. 内容格式匹配度（合作者的内容形式与任务要求的内容格式匹配）
        3. 内容风格匹配度（合作者的内容风格与任务要求的风格匹配）
        4. 任务预算（更高预算的任务优先）
        5. 发布时间（更新的任务优先）
        6. 排除已经收藏的任务和已经申请的任务
        
        返回推荐的任务列表
        """
        try:
            # 获取合作者信息
            collaborator = self.collaborator_dao.get_collaborator_by_id(collaborator_id)
            if not collaborator:
                print(f"合作者 ID {collaborator_id} 不存在，使用备用方案")
                return self._get_fallback_tasks(limit)
            
            # 获取合作者已收藏的任务ID列表
            try:
                favorite_task_ids = self.ad_tasks_dao.get_user_favorite_task_ids(collaborator_id)
            except Exception as e:
                print(f"获取收藏任务ID列表出错: {str(e)}")
                favorite_task_ids = []
            
            # 获取合作者已申请的任务ID列表
            try:
                applied_task_ids = self.collaboration_requests_dao.get_applied_task_ids(collaborator_id)
            except Exception as e:
                print(f"获取已申请任务ID列表出错: {str(e)}")
                applied_task_ids = []
            
            # 合并要排除的任务ID列表
            excluded_ids = list(set(favorite_task_ids + applied_task_ids))
            
            # 提取合作者的内容特征
            content_format = collaborator.get('content_format')
            content_style = collaborator.get('content_style')
            content_domain = collaborator.get('content_domain')
            
            # 获取候选任务
            try:
                # 获取足够多的候选任务
                base_query = """
                    SELECT at.*, a.username as advertiser_name, a.company_name, a.avatar_url as advertiser_avatar
                    FROM ad_tasks at
                    JOIN advertisers a ON at.advertiser_id = a.id
                    WHERE at.status = 'published'
                """
                
                params = []
                
                # 排除已收藏和已申请的任务
                if excluded_ids:
                    placeholders = ', '.join(['%s'] * len(excluded_ids))
                    base_query += f" AND at.id NOT IN ({placeholders})"
                    params.extend(excluded_ids)
                
                # 先按预算和新鲜度排序，获取更多候选
                base_query += """
                    ORDER BY at.budget DESC, at.created_at DESC
                    LIMIT %s
                """
                
                # 获取3倍的候选数量，后面会进行加权排序
                params.append(limit * 3)
                
                from app.dao.db import db
                candidate_tasks = db.fetch_all(base_query, tuple(params))
                
                if not candidate_tasks:
                    print("没有找到候选任务，使用备用方案")
                    return self._get_fallback_tasks(limit)
                
                # 计算每个任务的推荐分数
                scored_tasks = []
                max_budget = max(task.get('budget', 0) for task in candidate_tasks)
                
                # 获取最新的发布时间和最早的发布时间，用于归一化时间差
                from datetime import datetime
                now = datetime.now()
                
                # 将字符串时间转换为datetime对象
                task_dates = []
                for task in candidate_tasks:
                    if task.get('created_at'):
                        created_at = task['created_at']
                        if isinstance(created_at, str):
                            try:
                                created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                            except:
                                created_at = now
                        task_dates.append(created_at)
                
                # 如果没有有效的日期，使用当前时间
                if not task_dates:
                    oldest_date = now
                else:
                    oldest_date = min(task_dates)
                
                # 计算时间跨度（天数）
                time_span = max(1, (now - oldest_date).days)
                
                for task in candidate_tasks:
                    score = self._calculate_task_score(
                        task,
                        max_budget,
                        now,
                        time_span,
                        content_format,
                        content_style,
                        content_domain
                    )
                    task['recommendation_score'] = score
                    scored_tasks.append(task)
                
                # 按推荐分数排序
                scored_tasks.sort(key=lambda x: x.get('recommendation_score', 0), reverse=True)
                
                # 引入一定的随机性，从前20%的候选中随机选择一部分
                top_percentage = max(3, int(len(scored_tasks) * 0.2))
                top_candidates = scored_tasks[:top_percentage]
                
                if len(top_candidates) > limit:
                    # 随机排序前几名
                    random.shuffle(top_candidates)
                    result = top_candidates[:limit]
                else:
                    # 如果前几名不足，则补充其他排序后的结果
                    result = top_candidates + scored_tasks[top_percentage:limit-len(top_candidates)]
                
                return result[:limit]
                
            except Exception as e:
                print(f"加权推荐算法出错: {str(e)}")
                return self._get_fallback_tasks(limit)
            
        except Exception as e:
            print(f"推荐任务主流程出错: {str(e)}")
            return self._get_fallback_tasks(limit)
    
    def _calculate_task_score(self, task, max_budget, current_time, time_span, user_format, user_style, user_domain):
        """
        计算任务的推荐分数
        
        使用加权和模型计算:
        score = w1*norm(budget) + w2*recency + w3*domain_match + w4*format_match + w5*style_match
        
        其中，norm表示归一化，将各个指标都缩放到[0,1]区间
        """
        try:
            # 1. 预算得分 - 归一化处理
            budget_score = min(1.0, (task.get('budget', 0) / max_budget)) if max_budget > 0 else 0
            
            # 2. 时间新鲜度得分 - 基于发布时间
            recency_score = 0.0
            if task.get('created_at'):
                created_at = task['created_at']
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    except:
                        from datetime import datetime
                        created_at = current_time
                
                # 计算发布时间距今的天数
                days_since_created = max(0, (current_time - created_at).days)
                # 根据时间跨度归一化，越新的任务分数越高
                recency_score = max(0, 1 - (days_since_created / time_span))
            
            # 3. 领域匹配度得分
            domain_match_score = 0.0
            if user_domain and task.get('target_audience'):
                # 简单文本匹配
                if user_domain.lower() in task['target_audience'].lower():
                    domain_match_score = 1.0
                else:
                    # 关键词匹配，检查是否有部分匹配
                    user_keywords = set(k.strip().lower() for k in user_domain.split(','))
                    target_keywords = set(k.strip().lower() for k in task['target_audience'].split(','))
                    
                    if user_keywords and target_keywords:
                        matches = user_keywords.intersection(target_keywords)
                        if matches:
                            domain_match_score = len(matches) / len(user_keywords)
                        else:
                            # 尝试部分字符串匹配
                            partial_matches = 0
                            for uk in user_keywords:
                                for tk in target_keywords:
                                    if uk in tk or tk in uk:
                                        partial_matches += 1
                                        break
                            if partial_matches > 0:
                                domain_match_score = 0.5 * (partial_matches / len(user_keywords))
            
            # 4. 内容格式匹配度得分
            format_match_score = 0.0
            if user_format and task.get('content_format'):
                if user_format.lower() == task['content_format'].lower():
                    format_match_score = 1.0
            
            # 5. 内容风格匹配度得分
            style_match_score = 0.0
            if user_style and task.get('content_style'):
                if user_style.lower() in task['content_style'].lower() or task['content_style'].lower() in user_style.lower():
                    style_match_score = 1.0
                else:
                    # 关键词匹配
                    user_keywords = set(k.strip().lower() for k in user_style.split(','))
                    task_keywords = set(k.strip().lower() for k in task['content_style'].split(','))
                    
                    if user_keywords and task_keywords:
                        matches = user_keywords.intersection(task_keywords)
                        if matches:
                            style_match_score = len(matches) / len(user_keywords)
            
            # 应用权重计算加权和
            final_score = (
                self.weights['budget'] * budget_score +
                self.weights['recency'] * recency_score +
                self.weights['domain_match'] * domain_match_score +
                self.weights['format_match'] * format_match_score +
                self.weights['style_match'] * style_match_score
            )
            
            # 加入少量随机因素，打破相似分数的任务排序
            final_score += random.uniform(0, 0.05)
            
            return final_score
            
        except Exception as e:
            print(f"计算任务推荐分数出错: {str(e)}")
            # 出错时返回随机低分，确保这个任务排名靠后
            return random.uniform(0, 0.1)
    
    def _get_fallback_tasks(self, limit=5):
        """获取备用的任务列表（当推荐算法出错时使用）"""
        print("使用备用方案获取任务")
        try:
            # 尝试获取预算最高的任务作为备用
            query = """
                SELECT at.*, a.username as advertiser_name, a.company_name, a.avatar_url as advertiser_avatar
                FROM ad_tasks at
                JOIN advertisers a ON at.advertiser_id = a.id
                WHERE at.status = 'published'
                ORDER BY at.budget DESC, at.created_at DESC
                LIMIT %s
            """
            
            from app.dao.db import db
            tasks = db.fetch_all(query, (limit,))
            if tasks:
                return tasks
        except Exception as e:
            print(f"备用方案1出错: {str(e)}")
        
        # 如果数据库查询也失败，返回模拟数据
        print("返回模拟数据")
        mock_tasks = []
        for i in range(limit):
            mock_tasks.append({
                'id': i + 1,
                'title': f'模拟广告任务{i+1}',
                'description': '这是一个自动生成的模拟广告任务，用于测试推荐系统功能。',
                'budget': 3000.00 + i * 1000.00,
                'advertiser_name': f'模拟广告主{i+1}',
                'company_name': '模拟公司',
                'advertiser_avatar': None,
                'applications_count': 5 + i,
                'views_count': 50 + i * 10
            })
        return mock_tasks
    
    def get_trending_tasks(self, limit=5):
        """获取热门趋势任务（申请数和浏览数较高的任务）"""
        try:
            # 计算热度得分 = 申请数*5 + 浏览数
            query = """
                SELECT at.*, a.username as advertiser_name, a.company_name, a.avatar_url as advertiser_avatar,
                       (at.applications_count * 5 + at.views_count) AS popularity_score
                FROM ad_tasks at
                JOIN advertisers a ON at.advertiser_id = a.id
                WHERE at.status = 'published'
                ORDER BY popularity_score DESC, at.created_at DESC
                LIMIT %s
            """
            
            from app.dao.db import db
            tasks = db.fetch_all(query, (limit,))
            if tasks:
                return tasks
            else:
                return self._get_fallback_tasks(limit)
        except Exception as e:
            print(f"获取热门任务出错: {str(e)}")
            return self._get_fallback_tasks(limit)
    
    def get_high_budget_tasks(self, limit=5):
        """获取高预算任务"""
        try:
            query = """
                SELECT at.*, a.username as advertiser_name, a.company_name, a.avatar_url as advertiser_avatar
                FROM ad_tasks at
                JOIN advertisers a ON at.advertiser_id = a.id
                WHERE at.status = 'published'
                ORDER BY at.budget DESC, at.created_at DESC
                LIMIT %s
            """
            
            from app.dao.db import db
            tasks = db.fetch_all(query, (limit,))
            if tasks:
                return tasks
            else:
                return self._get_fallback_tasks(limit)
        except Exception as e:
            print(f"获取高预算任务出错: {str(e)}")
            return self._get_fallback_tasks(limit) 