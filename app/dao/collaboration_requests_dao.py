from app.dao.database import db
from datetime import datetime

class CollaborationRequestsDAO:
    def get_advertiser_sent_requests(self, advertiser_id):
        """获取广告主发出的合作请求"""
        query = """
            SELECT cra.*, c.username as collaborator_name, c.avatar_url as collaborator_avatar,
                   at.title as task_title, at.budget
            FROM collaboration_requests_advertiser cra
            JOIN collaborators c ON cra.collaborator_id = c.id
            JOIN ad_tasks at ON cra.ad_task_id = at.id
            WHERE cra.advertiser_id = %s
            ORDER BY cra.created_at DESC
        """
        return db.execute_query(query, (advertiser_id,))
    
    def get_advertiser_received_requests(self, advertiser_id):
        """获取广告主收到的合作请求"""
        query = """
            SELECT crc.*, c.username as collaborator_name, c.avatar_url as collaborator_avatar,
                   at.title as task_title, at.budget
            FROM collaboration_requests_collaborator crc
            JOIN collaborators c ON crc.collaborator_id = c.id
            JOIN ad_tasks at ON crc.ad_task_id = at.id
            WHERE crc.advertiser_id = %s
            ORDER BY crc.created_at DESC
        """
        return db.execute_query(query, (advertiser_id,))
    
    def get_collaborator_sent_requests(self, collaborator_id):
        """获取合作者发出的合作请求"""
        query = """
            SELECT crc.*, a.username as advertiser_name, a.avatar_url as advertiser_avatar,
                   at.title as task_title, at.budget
            FROM collaboration_requests_collaborator crc
            JOIN advertisers a ON crc.advertiser_id = a.id
            JOIN ad_tasks at ON crc.ad_task_id = at.id
            WHERE crc.collaborator_id = %s
            ORDER BY crc.created_at DESC
        """
        return db.execute_query(query, (collaborator_id,))
    
    def get_collaborator_received_requests(self, collaborator_id):
        """获取合作者收到的合作请求"""
        query = """
            SELECT cra.*, a.username as advertiser_name, a.avatar_url as advertiser_avatar,
                   at.title as task_title, at.budget
            FROM collaboration_requests_advertiser cra
            JOIN advertisers a ON cra.advertiser_id = a.id
            JOIN ad_tasks at ON cra.ad_task_id = at.id
            WHERE cra.collaborator_id = %s
            ORDER BY cra.created_at DESC
        """
        return db.execute_query(query, (collaborator_id,))
    
    def group_by_status(self, requests):
        """将请求按状态分组"""
        status_groups = {
            'pending': [],
            'accepted': [],
            'rejected': [],
            'canceled': []
        }
        
        for request in requests:
            if request['status'] in status_groups:
                status_groups[request['status']].append(request)
        
        return status_groups
    
    def update_advertiser_request_status(self, request_id, status, response_message=None):
        """更新广告主发出的合作请求状态"""
        if response_message:
            query = """
                UPDATE collaboration_requests_advertiser
                SET status = %s, response_message = %s, response_time = NOW()
                WHERE id = %s
            """
            return db.execute(query, (status, response_message, request_id))
        else:
            query = """
                UPDATE collaboration_requests_advertiser
                SET status = %s, response_time = NOW()
                WHERE id = %s
            """
            return db.execute(query, (status, request_id))
    
    def update_collaborator_request_status(self, request_id, status, response_message=None):
        """更新合作者发出的合作请求状态"""
        if response_message:
            query = """
                UPDATE collaboration_requests_collaborator
                SET status = %s, response_message = %s, response_time = NOW()
                WHERE id = %s
            """
            return db.execute(query, (status, response_message, request_id))
        else:
            query = """
                UPDATE collaboration_requests_collaborator
                SET status = %s, response_time = NOW()
                WHERE id = %s
            """
            return db.execute(query, (status, request_id))
    
    def get_all_advertiser_requests(self):
        """获取所有广告主发起的合作请求（管理员API使用）"""
        query = """
            SELECT cra.*, a.username as advertiser_name, c.username as collaborator_name,
                   at.title as task_title, at.budget, at.id as task_id
            FROM collaboration_requests_advertiser cra
            JOIN advertisers a ON cra.advertiser_id = a.id
            JOIN collaborators c ON cra.collaborator_id = c.id
            JOIN ad_tasks at ON cra.ad_task_id = at.id
            ORDER BY cra.created_at DESC
        """
        return db.execute_query(query)
    
    def get_all_collaborator_requests(self):
        """获取所有合作者发起的合作请求（管理员API使用）"""
        query = """
            SELECT crc.*, a.username as advertiser_name, c.username as collaborator_name,
                   at.title as task_title, at.budget, at.id as task_id
            FROM collaboration_requests_collaborator crc
            JOIN advertisers a ON crc.advertiser_id = a.id
            JOIN collaborators c ON crc.collaborator_id = c.id
            JOIN ad_tasks at ON crc.ad_task_id = at.id
            ORDER BY crc.created_at DESC
        """
        return db.execute_query(query)
    
    def delete_advertiser_request(self, request_id):
        """删除广告主发起的合作请求（管理员API使用）"""
        query = """
            DELETE FROM collaboration_requests_advertiser
            WHERE id = %s
        """
        return db.execute(query, (request_id,))
    
    def delete_collaborator_request(self, request_id):
        """删除合作者发起的合作请求（管理员API使用）"""
        query = """
            DELETE FROM collaboration_requests_collaborator
            WHERE id = %s
        """
        return db.execute(query, (request_id,))
    
    def get_invited_collaborator_ids(self, advertiser_id):
        """获取广告主已经发送过邀请的合作者ID列表"""
        query = """
            SELECT DISTINCT collaborator_id 
            FROM collaboration_requests_advertiser 
            WHERE advertiser_id = %s
        """
        results = db.fetch_all(query, (advertiser_id,))
        return [row['collaborator_id'] for row in results] if results else []
    
    def get_applied_task_ids(self, collaborator_id):
        """获取合作者已经申请的任务ID列表"""
        query = """
            SELECT DISTINCT ad_task_id 
            FROM collaboration_requests_collaborator 
            WHERE collaborator_id = %s
        """
        results = db.fetch_all(query, (collaborator_id,))
        return [row['ad_task_id'] for row in results] if results else []

# 初始化DAO实例
collaboration_requests_dao = CollaborationRequestsDAO() 