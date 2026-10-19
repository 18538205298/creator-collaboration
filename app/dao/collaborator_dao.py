from app.dao.db import db
from app.config.settings import DB_CONFIG
from datetime import datetime, timedelta

class CollaboratorDAO:
    def get_all_collaborators(self, page=1, per_page=12, filter_params=None):
        """获取合作者列表，带分页和筛选功能"""
        offset = (page - 1) * per_page
        
        # 构建基础查询
        base_query = """
            SELECT *
            FROM collaborators
            WHERE 1=1
        """
        count_query = "SELECT COUNT(*) as count FROM collaborators WHERE 1=1"
        
        # 添加筛选条件
        params = []
        filter_conditions = []
        
        if filter_params:
            if filter_params.get('platform'):
                filter_conditions.append("platform = %s")
                params.append(filter_params['platform'])
                
            if filter_params.get('content_format'):
                filter_conditions.append("content_format = %s")
                params.append(filter_params['content_format'])
                
            if filter_params.get('content_domain'):
                filter_conditions.append("content_domain = %s")
                params.append(filter_params['content_domain'])
                
            if filter_params.get('min_followers'):
                filter_conditions.append("followers_count >= %s")
                params.append(filter_params['min_followers'])
                
            if filter_params.get('content_style'):
                filter_conditions.append("content_style = %s")
                params.append(filter_params['content_style'])
                
            if filter_params.get('keyword'):
                filter_conditions.append("(username LIKE %s OR content_domain LIKE %s)")
                params.append(f"%{filter_params['keyword']}%")
                params.append(f"%{filter_params['keyword']}%")
        
        # 添加筛选条件到查询
        if filter_conditions:
            condition_str = " AND " + " AND ".join(filter_conditions)
            base_query += condition_str
            count_query += condition_str
            
        # 添加排序和分页
        base_query += " ORDER BY followers_count DESC LIMIT %s, %s"
        
        # 查询总数
        count_result = db.fetch_one(count_query, params)
        total = count_result['count'] if count_result else 0
        
        # 添加分页参数
        query_params = params.copy()
        query_params.extend([offset, per_page])
        
        # 执行查询
        collaborators = db.fetch_all(base_query, query_params)
        
        return collaborators, total
    
    def is_favorite(self, advertiser_id, collaborator_id):
        """检查合作者是否被广告主收藏"""
        query = """
            SELECT id FROM favorites_advertiser 
            WHERE advertiser_id = %s AND collaborator_id = %s
        """
        result = db.fetch_one(query, (advertiser_id, collaborator_id))
        return True if result else False
    
    def add_favorite(self, advertiser_id, collaborator_id):
        """添加收藏记录"""
        # 先检查是否已存在收藏记录
        if self.is_favorite(advertiser_id, collaborator_id):
            return True
            
        # 不存在则添加新收藏记录
        query = """
            INSERT INTO favorites_advertiser (advertiser_id, collaborator_id, created_at)
            VALUES (%s, %s, NOW())
        """
        return db.execute(query, (advertiser_id, collaborator_id))
    
    def remove_favorite(self, advertiser_id, collaborator_id):
        """删除收藏记录"""
        query = """
            DELETE FROM favorites_advertiser 
            WHERE advertiser_id = %s AND collaborator_id = %s
        """
        return db.execute(query, (advertiser_id, collaborator_id))
    
    def record_view_history(self, advertiser_id, collaborator_id):
        """记录广告主对合作者的浏览历史"""
        # 首先检查是否已经有相同的记录
        check_query = """
            SELECT id FROM view_history_advertiser 
            WHERE advertiser_id = %s AND collaborator_id = %s
        """
        existing_record = db.fetch_one(check_query, (advertiser_id, collaborator_id))
        
        if existing_record:
            # 如果已存在记录，则更新访问时间
            update_query = """
                UPDATE view_history_advertiser 
                SET viewed_at = NOW() 
                WHERE advertiser_id = %s AND collaborator_id = %s
            """
            return db.execute(update_query, (advertiser_id, collaborator_id))
        else:
            # 如果不存在记录，则新增
            insert_query = """
                INSERT INTO view_history_advertiser (advertiser_id, collaborator_id, viewed_at)
                VALUES (%s, %s, NOW())
            """
            return db.execute(insert_query, (advertiser_id, collaborator_id))
    
    def get_favorite_collaborators(self, advertiser_id, page=1, per_page=12):
        """获取广告主收藏的合作者"""
        offset = (page - 1) * per_page
        
        query = """
            SELECT c.*
            FROM collaborators c
            JOIN favorites_advertiser f ON c.id = f.collaborator_id
            WHERE f.advertiser_id = %s
            ORDER BY f.created_at DESC
            LIMIT %s, %s
        """
        
        count_query = """
            SELECT COUNT(*) as count
            FROM favorites_advertiser
            WHERE advertiser_id = %s
        """
        
        count_result = db.fetch_one(count_query, (advertiser_id,))
        total = count_result['count'] if count_result else 0
        
        collaborators = db.fetch_all(query, (advertiser_id, offset, per_page))
        
        return collaborators, total
    
    def get_view_history(self, advertiser_id, page=1, per_page=12):
        """获取广告主的合作者浏览历史"""
        offset = (page - 1) * per_page
        
        query = """
            SELECT c.*, vh.viewed_at as last_viewed_at
            FROM view_history_advertiser vh
            JOIN collaborators c ON vh.collaborator_id = c.id
            WHERE vh.advertiser_id = %s
            ORDER BY vh.viewed_at DESC
            LIMIT %s, %s
        """
        
        return db.fetch_all(query, (advertiser_id, offset, per_page))
    
    def count_favorite_collaborators(self, advertiser_id):
        """获取广告主收藏的合作者总数"""
        count_query = """
            SELECT COUNT(*) as count
            FROM favorites_advertiser
            WHERE advertiser_id = %s
        """
        
        count_result = db.fetch_one(count_query, (advertiser_id,))
        return count_result['count'] if count_result else 0
    
    def count_view_history(self, advertiser_id):
        """获取广告主浏览历史的总数"""
        count_query = """
            SELECT COUNT(*) as count
            FROM view_history_advertiser
            WHERE advertiser_id = %s
        """
        
        count_result = db.fetch_one(count_query, (advertiser_id,))
        return count_result['count'] if count_result else 0
    
    def get_user_favorite_collaborator_ids(self, advertiser_id):
        """获取广告主收藏的所有合作者ID列表"""
        query = """
            SELECT collaborator_id FROM favorites_advertiser 
            WHERE advertiser_id = %s
        """
        results = db.fetch_all(query, (advertiser_id,))
        return [row['collaborator_id'] for row in results] if results else []

    @staticmethod
    def get_collaborator_by_id(collaborator_id):
        """根据ID获取合作者信息"""
        try:
            sql = """
                SELECT * FROM collaborators
                WHERE id = %s
            """
            result = db.fetch_one(sql, (collaborator_id,))
            return result
        except Exception as e:
            print(f"获取合作者信息出错: {str(e)}")
            return None
    
    @staticmethod
    def get_collaborator_by_username(username):
        """根据用户名获取合作者信息"""
        try:
            sql = """
                SELECT * FROM collaborators
                WHERE username = %s
            """
            result = db.fetch_one(sql, (username,))
            return result
        except Exception as e:
            print(f"通过用户名获取合作者信息出错: {str(e)}")
            return None
    
    @staticmethod
    def authenticate(username, password):
        """合作者登录认证"""
        try:
            sql = """
                SELECT * FROM collaborators
                WHERE username = %s AND password = %s
            """
            result = db.fetch_one(sql, (username, password))
            return result
        except Exception as e:
            print(f"合作者登录认证出错: {str(e)}")
            return None
    
    @staticmethod
    def update_last_login(collaborator_id):
        """更新合作者最后登录时间"""
        try:
            sql = """
                UPDATE collaborators
                SET last_login = NOW()
                WHERE id = %s
            """
            db.execute(sql, (collaborator_id,))
            return True
        except Exception as e:
            print(f"更新合作者登录时间出错: {str(e)}")
            return False
    
    @staticmethod
    def update_collaborator_profile(collaborator_id, profile_data):
        """更新合作者个人资料"""
        try:
            set_clause = ", ".join([f"{key} = %s" for key in profile_data.keys()])
            values = list(profile_data.values())
            values.append(collaborator_id)
            
            sql = f"""
                UPDATE collaborators
                SET {set_clause}
                WHERE id = %s
            """
            
            db.execute(sql, tuple(values))
            return True
        except Exception as e:
            print(f"更新合作者资料出错: {str(e)}")
            return False
    
    @staticmethod
    def get_collaborators_by_filters(filters, limit=20, offset=0):
        """根据筛选条件获取合作者列表"""
        try:
            conditions = []
            params = []
            
            if filters.get('platform'):
                conditions.append("platform = %s")
                params.append(filters['platform'])
            
            if filters.get('content_domain'):
                conditions.append("content_domain = %s")
                params.append(filters['content_domain'])
            
            if filters.get('content_format'):
                conditions.append("content_format = %s")
                params.append(filters['content_format'])
            
            if filters.get('content_style'):
                conditions.append("content_style = %s")
                params.append(filters['content_style'])
            
            if filters.get('min_followers'):
                conditions.append("followers_count >= %s")
                params.append(filters['min_followers'])
            
            if filters.get('search_keyword'):
                conditions.append("(username LIKE %s OR platform LIKE %s)")
                keyword = f"%{filters['search_keyword']}%"
                params.extend([keyword, keyword])
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 按照粉丝数量降序排序
            sql = f"""
                SELECT * FROM collaborators
                WHERE {where_clause}
                ORDER BY followers_count DESC
                LIMIT %s OFFSET %s
            """
            
            params.extend([limit, offset])
            results = db.fetch_all(sql, tuple(params))
            return results
        except Exception as e:
            print(f"筛选合作者列表出错: {str(e)}")
            return []

    @staticmethod
    def get_all_collaborators():
        """获取所有合作者列表（管理员API使用）"""
        try:
            sql = "SELECT * FROM collaborators ORDER BY id ASC"
            return db.fetch_all(sql)
        except Exception as e:
            print(f"获取所有合作者出错: {str(e)}")
            return []
            
    @staticmethod
    def update_collaborator(collaborator_id, data):
        """更新合作者信息（管理员API使用）"""
        try:
            # 构建SET子句和参数列表
            set_parts = []
            params = []
            
            # 处理常规字段
            for key, value in data.items():
                if key != 'password':  # 密码字段单独处理
                    set_parts.append(f"{key} = %s")
                    params.append(value)
            
            # 处理密码字段（如果提供的话）
            if 'password' in data and data['password']:
                set_parts.append("password = %s")
                params.append(data['password'])
            
            # 没有要更新的字段
            if not set_parts:
                return False
                
            # 完成SQL语句并添加collaborator_id
            set_clause = ", ".join(set_parts)
            params.append(collaborator_id)
            
            sql = f"""
                UPDATE collaborators
                SET {set_clause}
                WHERE id = %s
            """
            
            db.execute(sql, tuple(params))
            return True
        except Exception as e:
            print(f"更新合作者信息出错: {str(e)}")
            return False
    
    @staticmethod
    def delete_collaborator(collaborator_id):
        """删除合作者（管理员API使用）"""
        try:
            sql = "DELETE FROM collaborators WHERE id = %s"
            db.execute(sql, (collaborator_id,))
            return True
        except Exception as e:
            print(f"删除合作者出错: {str(e)}")
            return False

    @staticmethod
    def get_collaborators_count():
        """获取合作者总数"""
        try:
            sql = "SELECT COUNT(*) as count FROM collaborators"
            result = db.fetch_one(sql)
            return result['count'] if result else 0
        except Exception as e:
            print(f"获取合作者总数出错: {str(e)}")
            return 0
    
    @staticmethod
    def get_active_collaborators_count(days=30):
        """获取指定天数内活跃的合作者数量"""
        try:
            date_threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            sql = """
                SELECT COUNT(*) as count FROM collaborators
                WHERE last_login >= %s
            """
            result = db.fetch_one(sql, (date_threshold,))
            return result['count'] if result else 0
        except Exception as e:
            print(f"获取活跃合作者数量出错: {str(e)}")
            return 0
    
    @staticmethod
    def get_new_collaborators_count(days=30):
        """获取指定天数内新增的合作者数量"""
        try:
            date_threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            sql = """
                SELECT COUNT(*) as count FROM collaborators
                WHERE created_at >= %s
            """
            result = db.fetch_one(sql, (date_threshold,))
            return result['count'] if result else 0
        except Exception as e:
            print(f"获取新增合作者数量出错: {str(e)}")
            return 0
    
    @staticmethod
    def get_monthly_growth(months=12):
        """获取过去N个月的合作者增长数据"""
        try:
            growth_data = []
            current_date = datetime.now()
            for i in range(months):
                # 计算每个月的开始和结束日期
                end_date = (current_date - timedelta(days=30*i)).strftime('%Y-%m-%d 23:59:59')
                start_date = (current_date - timedelta(days=30*(i+1))).strftime('%Y-%m-%d 00:00:00')
                
                sql = """
                    SELECT COUNT(*) as count FROM collaborators
                    WHERE created_at BETWEEN %s AND %s
                """
                result = db.fetch_one(sql, (start_date, end_date))
                growth_data.insert(0, result['count'] if result else 0)
            
            return growth_data
        except Exception as e:
            print(f"获取合作者月增长数据出错: {str(e)}")
            return [0] * months
    
    @staticmethod
    def get_platform_distribution():
        """获取合作者平台分布数据"""
        try:
            sql = """
                SELECT platform, COUNT(*) as count 
                FROM collaborators 
                WHERE platform IS NOT NULL AND platform != ''
                GROUP BY platform 
                ORDER BY count DESC
            """
            results = db.fetch_all(sql)
            return results
        except Exception as e:
            print(f"获取合作者平台分布数据出错: {str(e)}")
            return []
    
    @staticmethod
    def get_follower_distribution(ranges):
        """获取合作者粉丝数范围分布"""
        try:
            result_data = []
            
            for range_item in ranges:
                min_value = range_item['min']
                max_value = range_item['max']
                
                if max_value == float('inf'):
                    sql = """
                        SELECT COUNT(*) as count FROM collaborators
                        WHERE followers_count > %s
                    """
                    result = db.fetch_one(sql, (min_value,))
                else:
                    sql = """
                        SELECT COUNT(*) as count FROM collaborators
                        WHERE followers_count > %s AND followers_count <= %s
                    """
                    result = db.fetch_one(sql, (min_value, max_value))
                
                result_data.append({
                    'name': range_item['name'],
                    'count': result['count'] if result else 0
                })
            
            return result_data
        except Exception as e:
            print(f"获取合作者粉丝数分布数据出错: {str(e)}")
            return [{'name': r['name'], 'count': 0} for r in ranges]
    
    @staticmethod
    def get_content_domain_distribution():
        """获取合作者内容领域分布数据"""
        try:
            sql = """
                SELECT content_domain, COUNT(*) as count 
                FROM collaborators 
                WHERE content_domain IS NOT NULL AND content_domain != ''
                GROUP BY content_domain 
                ORDER BY count DESC
            """
            results = db.fetch_all(sql)
            return results
        except Exception as e:
            print(f"获取合作者内容领域分布数据出错: {str(e)}")
            return []
    
    @staticmethod
    def get_daily_activity(days=7):
        """获取过去N天的合作者活跃度数据"""
        try:
            activity_data = []
            
            # 假设我们使用的是登录记录作为活跃度指标
            # 实际应用中，可能需要使用专门的用户活动日志表
            current_date = datetime.now()
            
            for i in range(days):
                day = (current_date - timedelta(days=i)).strftime('%Y-%m-%d')
                day_start = f"{day} 00:00:00"
                day_end = f"{day} 23:59:59"
                
                sql = """
                    SELECT COUNT(DISTINCT id) as count FROM collaborators
                    WHERE last_login BETWEEN %s AND %s
                """
                result = db.fetch_one(sql, (day_start, day_end))
                # 将结果添加到列表开头，使最早的日期在前
                activity_data.insert(0, result['count'] if result else 0)
            
            return activity_data
        except Exception as e:
            print(f"获取合作者活跃度数据出错: {str(e)}")
            return [0] * days

collaborator_dao = CollaboratorDAO() 