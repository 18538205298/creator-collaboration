from app.dao.db import db
from app.config.settings import DB_CONFIG
from datetime import datetime

class AdTaskDAO:
    """广告任务数据访问对象"""

    @staticmethod
    def get_task_by_id(task_id):
        """根据ID获取任务详情"""
        try:
            sql = """
                SELECT * FROM ad_tasks
                WHERE id = %s
            """
            result = db.fetch_one(sql, (task_id,))
            return result
        except Exception as e:
            print(f"获取任务详情出错: {str(e)}")
            return None

    @staticmethod
    def get_tasks_by_advertiser(advertiser_id, status=None):
        """获取广告主的所有任务"""
        try:
            if status:
                sql = """
                    SELECT * FROM ad_tasks
                    WHERE advertiser_id = %s AND status = %s
                    ORDER BY updated_at DESC
                """
                results = db.fetch_all(sql, (advertiser_id, status))
            else:
                sql = """
                    SELECT * FROM ad_tasks
                    WHERE advertiser_id = %s
                    ORDER BY updated_at DESC
                """
                results = db.fetch_all(sql, (advertiser_id,))
            return results
        except Exception as e:
            print(f"获取广告主任务列表出错: {str(e)}")
            return []

    @staticmethod
    def get_task_collaboration(task_id):
        """获取任务的合作关系信息"""
        try:
            # 首先检查广告主发起的合作请求
            sql = """
                SELECT c.*, c.created_at as start_time, c.collaborator_id
                FROM collaboration_requests_advertiser c
                WHERE c.ad_task_id = %s AND c.status = 'accepted'
                LIMIT 1
            """
            result = db.fetch_one(sql, (task_id,))
            
            if result:
                return result
            
            # 如果没有找到广告主发起的请求，检查合作者发起的请求
            sql = """
                SELECT c.*, c.created_at as start_time, c.collaborator_id
                FROM collaboration_requests_collaborator c
                WHERE c.ad_task_id = %s AND c.status = 'accepted'
                LIMIT 1
            """
            result = db.fetch_one(sql, (task_id,))
            return result
        except Exception as e:
            print(f"获取任务合作关系出错: {str(e)}")
            return None

    @staticmethod
    def create_task(task_data):
        """创建新任务"""
        try:
            columns = ', '.join(task_data.keys())
            placeholders = ', '.join(['%s'] * len(task_data))
            
            sql = f"""
                INSERT INTO ad_tasks ({columns})
                VALUES ({placeholders})
            """
            
            task_id = db.execute(sql, tuple(task_data.values()))
            return task_id
        except Exception as e:
            print(f"创建任务出错: {str(e)}")
            return None

    @staticmethod
    def update_task_status(task_id, status, updated_at=None):
        """更新任务状态"""
        try:
            if not updated_at:
                updated_at = datetime.now()
                
            sql = """
                UPDATE ad_tasks
                SET status = %s, updated_at = %s
                WHERE id = %s
            """
            
            db.execute(sql, (status, updated_at, task_id))
            return True
        except Exception as e:
            print(f"更新任务状态出错: {str(e)}")
            return False

    @staticmethod
    def get_available_tasks(collaborator_id=None, content_format=None, content_style=None, min_budget=None, max_budget=None):
        """获取可用的广告任务列表"""
        try:
            conditions = ["status = 'published'"]
            params = []
            
            if content_format:
                conditions.append("content_format = %s")
                params.append(content_format)
                
            if content_style:
                conditions.append("content_style = %s")
                params.append(content_style)
                
            if min_budget is not None:
                conditions.append("budget >= %s")
                params.append(min_budget)
                
            if max_budget is not None:
                conditions.append("budget <= %s")
                params.append(max_budget)
                
            # 排除已经申请过的任务
            if collaborator_id:
                conditions.append("""
                    id NOT IN (
                        SELECT ad_task_id FROM collaboration_requests_collaborator 
                        WHERE collaborator_id = %s
                    )
                """)
                params.append(collaborator_id)
            
            where_clause = " AND ".join(conditions)
            
            sql = f"""
                SELECT * FROM ad_tasks
                WHERE {where_clause}
                ORDER BY created_at DESC
            """
            
            results = db.fetch_all(sql, tuple(params))
            return results
        except Exception as e:
            print(f"获取可用任务列表出错: {str(e)}")
            return []

    @staticmethod
    def get_all_tasks():
        """获取所有广告任务"""
        try:
            sql = """
                SELECT * FROM ad_tasks
                ORDER BY updated_at DESC
            """
            results = db.fetch_all(sql)
            return results
        except Exception as e:
            print(f"获取所有广告任务出错: {str(e)}")
            return []

    @staticmethod
    def get_tasks_by_status(status):
        """根据状态获取广告任务"""
        try:
            sql = """
                SELECT * FROM ad_tasks
                WHERE status = %s
                ORDER BY updated_at DESC
            """
            results = db.fetch_all(sql, (status,))
            return results
        except Exception as e:
            print(f"根据状态获取广告任务出错: {str(e)}")
            return [] 