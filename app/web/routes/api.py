from flask import Blueprint, jsonify, request, current_app, session
from app.dao.ad_task_dao import AdTaskDAO
from app.dao.advertiser_dao import AdvertiserDAO
from app.dao.collaborator_dao import CollaboratorDAO
from datetime import datetime

# 创建API蓝图
api_bp = Blueprint('api', __name__)

@api_bp.route('/api/task_details/<int:task_id>', methods=['GET'])
def get_task_details(task_id):
    """获取任务详情API"""
    try:
        # 获取任务基本信息
        task = AdTaskDAO.get_task_by_id(task_id)
        if not task:
            return jsonify({'status': 'error', 'message': '任务不存在'}), 404
        
        # 转换为前端可用的JSON格式
        task_data = {
            'id': task['id'],
            'title': task['title'],
            'description': task['description'],
            'budget': float(task['budget']),
            'status': task['status'],
            'created_at': task['created_at'].strftime('%Y-%m-%d %H:%M') if task['created_at'] else None,
            'updated_at': task['updated_at'].strftime('%Y-%m-%d %H:%M') if task['updated_at'] else None,
            'deadline': task['deadline'].strftime('%Y-%m-%d') if task['deadline'] else None,
            'target_audience': task['target_audience'],
            'platform_requirements': task['platform_requirements'],
            'content_format': task['content_format'],
            'content_style': task['content_style'],
            'requirements': task['requirements'],
            'views_count': task['views_count'],
            'applications_count': task['applications_count'],
            'advertiser_id': task['advertiser_id']
        }
        
        # 获取广告主信息
        advertiser = AdvertiserDAO.get_advertiser_by_id(task['advertiser_id'])
        if advertiser:
            task_data.update({
                'advertiser_name': advertiser['username'],
                'company_name': advertiser['company_name'],
                'industry': advertiser['industry'],
                'advertiser_avatar': advertiser['avatar_url'],
                'previous_collaboration_count': advertiser['previous_collaboration_count']
            })
        
        # 如果任务状态为进行中或已完成，获取合作者信息
        if task['status'] in ['in_progress', 'completed']:
            # 获取任务关联的合作者ID (这里假设有一个方法可以获取)
            collaboration = AdTaskDAO.get_task_collaboration(task_id)
            if collaboration:
                collaborator_id = collaboration.get('collaborator_id')
                if collaborator_id:
                    collaborator = CollaboratorDAO.get_collaborator_by_id(collaborator_id)
                    if collaborator:
                        task_data.update({
                            'collaborator_id': collaborator['id'],
                            'collaborator_name': collaborator['username'],
                            'collaborator_platform': collaborator['platform'],
                            'collaborator_avatar': collaborator['avatar_url'],
                            'followers_count': collaborator['followers_count'],
                            'previous_collaboration_count': collaborator['previous_collaboration_count'],
                            'collaboration_start_time': collaboration.get('start_time'),
                        })
        
        return jsonify({'status': 'success', 'task': task_data})
    
    except Exception as e:
        print(f"获取任务详情错误: {str(e)}")
        return jsonify({'status': 'error', 'message': '服务器内部错误'}), 500

# 测试路由，确保API正常工作
@api_bp.route('/api/test', methods=['GET'])
def test_api():
    return jsonify({
        'status': 'success',
        'message': 'API工作正常',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })