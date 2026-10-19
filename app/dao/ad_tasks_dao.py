from app.dao.database import db
from flask_paginate import Pagination

class AdTasksDAO:
    def get_all_tasks(self, page=1, per_page=12, filter_params=None):
        """获取广告任务列表，带分页和筛选功能"""
        offset = (page - 1) * per_page
        
        # 构建基础查询
        base_query = """
            SELECT at.*, a.username as advertiser_name, a.company_name, a.avatar_url as advertiser_avatar
            FROM ad_tasks at
            JOIN advertisers a ON at.advertiser_id = a.id
            WHERE at.status = 'published'
        """
        count_query = "SELECT COUNT(*) as count FROM ad_tasks WHERE status = 'published'"
        
        # 添加筛选条件
        params = []
        filter_conditions = []
        
        if filter_params:
            if filter_params.get('platform'):
                filter_conditions.append("platform_requirements LIKE %s")
                params.append(f"%{filter_params['platform']}%")
                
            if filter_params.get('content_format'):
                filter_conditions.append("content_format = %s")
                params.append(filter_params['content_format'])
                
            if filter_params.get('content_domain'):
                filter_conditions.append("target_audience LIKE %s")
                params.append(f"%{filter_params['content_domain']}%")
                
            if filter_params.get('min_budget'):
                filter_conditions.append("budget >= %s")
                params.append(filter_params['min_budget'])
                
            if filter_params.get('content_style'):
                filter_conditions.append("content_style = %s")
                params.append(filter_params['content_style'])
                
            if filter_params.get('keyword'):
                filter_conditions.append("(title LIKE %s OR description LIKE %s)")
                params.append(f"%{filter_params['keyword']}%")
                params.append(f"%{filter_params['keyword']}%")
        
        # 添加筛选条件到查询
        if filter_conditions:
            condition_str = " AND " + " AND ".join(filter_conditions)
            base_query += condition_str
            count_query += condition_str
            
        # 添加排序和分页
        base_query += " ORDER BY created_at DESC LIMIT %s, %s"
        
        # 查询总数
        count_result = db.execute_one(count_query, params)
        total = count_result['count'] if count_result else 0
        
        # 添加分页参数
        query_params = params.copy()
        query_params.extend([offset, per_page])
        
        # 执行查询
        tasks = db.execute_query(base_query, query_params)
        
        return tasks, total
    
    def get_task_by_id(self, task_id):
        """根据ID获取广告任务详情"""
        query = """
            SELECT at.*, a.username as advertiser_name, a.company_name, a.avatar_url as advertiser_avatar
            FROM ad_tasks at
            JOIN advertisers a ON at.advertiser_id = a.id
            WHERE at.id = %s
        """
        return db.execute_one(query, (task_id,))
    
    def increment_views_count(self, task_id):
        """增加任务的浏览次数"""
        query = "UPDATE ad_tasks SET views_count = views_count + 1 WHERE id = %s"
        return db.execute(query, (task_id,))
    
    def get_hot_tasks(self, limit=6):
        """获取热门任务（按申请数和浏览数排序）"""
        query = """
            SELECT at.*, a.username as advertiser_name, a.company_name
            FROM ad_tasks at
            JOIN advertisers a ON at.advertiser_id = a.id
            WHERE at.status = 'published'
            ORDER BY at.applications_count DESC, at.views_count DESC, at.created_at DESC
            LIMIT %s
        """
        return db.execute_query(query, (limit,))
    
    def get_latest_tasks(self, limit=6):
        """获取最新发布的任务"""
        query = """
            SELECT at.*, a.username as advertiser_name, a.company_name
            FROM ad_tasks at
            JOIN advertisers a ON at.advertiser_id = a.id
            WHERE at.status = 'published'
            ORDER BY at.created_at DESC
            LIMIT %s
        """
        return db.execute_query(query, (limit,))
    
    def get_favorite_tasks(self, collaborator_id, page=1, per_page=12):
        """获取用户收藏的任务"""
        offset = (page - 1) * per_page
        
        query = """
            SELECT at.*, a.username as advertiser_name, a.company_name, a.avatar_url as advertiser_avatar
            FROM ad_tasks at
            JOIN advertisers a ON at.advertiser_id = a.id
            JOIN favorites f ON at.id = f.ad_task_id
            WHERE f.collaborator_id = %s
            ORDER BY f.created_at DESC
            LIMIT %s, %s
        """
        
        count_query = """
            SELECT COUNT(*) as count
            FROM favorites
            WHERE collaborator_id = %s
        """
        
        count_result = db.execute_one(count_query, (collaborator_id,))
        total = count_result['count'] if count_result else 0
        
        tasks = db.execute_query(query, (collaborator_id, offset, per_page))
        
        return tasks, total
    
    def count_tasks(self, filter_params=None):
        """获取广告任务总数（含筛选条件）#支持通用分页组件"""
        # 构建基础查询
        count_query = "SELECT COUNT(*) as count FROM ad_tasks WHERE status = 'published'"
        
        # 添加筛选条件
        params = []
        filter_conditions = []
        
        if filter_params:
            if filter_params.get('platform'):
                filter_conditions.append("platform_requirements LIKE %s")
                params.append(f"%{filter_params['platform']}%")
                
            if filter_params.get('content_format'):
                filter_conditions.append("content_format = %s")
                params.append(filter_params['content_format'])
                
            if filter_params.get('content_domain'):
                filter_conditions.append("target_audience LIKE %s")
                params.append(f"%{filter_params['content_domain']}%")
                
            if filter_params.get('min_budget'):
                filter_conditions.append("budget >= %s")
                params.append(filter_params['min_budget'])
                
            if filter_params.get('content_style'):
                filter_conditions.append("content_style = %s")
                params.append(filter_params['content_style'])
                
            if filter_params.get('keyword'):
                filter_conditions.append("(title LIKE %s OR description LIKE %s)")
                params.append(f"%{filter_params['keyword']}%")
                params.append(f"%{filter_params['keyword']}%")
        
        # 添加筛选条件到查询
        if filter_conditions:
            condition_str = " AND " + " AND ".join(filter_conditions)
            count_query += condition_str
            
        # 查询总数
        count_result = db.execute_one(count_query, params)
        return count_result['count'] if count_result else 0
    
    def get_tasks_by_page(self, page, per_page, filter_params=None):
        """获取指定页的广告任务列表#支持通用分页组件"""
        offset = (page - 1) * per_page
        
        # 构建基础查询
        base_query = """
            SELECT at.*, a.username as advertiser_name, a.company_name, a.avatar_url as advertiser_avatar
            FROM ad_tasks at
            JOIN advertisers a ON at.advertiser_id = a.id
            WHERE at.status = 'published'
        """
        
        # 添加筛选条件
        params = []
        filter_conditions = []
        
        if filter_params:
            if filter_params.get('platform'):
                filter_conditions.append("platform_requirements LIKE %s")
                params.append(f"%{filter_params['platform']}%")
                
            if filter_params.get('content_format'):
                filter_conditions.append("content_format = %s")
                params.append(filter_params['content_format'])
                
            if filter_params.get('content_domain'):
                filter_conditions.append("target_audience LIKE %s")
                params.append(f"%{filter_params['content_domain']}%")
                
            if filter_params.get('min_budget'):
                filter_conditions.append("budget >= %s")
                params.append(filter_params['min_budget'])
                
            if filter_params.get('content_style'):
                filter_conditions.append("content_style = %s")
                params.append(filter_params['content_style'])
                
            if filter_params.get('keyword'):
                filter_conditions.append("(title LIKE %s OR description LIKE %s)")
                params.append(f"%{filter_params['keyword']}%")
                params.append(f"%{filter_params['keyword']}%")
        
        # 添加筛选条件到查询
        if filter_conditions:
            condition_str = " AND " + " AND ".join(filter_conditions)
            base_query += condition_str
            
        # 添加排序和分页
        base_query += " ORDER BY created_at DESC LIMIT %s, %s"
        
        # 添加分页参数
        query_params = params.copy()
        query_params.extend([offset, per_page])
        
        # 执行查询
        return db.execute_query(base_query, query_params)
    
    def count_favorite_tasks(self, collaborator_id):
        """获取用户收藏的任务总数#支持通用分页组件"""
        count_query = """
            SELECT COUNT(*) as count
            FROM favorites_collaborator
            WHERE collaborator_id = %s
        """
        
        count_result = db.execute_one(count_query, (collaborator_id,))
        return count_result['count'] if count_result else 0
    
    def get_favorite_tasks_by_page(self, collaborator_id, page, per_page):
        """获取用户指定页的收藏任务#支持通用分页组件"""
        offset = (page - 1) * per_page
        
        query = """
            SELECT at.*, a.username as advertiser_name, a.company_name, a.avatar_url as advertiser_avatar
            FROM ad_tasks at
            JOIN advertisers a ON at.advertiser_id = a.id
            JOIN favorites_collaborator f ON at.id = f.task_id
            WHERE f.collaborator_id = %s
            ORDER BY f.created_at DESC
            LIMIT %s, %s
        """
        
        return db.execute_query(query, (collaborator_id, offset, per_page))
    
    def record_view_history(self, collaborator_id, task_id):
        """记录用户的任务浏览历史"""
        # 首先检查是否已经有相同的记录
        check_query = """
            SELECT id FROM view_history_collaborator 
            WHERE collaborator_id = %s AND task_id = %s
        """
        existing_record = db.execute_one(check_query, (collaborator_id, task_id))
        
        if existing_record:
            # 如果已存在记录，则更新访问时间
            update_query = """
                UPDATE view_history_collaborator 
                SET viewed_at = NOW() 
                WHERE collaborator_id = %s AND task_id = %s
            """
            return db.execute(update_query, (collaborator_id, task_id))
        else:
            # 如果不存在记录，则新增
            insert_query = """
                INSERT INTO view_history_collaborator (collaborator_id, task_id, viewed_at)
                VALUES (%s, %s, NOW())
            """
            return db.execute(insert_query, (collaborator_id, task_id))
    
    def is_favorite(self, collaborator_id, task_id):
        """检查任务是否被用户收藏"""
        query = """
            SELECT id FROM favorites_collaborator 
            WHERE collaborator_id = %s AND task_id = %s
        """
        result = db.execute_one(query, (collaborator_id, task_id))
        return True if result else False
    
    def add_favorite(self, collaborator_id, task_id):
        """添加收藏记录"""
        # 先检查是否已存在收藏记录
        if self.is_favorite(collaborator_id, task_id):
            return True
            
        # 不存在则添加新收藏记录
        query = """
            INSERT INTO favorites_collaborator (collaborator_id, task_id, created_at)
            VALUES (%s, %s, NOW())
        """
        return db.execute(query, (collaborator_id, task_id))
    
    def remove_favorite(self, collaborator_id, task_id):
        """删除收藏记录"""
        query = """
            DELETE FROM favorites_collaborator 
            WHERE collaborator_id = %s AND task_id = %s
        """
        return db.execute(query, (collaborator_id, task_id))
    
    def get_view_history(self, collaborator_id, page=1, per_page=12):
        """获取用户的任务浏览历史"""
        offset = (page - 1) * per_page
        
        query = """
            SELECT at.*, a.username as advertiser_name, a.company_name, a.avatar_url as advertiser_avatar,
                  vh.viewed_at as last_viewed_at
            FROM view_history_collaborator vh
            JOIN ad_tasks at ON vh.task_id = at.id
            JOIN advertisers a ON at.advertiser_id = a.id
            WHERE vh.collaborator_id = %s
            ORDER BY vh.viewed_at DESC
            LIMIT %s, %s
        """
        
        return db.execute_query(query, (collaborator_id, offset, per_page))
    
    def count_view_history(self, collaborator_id):
        """获取用户浏览历史的总数#支持通用分页组件"""
        count_query = """
            SELECT COUNT(*) as count
            FROM view_history_collaborator
            WHERE collaborator_id = %s
        """
        
        count_result = db.execute_one(count_query, (collaborator_id,))
        return count_result['count'] if count_result else 0
    
    def get_user_favorite_task_ids(self, collaborator_id):
        """获取用户收藏的所有任务ID列表"""
        query = """
            SELECT task_id FROM favorites_collaborator 
            WHERE collaborator_id = %s
        """
        results = db.execute_query(query, (collaborator_id,))
        return [row['task_id'] for row in results] if results else []
    
    def get_advertiser_tasks(self, advertiser_id, limit=5):
        """获取广告主发布的任务列表，用于内容分析"""
        query = """
            SELECT * FROM ad_tasks
            WHERE advertiser_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        return db.execute_query(query, (advertiser_id, limit))
        
ad_tasks_dao = AdTasksDAO() 