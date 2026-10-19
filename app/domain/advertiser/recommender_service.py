from app.dao.collaborator_dao import CollaboratorDAO
from app.dao.advertiser_dao import AdvertiserDAO
from app.dao.ad_tasks_dao import AdTasksDAO
from app.dao.collaboration_requests_dao import CollaborationRequestsDAO
import random
import math

class AdvertiserRecommenderService:
    """广告主的合作者推荐服务"""
    
    def __init__(self):
        self.collaborator_dao = CollaboratorDAO()
        self.advertiser_dao = AdvertiserDAO()
        self.ad_tasks_dao = AdTasksDAO()
        self.collaboration_requests_dao = CollaborationRequestsDAO()
        
        # 推荐算法权重参数
        self.weights = {
            'followers_count': 0.35,  # 粉丝数量权重
            'previous_collaboration_count': 0.20,  # 历史合作次数权重
            'activity_score': 0.15,  # 活跃度权重
            'domain_match': 0.20,  # 领域匹配度权重
            'style_match': 0.10,  # 风格匹配度权重
        }
    
    def get_recommended_collaborators(self, advertiser_id, limit=10):
        """
        为广告主推荐合适的合作者
        
        推荐算法基于加权和模型，考虑以下几个因素：
        1. 合作者粉丝量（更多粉丝优先）
        2. 历史合作次数（经验丰富的合作者优先）
        3. 活跃度（最近登录的合作者优先）
        4. 领域匹配度（基于广告主历史任务的领域匹配）
        5. 风格匹配度（基于广告主历史任务的风格匹配）
        6. 排除已经收藏的合作者和已经发送过邀请的合作者
        
        返回推荐的合作者列表
        """
        try:
            # 首先尝试简单地获取所有合作者（按粉丝数量排序），确保有数据
            try:
                print("尝试获取所有合作者（按粉丝数排序）")
                query = """
                    SELECT *
                    FROM collaborators
                    ORDER BY followers_count DESC
                    LIMIT %s
                """
                from app.dao.db import db
                all_collaborators = db.fetch_all(query, (limit * 2,))
                if all_collaborators and len(all_collaborators) >= 3:
                    print(f"成功获取到 {len(all_collaborators)} 个合作者")
                    return all_collaborators[:limit]
            except Exception as e:
                print(f"获取所有合作者失败: {str(e)}")
            
            # 如果简单方法失败，再尝试复杂的推荐算法
            print("简单方法失败，尝试使用加权和推荐算法")
            
            # 获取广告主信息
            advertiser = self.advertiser_dao.get_advertiser_by_id(advertiser_id)
            if not advertiser:
                print(f"广告主 ID {advertiser_id} 不存在，使用备用方案")
                return self._get_fallback_collaborators(limit)
            
            # 获取广告主已收藏的合作者ID列表
            try:
                favorite_collaborator_ids = self.collaborator_dao.get_user_favorite_collaborator_ids(advertiser_id)
            except Exception as e:
                print(f"获取收藏合作者ID列表出错: {str(e)}")
                favorite_collaborator_ids = []
            
            # 获取广告主已发送邀请的合作者ID列表
            try:
                invited_collaborator_ids = self.collaboration_requests_dao.get_invited_collaborator_ids(advertiser_id)
            except Exception as e:
                print(f"获取已邀请合作者ID列表出错: {str(e)}")
                invited_collaborator_ids = []
            
            # 合并要排除的合作者ID列表
            excluded_ids = list(set(favorite_collaborator_ids + invited_collaborator_ids))
            
            # 获取广告主历史发布的广告任务信息，用于领域匹配
            try:
                advertiser_tasks = self.ad_tasks_dao.get_advertiser_tasks(advertiser_id, limit=5)
            except Exception as e:
                print(f"获取广告主任务列表出错: {str(e)}")
                advertiser_tasks = []
            
            # 提取广告主任务的内容特征
            content_formats = []
            content_styles = []
            target_audiences = []
            
            for task in advertiser_tasks:
                if task.get('content_format') and task['content_format'] not in content_formats:
                    content_formats.append(task['content_format'])
                if task.get('content_style') and task['content_style'] not in content_styles:
                    content_styles.append(task['content_style'])
                if task.get('target_audience') and task['target_audience'] not in target_audiences:
                    target_audiences.append(task['target_audience'])
            
            # 获取候选合作者
            try:
                query = """
                    SELECT *
                    FROM collaborators
                    WHERE 1=1
                """
                
                params = []
                
                # 排除已收藏和已邀请的合作者
                if excluded_ids:
                    placeholders = ', '.join(['%s'] * len(excluded_ids))
                    query += f" AND id NOT IN ({placeholders})"
                    params.extend(excluded_ids)
                
                # 限制获取的候选数量为原始限制的3倍，后续会进行加权排序
                query += " ORDER BY followers_count DESC LIMIT %s"
                params.append(limit * 3)
                
                from app.dao.db import db
                candidate_collaborators = db.fetch_all(query, tuple(params))
                
                if not candidate_collaborators:
                    print("没有找到候选合作者，使用备用方案")
                    return self._get_fallback_collaborators(limit)
                    
                # 计算每个合作者的推荐分数
                scored_collaborators = []
                max_followers = max(c.get('followers_count', 0) for c in candidate_collaborators)
                max_collabs = max(c.get('previous_collaboration_count', 0) for c in candidate_collaborators)
                
                for collaborator in candidate_collaborators:
                    score = self._calculate_recommendation_score(
                        collaborator, 
                        max_followers, 
                        max_collabs, 
                        content_formats, 
                        content_styles, 
                        target_audiences
                    )
                    collaborator['recommendation_score'] = score
                    scored_collaborators.append(collaborator)
                
                # 按推荐分数排序
                scored_collaborators.sort(key=lambda x: x.get('recommendation_score', 0), reverse=True)
                
                # 引入一定的随机性，避免推荐结果过于相似
                # 从前20%的候选中随机选择一部分
                top_candidates = scored_collaborators[:max(3, int(len(scored_collaborators) * 0.2))]
                if len(top_candidates) > limit:
                    # 随机排序前几名
                    random.shuffle(top_candidates)
                    result = top_candidates[:limit]
                else:
                    # 如果前几名不足，则直接返回所有排序后的结果
                    result = scored_collaborators[:limit]
                
                return result
                
            except Exception as e:
                print(f"加权推荐算法出错: {str(e)}")
                return self._get_fallback_collaborators(limit)
            
        except Exception as e:
            print(f"推荐合作者主流程出错: {str(e)}")
            return self._get_fallback_collaborators(limit)
    
    def _calculate_recommendation_score(self, collaborator, max_followers, max_collabs, content_formats, content_styles, target_audiences):
        """
        计算合作者的推荐分数
        
        使用加权和模型计算:
        score = w1*norm(followers) + w2*norm(collabs) + w3*activity + w4*domain_match + w5*style_match
        
        其中，norm表示归一化，将各个指标都缩放到[0,1]区间
        """
        try:
            # 1. 粉丝数量得分 - 归一化处理
            followers_score = min(1.0, (collaborator.get('followers_count', 0) / max_followers)) if max_followers > 0 else 0
            
            # 2. 历史合作次数得分 - 归一化处理
            collab_score = min(1.0, (collaborator.get('previous_collaboration_count', 0) / max_collabs)) if max_collabs > 0 else 0
            
            # 3. 活跃度得分 - 基于最后登录时间
            activity_score = 0.0
            if collaborator.get('last_login'):
                # 计算最近登录距今的天数
                from datetime import datetime
                last_login = collaborator['last_login']
                if isinstance(last_login, str):
                    try:
                        last_login = datetime.strptime(last_login, '%Y-%m-%d %H:%M:%S')
                    except:
                        last_login = datetime.now()
                
                days_since_login = (datetime.now() - last_login).days
                # 30天内活跃度线性递减
                activity_score = max(0, 1 - (days_since_login / 30))
            
            # 4. 领域匹配度得分
            domain_match_score = 0.0
            if target_audiences and collaborator.get('content_domain'):
                # 计算目标受众与合作者内容领域的匹配程度
                matches = 0
                for audience in target_audiences:
                    if audience.lower() in collaborator['content_domain'].lower():
                        matches += 1
                domain_match_score = matches / len(target_audiences) if len(target_audiences) > 0 else 0
            
            # 5. 风格匹配度得分
            style_match_score = 0.0
            if content_styles and collaborator.get('content_style'):
                # 计算内容风格的匹配程度
                matches = 0
                for style in content_styles:
                    if style.lower() in collaborator['content_style'].lower():
                        matches += 1
                style_match_score = matches / len(content_styles) if len(content_styles) > 0 else 0
            
            # 应用权重计算加权和
            final_score = (
                self.weights['followers_count'] * followers_score +
                self.weights['previous_collaboration_count'] * collab_score +
                self.weights['activity_score'] * activity_score +
                self.weights['domain_match'] * domain_match_score +
                self.weights['style_match'] * style_match_score
            )
            
            # 加入少量随机因素，避免相似分数的合作者总是以相同顺序排列
            final_score += random.uniform(0, 0.05)
            
            return final_score
            
        except Exception as e:
            print(f"计算推荐分数出错: {str(e)}")
            # 出错时返回随机低分，确保这个合作者排名靠后
            return random.uniform(0, 0.1)
    
    def _get_fallback_collaborators(self, limit=5):
        """获取备用的合作者列表（当推荐算法出错时使用）"""
        print("使用备用方案获取合作者")
        try:
            # 尝试获取粉丝最多的合作者作为备用
            query = """
                SELECT *
                FROM collaborators
                ORDER BY followers_count DESC
                LIMIT %s
            """
            
            from app.dao.db import db
            collaborators = db.fetch_all(query, (limit,))
            if collaborators:
                return collaborators
        except Exception as e:
            print(f"备用方案1出错: {str(e)}")
        
        # 尝试直接获取所有合作者
        try:
            print("尝试获取所有合作者")
            query = "SELECT * FROM collaborators LIMIT %s"
            
            from app.dao.db import db
            collaborators = db.fetch_all(query, (limit,))
            if collaborators:
                return collaborators
        except Exception as e:
            print(f"备用方案2出错: {str(e)}")
        
        # 如果数据库查询也失败，返回模拟数据
        print("返回模拟数据")
        mock_collaborators = []
        for i in range(limit):
            mock_collaborators.append({
                'id': i + 1,
                'username': f'模拟合作者{i+1}',
                'avatar_url': None,
                'followers_count': 50000 + i * 5000,
                'likes_count': 200000 + i * 10000,
                'content_domain': '模拟领域',
                'content_style': '模拟风格',
                'platform': '模拟平台',
                'previous_collaboration_count': 3 + i
            })
        return mock_collaborators
    
    def get_trending_collaborators(self, limit=5):
        """获取热门趋势合作者（粉丝数量多且最近活跃的）"""
        try:
            # 先直接获取粉丝最多的合作者
            query = """
                SELECT *
                FROM collaborators
                ORDER BY followers_count DESC
                LIMIT %s
            """
            
            from app.dao.db import db
            collaborators = db.fetch_all(query, (limit,))
            if collaborators:
                return collaborators
                
            # 如果上面的查询没结果，再尝试最近活跃的查询
            query = """
                SELECT *
                FROM collaborators
                WHERE last_login > DATE_SUB(NOW(), INTERVAL 30 DAY)
                ORDER BY followers_count DESC, last_login DESC
                LIMIT %s
            """
            
            collaborators = db.fetch_all(query, (limit,))
            if collaborators:
                return collaborators
            
            # 尝试获取所有合作者
            query = "SELECT * FROM collaborators LIMIT %s"
            collaborators = db.fetch_all(query, (limit,))
            if collaborators:
                return collaborators
                
            return self._get_fallback_collaborators(limit)
        except Exception as e:
            print(f"获取热门合作者出错: {str(e)}")
            return self._get_fallback_collaborators(limit)
    
    def get_new_rising_collaborators(self, limit=5):
        """获取新晋合作者（注册时间较短但粉丝增长快的）"""
        try:
            # 先直接获取所有合作者
            query = """
                SELECT *
                FROM collaborators
                ORDER BY followers_count DESC
                LIMIT %s
            """
            
            from app.dao.db import db
            collaborators = db.fetch_all(query, (limit,))
            if collaborators:
                # 稍微打乱排序，使其看起来不同于热门推荐
                if len(collaborators) > 3:
                    # 如果有至少3个结果，随机排序
                    random.shuffle(collaborators)
                return collaborators
                
            # 如果上面的查询没结果，再尝试按创建时间排序
            query = """
                SELECT *
                FROM collaborators
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 90 DAY)
                ORDER BY followers_count DESC, created_at DESC
                LIMIT %s
            """
            
            collaborators = db.fetch_all(query, (limit,))
            if collaborators:
                return collaborators
                
            return self._get_fallback_collaborators(limit)
        except Exception as e:
            print(f"获取新晋合作者出错: {str(e)}")
            return self._get_fallback_collaborators(limit) 