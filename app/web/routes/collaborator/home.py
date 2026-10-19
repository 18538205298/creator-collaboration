from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from app.domain.collaborator.recommender_service import CollaboratorRecommenderService
# ... 其他导入 ...

# 初始化蓝图
collaborator_home_bp = Blueprint('collaborator', __name__, url_prefix='/collaborator/home')

# 初始化推荐服务
recommender_service = CollaboratorRecommenderService()

# ... 其他路由函数 ...

@collaborator_home_bp.route('/recommended')
def home_recommended():
    """合作者首页 - 推荐任务页面"""
    collaborator_id = session.get('user_id')
    if not collaborator_id:
        collaborator_id = 101  # 默认使用ID为101的合作者进行测试
    
    # 使用推荐服务获取推荐任务
    try:
        trending_tasks = recommender_service.get_trending_tasks(limit=3)
        print(f"获取到 {len(trending_tasks) if trending_tasks else 0} 个热门任务")
    except Exception as e:
        print(f"获取热门任务出错: {str(e)}")
        trending_tasks = []
    
    try:
        high_budget_tasks = recommender_service.get_high_budget_tasks(limit=2)
        print(f"获取到 {len(high_budget_tasks) if high_budget_tasks else 0} 个高预算任务")
    except Exception as e:
        print(f"获取高预算任务出错: {str(e)}")
        high_budget_tasks = []
    
    # 自定义推荐任务 - 基于合作者的特定专长
    try:
        recommended_tasks = recommender_service.get_recommended_tasks(collaborator_id, limit=5)
        print(f"获取到 {len(recommended_tasks) if recommended_tasks else 0} 个推荐任务")
    except Exception as e:
        print(f"获取推荐任务出错: {str(e)}")
        recommended_tasks = []
    
    # 如果没有获取到任何推荐数据，则提供一些模拟数据确保界面有内容显示
    if not trending_tasks and not high_budget_tasks and not recommended_tasks:
        print("所有推荐列表为空，使用模拟数据")
        # 模拟数据
        mock_task = {
            'id': 1,
            'title': '测试广告任务',
            'description': '这是一个测试用的广告任务描述，用于展示推荐系统界面效果。',
            'budget': 5000.00,
            'advertiser_name': '测试广告主',
            'company_name': '测试公司',
            'advertiser_avatar': None,
            'applications_count': 10,
            'views_count': 100
        }
        
        recommended_tasks = [mock_task.copy() for _ in range(3)]
        trending_tasks = [mock_task.copy() for _ in range(2)]
        trending_tasks[0]['title'] = '热门测试任务1'
        trending_tasks[1]['title'] = '热门测试任务2'
        high_budget_tasks = [mock_task.copy() for _ in range(2)]
        high_budget_tasks[0]['title'] = '高预算测试任务1'
        high_budget_tasks[0]['budget'] = 10000.00
        high_budget_tasks[1]['title'] = '高预算测试任务2'
        high_budget_tasks[1]['budget'] = 15000.00
    
    return render_template(
        'collaborator/home/recommended.html', 
        active_tab='recommended',
        trending_tasks=trending_tasks,
        high_budget_tasks=high_budget_tasks,
        recommended_tasks=recommended_tasks
    ) 