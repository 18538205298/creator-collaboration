from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify, flash, g
from app.web.auth_decorators import collaborator_required
from app.dao.user_dao import user_dao
from app.dao.ad_tasks_dao import ad_tasks_dao
from app.web.utils.notifications import notify_success, notify_error
import os
from werkzeug.utils import secure_filename
from app.config.settings import UPLOAD_FOLDER
from flask_paginate import Pagination
from datetime import datetime, date
from app.web.pagination import create_pagination
from app.dao.database import db
from app.dao.collaboration_requests_dao import collaboration_requests_dao
from functools import wraps

collaborator_bp = Blueprint('collaborator', __name__)

# 添加一个装饰器函数，用于向视图函数添加未读消息总数
def add_unread_count(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        # 先调用原始视图函数
        result = view_func(*args, **kwargs)
        
        # 如果结果是元组(响应, 状态码)，则不处理
        if isinstance(result, tuple):
            return result
        
        # 如果结果不是render_template返回的响应，则直接返回
        if not hasattr(result, 'template'):
            return result
        
        # 获取用户ID
        collaborator_id = session.get('user_id')
        if not collaborator_id:
            return result
        
        # 获取未读消息总数
        unread_count = get_collaborator_unread_count(collaborator_id)
        
        # 将未读消息总数添加到模板上下文
        if hasattr(result, '_TemplateReference__context'):
            ctx = result._TemplateReference__context
            ctx['total_unread_count'] = unread_count
        
        return result
    
    return wrapper

# 修改所有路由装饰器，添加未读消息总数装饰器
collaborator_bp.before_request(lambda: None)

@collaborator_bp.before_request
def before_request():
    # 如果是合作者登录页面或不需要登录的页面，则不处理
    if not session.get('user_id') or not session.get('user_type') == 'collaborator':
        return
    
    # 获取用户ID
    collaborator_id = session.get('user_id')
    
    # 获取未读消息总数
    unread_count = get_collaborator_unread_count(collaborator_id)
    
    # 将未读消息总数保存到g对象中，以便在模板中使用
    g.total_unread_count = unread_count

# 添加获取待处理邀请数量的方法
def get_collaborator_pending_invitations_count(collaborator_id):
    """获取合作者收到的待处理邀请数量"""
    query = """
        SELECT COUNT(*) as count
        FROM collaboration_requests_advertiser
        WHERE collaborator_id = %s AND status = 'pending'
    """
    result = db.execute_one(query, (collaborator_id,))
    return result['count'] if result else 0

# 修改模板过滤器，添加全局变量
@collaborator_bp.context_processor
def inject_unread_count():
    unread_count = getattr(g, 'total_unread_count', 0)
    # 如果用户已登录，则获取待处理邀请数量
    pending_invitations_count = 0
    if session.get('user_id') and session.get('user_type') == 'collaborator':
        collaborator_id = session.get('user_id')
        pending_invitations_count = get_collaborator_pending_invitations_count(collaborator_id)
    
    return {
        'total_unread_count': unread_count,
        'pending_invitations_count': pending_invitations_count
    }

# 首页相关路由
@collaborator_bp.route('/home')
@collaborator_required
def home():
    # 重定向到首页概览页面
    return redirect(url_for('collaborator.home_overview'))

@collaborator_bp.route('/home/overview')
@collaborator_required
def home_overview():
    # 获取用户ID
    collaborator_id = session.get('user_id')
    
    # 获取合作者基本信息
    collaborator = user_dao.get_user_by_id(collaborator_id, 'collaborator')
    
    # 获取浏览历史统计数据
    view_history_query = """
        SELECT COUNT(*) as view_count, COUNT(DISTINCT task_id) as tasks_viewed
        FROM view_history_collaborator
        WHERE collaborator_id = %s
    """
    view_stats = db.execute_one(view_history_query, (collaborator_id,))
    
    # 获取最近7天的浏览记录数
    recent_views_query = """
        SELECT COUNT(*) as count
        FROM view_history_collaborator
        WHERE collaborator_id = %s AND viewed_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """
    recent_views = db.execute_one(recent_views_query, (collaborator_id,))
    
    # 获取收藏任务统计
    favorites_query = """
        SELECT COUNT(*) as count
        FROM favorites_collaborator
        WHERE collaborator_id = %s
    """
    favorites = db.execute_one(favorites_query, (collaborator_id,))
    
    # 获取最近7天的收藏记录数
    recent_favorites_query = """
        SELECT COUNT(*) as count
        FROM favorites_collaborator
        WHERE collaborator_id = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """
    recent_favorites = db.execute_one(recent_favorites_query, (collaborator_id,))
    
    # 获取收藏率
    if view_stats and view_stats['tasks_viewed'] > 0:
        favorite_ratio = f"{(favorites['count'] / view_stats['tasks_viewed'] * 100):.1f}%"
    else:
        favorite_ratio = "0%"
    
    # 获取申请数据
    requests_query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted
        FROM collaboration_requests_collaborator
        WHERE collaborator_id = %s
    """
    requests = db.execute_one(requests_query, (collaborator_id,))
    
    # 计算申请通过率
    total_requests = requests['total'] if requests else 0
    accepted_requests = requests['accepted'] if requests else 0
    
    if total_requests > 0:
        accepted_ratio = f"{(accepted_requests / total_requests * 100):.1f}%"
    else:
        accepted_ratio = "0%"
    
    # 获取消息统计
    sent_messages_query = """
        SELECT COUNT(*) as count
        FROM messages_collaborator_to_advertiser
        WHERE sender_id = %s
    """
    sent_messages = db.execute_one(sent_messages_query, (collaborator_id,))
    
    received_messages_query = """
        SELECT COUNT(*) as count, SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as unread
        FROM messages_advertiser_to_collaborator
        WHERE receiver_id = %s
    """
    received_messages = db.execute_one(received_messages_query, (collaborator_id,))
    
    # 计算消息回复率
    total_received = received_messages['count'] if received_messages else 0
    total_sent = sent_messages['count'] if sent_messages else 0
    
    if total_received > 0:
        message_response_rate = f"{(total_sent / total_received * 100):.1f}%"
    else:
        message_response_rate = "0%"
    
    # 获取最近浏览的广告任务
    recent_viewed_tasks_query = """
        SELECT at.id, at.title, at.budget, at.status, at.deadline, 
               a.username as advertiser_name, vhc.viewed_at
        FROM view_history_collaborator vhc
        JOIN ad_tasks at ON vhc.task_id = at.id
        JOIN advertisers a ON at.advertiser_id = a.id
        WHERE vhc.collaborator_id = %s
        ORDER BY vhc.viewed_at DESC
        LIMIT 5
    """
    recent_viewed_tasks = db.execute_query(recent_viewed_tasks_query, (collaborator_id,))
    
    # 获取收藏的广告任务
    favorite_tasks_query = """
        SELECT at.id, at.title, at.budget, at.status, at.deadline, 
               a.username as advertiser_name, fc.created_at as favorited_at
        FROM favorites_collaborator fc
        JOIN ad_tasks at ON fc.task_id = at.id
        JOIN advertisers a ON at.advertiser_id = a.id
        WHERE fc.collaborator_id = %s
        ORDER BY fc.created_at DESC
        LIMIT 5
    """
    favorite_tasks = db.execute_query(favorite_tasks_query, (collaborator_id,))
    
    # 准备模板数据
    template_data = {
        'active_tab': 'overview',
        'collaborator': collaborator,
        'view_history_count': view_stats['view_count'] if view_stats else 0,
        'tasks_viewed_count': view_stats['tasks_viewed'] if view_stats else 0,
        'recent_views_count': recent_views['count'] if recent_views else 0,
        'favorite_tasks_count': favorites['count'] if favorites else 0,
        'recent_favorites_count': recent_favorites['count'] if recent_favorites else 0,
        'favorite_ratio': favorite_ratio,
        'sent_requests_count': total_requests,
        'pending_requests_count': requests['pending'] if requests else 0,
        'accepted_ratio': accepted_ratio,
        'sent_messages_count': total_sent,
        'received_messages_count': total_received,
        'unread_messages_count': received_messages['unread'] if received_messages else 0,
        'message_response_rate': message_response_rate,
        'recent_viewed_tasks': recent_viewed_tasks,
        'favorite_tasks': favorite_tasks
    }
    
    # 为任务状态添加显示名称
    for task in recent_viewed_tasks:
        if task['status'] == 'draft':
            task['status_display'] = '草稿'
        elif task['status'] == 'published':
            task['status_display'] = '已发布'
        elif task['status'] == 'in_progress':
            task['status_display'] = '进行中'
        elif task['status'] == 'completed':
            task['status_display'] = '已完成'
        elif task['status'] == 'cancelled':
            task['status_display'] = '已取消'
    
    for task in favorite_tasks:
        if task['status'] == 'draft':
            task['status_display'] = '草稿'
        elif task['status'] == 'published':
            task['status_display'] = '已发布'
        elif task['status'] == 'in_progress':
            task['status_display'] = '进行中'
        elif task['status'] == 'completed':
            task['status_display'] = '已完成'
        elif task['status'] == 'cancelled':
            task['status_display'] = '已取消'
    
    return render_template('collaborator/home/overview.html', **template_data)

@collaborator_bp.route('/home/recommended')
@collaborator_required
def home_recommended():
    # 获取当前合作者ID
    collaborator_id = session.get('user_id')
    if not collaborator_id:
        collaborator_id = 101  # 默认使用ID为101的合作者进行测试
    
    # 初始化推荐服务
    from app.domain.collaborator.recommender_service import CollaboratorRecommenderService
    recommender_service = CollaboratorRecommenderService()
    
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

@collaborator_bp.route('/home/notifications')
@collaborator_required
def home_notifications():
    # 获取当前合作者ID
    collaborator_id = session.get('user_id')
    
    # 从数据库获取系统通知
    query = """
        SELECT * FROM system_notifications_collaborator 
        WHERE collaborator_id = %s 
        ORDER BY created_at DESC
    """
    notifications = db.execute_query(query, (collaborator_id,))
    
    return render_template('collaborator/home/notifications.html', 
                           active_tab='notifications',
                           notifications=notifications)

# 我的合作相关路由
@collaborator_bp.route('/my_collaborations')
@collaborator_required
def my_collaborations():
    # 重定向到进行中项目页面
    return redirect(url_for('collaborator.my_collaborations_ongoing'))

@collaborator_bp.route('/my_collaborations/ongoing')
@collaborator_required
def my_collaborations_ongoing():
    # 获取用户ID
    collaborator_id = session.get('user_id')
    
    # 获取该合作者参与的状态为in_progress的任务
    query = """
        SELECT at.*, 
               a.username as advertiser_name, 
               a.company_name as company_name,
               a.avatar_url as advertiser_avatar,
               a.id as advertiser_id,
               COALESCE(cr_col.created_at, cr_adv.created_at) as collaboration_start_time
        FROM ad_tasks at
        LEFT JOIN collaboration_requests_collaborator cr_col ON at.id = cr_col.ad_task_id AND cr_col.status = 'accepted' AND cr_col.collaborator_id = %s
        LEFT JOIN collaboration_requests_advertiser cr_adv ON at.id = cr_adv.ad_task_id AND cr_adv.status = 'accepted' AND cr_adv.collaborator_id = %s
        JOIN advertisers a ON at.advertiser_id = a.id
        WHERE at.status = 'in_progress' AND (cr_col.id IS NOT NULL OR cr_adv.id IS NOT NULL)
        ORDER BY COALESCE(cr_col.created_at, cr_adv.created_at) DESC
    """
    
    ongoing_tasks = db.execute_query(query, (collaborator_id, collaborator_id))
    
    return render_template('collaborator/my_collaborations/ongoing.html', 
                          active_tab='ongoing',
                          ongoing_tasks=ongoing_tasks)

@collaborator_bp.route('/my_collaborations/completed')
@collaborator_required
def my_collaborations_completed():
    # 获取用户ID
    collaborator_id = session.get('user_id')
    
    # 获取该合作者参与的状态为completed的任务
    query = """
        SELECT at.*, 
               a.username as advertiser_name, 
               a.company_name as company_name,
               a.avatar_url as advertiser_avatar,
               a.id as advertiser_id,
               cr.created_at as collaboration_start_time
        FROM ad_tasks at
        JOIN collaboration_requests_collaborator cr ON at.id = cr.ad_task_id AND cr.status = 'accepted'
        JOIN advertisers a ON at.advertiser_id = a.id
        WHERE cr.collaborator_id = %s AND at.status = 'completed'
        ORDER BY at.updated_at DESC
    """
    
    completed_tasks = db.execute_query(query, (collaborator_id,))
    
    return render_template('collaborator/my_collaborations/completed.html', 
                          active_tab='completed',
                          completed_tasks=completed_tasks)

# 广告机会相关路由
@collaborator_bp.route('/ad_opportunities')
@collaborator_required
def ad_opportunities():
    # 重定向到任务列表页面
    return redirect(url_for('collaborator.ad_opportunities_list'))

@collaborator_bp.route('/ad_opportunities/list')
@collaborator_required
def ad_opportunities_list():
    # 获取筛选参数
    platform = request.args.get('platform', '')
    content_format = request.args.get('content_format', '')
    content_domain = request.args.get('content_domain', '')
    min_budget = request.args.get('min_budget', '')
    content_style = request.args.get('content_style', '')
    keyword = request.args.get('keyword', '')
    
    # 构建筛选参数字典
    filter_params = {}
    if platform:
        filter_params['platform'] = platform
    if content_format:
        filter_params['content_format'] = content_format
    if content_domain:
        filter_params['content_domain'] = content_domain
    if min_budget and min_budget.isdigit():
        filter_params['min_budget'] = int(min_budget)
    if content_style:
        filter_params['content_style'] = content_style
    if keyword:
        filter_params['keyword'] = keyword
    
    # 获取广告任务总数
    total_tasks = ad_tasks_dao.count_tasks(filter_params)
    
    # 使用通用分页工具
    pagination_data = create_pagination(
        total_items=total_tasks,
        per_page=12,
        record_name='广告任务'
    )
    
    # 获取当前页的广告任务
    page = pagination_data['page']
    per_page = pagination_data['per_page']
    ad_tasks = ad_tasks_dao.get_tasks_by_page(page, per_page, filter_params)
    
    # 获取当前用户收藏的任务ID列表
    user_id = session.get('user_id')
    favorite_task_ids = ad_tasks_dao.get_user_favorite_task_ids(user_id)
    
    # 处理日期数据，确保deadline是date对象
    for task in ad_tasks:
        if task.get('deadline') and isinstance(task['deadline'], str):
            try:
                task['deadline'] = datetime.strptime(task['deadline'], '%Y-%m-%d').date()
            except ValueError:
                pass
    
    # 当前时间，用于计算任务截止天数
    now = date.today()
    
    return render_template('collaborator/ad_opportunities/list.html', 
                          active_tab='list',
                          ad_tasks=ad_tasks,
                          pagination=pagination_data['pagination'],
                          now=now,
                          favorite_task_ids=favorite_task_ids)

@collaborator_bp.route('/ad_opportunities/task/<int:id>')
@collaborator_required
def task_detail(id):
    # 获取任务详情
    task = ad_tasks_dao.get_task_by_id(id)
    
    if not task:
        notify_error('未找到该广告任务')
        return redirect(url_for('collaborator.ad_opportunities_list'))
    
    # 增加浏览次数
    ad_tasks_dao.increment_views_count(id)
    
    # 记录浏览历史
    user_id = session.get('user_id')
    ad_tasks_dao.record_view_history(user_id, id)
    
    # 检查是否已收藏
    is_favorite = ad_tasks_dao.is_favorite(user_id, id)
    
    # 处理日期数据，确保deadline是date对象
    if task.get('deadline') and isinstance(task['deadline'], str):
        try:
            task['deadline'] = datetime.strptime(task['deadline'], '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # 当前时间，用于计算任务截止天数
    now = date.today()
    
    return render_template('collaborator/ad_opportunities/task_detail.html',
                          active_tab='list',
                          task=task,
                          is_favorite=is_favorite,
                          now=now)

@collaborator_bp.route('/ad_opportunities/apply/<int:id>', methods=['GET', 'POST'])
@collaborator_required
def apply_task(id):
    # 获取任务详情
    task = ad_tasks_dao.get_task_by_id(id)
    
    if not task:
        notify_error('未找到该广告任务')
        return redirect(url_for('collaborator.ad_opportunities_list'))
    
    # 处理日期数据，确保deadline是date对象
    if task.get('deadline') and isinstance(task['deadline'], str):
        try:
            task['deadline'] = datetime.strptime(task['deadline'], '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if request.method == 'POST':
        # 获取表单数据
        request_content = request.form.get('request_content')
        user_id = session.get('user_id')
        
        # 检查是否已经申请过
        # TODO: 实现检查逻辑
        
        # 创建申请记录
        # TODO: 实现保存申请记录的逻辑
        
        notify_success('申请已成功提交，请等待广告主回复')
        return redirect(url_for('collaborator.collaboration_requests_sent'))
    
    return render_template('collaborator/ad_opportunities/apply_task.html',
                          active_tab='list',
                          task=task)

@collaborator_bp.route('/api/favorite/add/<int:task_id>', methods=['POST'])
@collaborator_required
def add_favorite(task_id):
    user_id = session.get('user_id')
    result = ad_tasks_dao.add_favorite(user_id, task_id)
    if result:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "添加收藏失败"}), 500

@collaborator_bp.route('/api/favorite/remove/<int:task_id>', methods=['POST'])
@collaborator_required
def remove_favorite(task_id):
    user_id = session.get('user_id')
    result = ad_tasks_dao.remove_favorite(user_id, task_id)
    if result:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "取消收藏失败"}), 500

@collaborator_bp.route('/api/apply_task', methods=['POST'])
@collaborator_required
def api_apply_task():
    """处理申请合作的API请求"""
    try:
        user_id = session.get('user_id')
        data = request.json
        
        # 获取请求数据
        task_id = int(data.get('task_id', 0))
        advertiser_id = int(data.get('advertiser_id', 0))
        request_content = data.get('request_content', '')
        
        # 验证数据
        if not task_id or not advertiser_id or not request_content:
            return jsonify({
                'status': 'error',
                'message': '请求参数不完整'
            }), 400
        
        # 验证任务是否存在
        task_query = "SELECT id, status FROM ad_tasks WHERE id = %s"
        tasks = db.execute_query(task_query, (task_id,))
        task = tasks[0] if tasks else None
        
        if not task:
            return jsonify({
                'status': 'error',
                'message': '广告任务不存在'
            }), 404
            
        # 验证任务状态是否为已发布
        if task['status'] != 'published':
            return jsonify({
                'status': 'error',
                'message': '该广告任务当前不接受申请'
            }), 400
        
        # 验证是否已经申请过
        exists_query = """
            SELECT id FROM collaboration_requests_collaborator 
            WHERE collaborator_id = %s AND advertiser_id = %s AND ad_task_id = %s
            AND status IN ('pending', 'accepted')
        """
        
        existing_requests = db.execute_query(exists_query, (user_id, advertiser_id, task_id))
        existing_request = existing_requests[0] if existing_requests else None
        
        if existing_request:
            return jsonify({
                'status': 'error',
                'message': '您已经申请过该任务，请勿重复申请'
            }), 400
        
        # 创建申请记录
        insert_query = """
            INSERT INTO collaboration_requests_collaborator 
            (collaborator_id, advertiser_id, ad_task_id, request_content, status, created_at)
            VALUES (%s, %s, %s, %s, 'pending', NOW())
        """
        
        result = db.execute(insert_query, (user_id, advertiser_id, task_id, request_content))
        
        if result:
            # 更新任务申请数量
            update_query = """
                UPDATE ad_tasks 
                SET applications_count = applications_count + 1
                WHERE id = %s
            """
            db.execute(update_query, (task_id,))
            
            return jsonify({
                'status': 'success',
                'message': '申请已成功提交，请等待广告主回复'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '提交申请失败，请稍后重试'
            }), 500
            
    except Exception as e:
        print(f"申请合作出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '服务器内部错误'
        }), 500

@collaborator_bp.route('/ad_opportunities/favorites')
@collaborator_required
def ad_opportunities_favorites():
    # 获取用户ID
    user_id = session.get('user_id')
    
    # 获取收藏任务总数
    total_favorites = ad_tasks_dao.count_favorite_tasks(user_id)
    
    # 使用通用分页工具
    pagination_data = create_pagination(
        total_items=total_favorites,
        per_page=12,
        record_name='收藏任务'
    )
    
    # 获取当前页的收藏任务
    page = pagination_data['page']
    per_page = pagination_data['per_page']
    favorite_tasks = ad_tasks_dao.get_favorite_tasks_by_page(user_id, page, per_page)
    
    # 处理日期数据，确保deadline是date对象
    for task in favorite_tasks:
        if task.get('deadline') and isinstance(task['deadline'], str):
            try:
                task['deadline'] = datetime.strptime(task['deadline'], '%Y-%m-%d').date()
            except ValueError:
                pass
    
    # 当前时间，用于计算任务截止天数
    now = date.today()
    
    return render_template('collaborator/ad_opportunities/favorites.html', 
                          active_tab='favorites',
                          ad_tasks=favorite_tasks,
                          pagination=pagination_data['pagination'],
                          now=now)

# 合作邀请相关路由
@collaborator_bp.route('/collaboration_requests')
@collaborator_required
def collaboration_requests():
    # 重定向到已发送页面
    return redirect(url_for('collaborator.collaboration_requests_sent'))

@collaborator_bp.route('/collaboration_requests/sent')
@collaborator_required
def collaboration_requests_sent():
    # 检查是否需要显示取消成功的flash消息
    if session.pop('show_cancel_success', False):
        notify_success('合作请求已成功取消', duration=3000)
    
    # 获取当前合作者ID
    collaborator_id = session.get('user_id')
    
    # 获取合作者发送的请求数据
    sent_requests = collaboration_requests_dao.get_collaborator_sent_requests(collaborator_id)
    
    # 按状态分组
    grouped_requests = collaboration_requests_dao.group_by_status(sent_requests)
    
    return render_template('collaborator/collaboration_requests/sent.html', 
                          active_tab='sent',
                          pending_requests=grouped_requests['pending'],
                          accepted_requests=grouped_requests['accepted'],
                          rejected_requests=grouped_requests['rejected'],
                          canceled_requests=grouped_requests['canceled'])

@collaborator_bp.route('/collaboration_requests/received')
@collaborator_required
def collaboration_requests_received():
    # 获取当前合作者ID
    collaborator_id = session.get('user_id')
    
    # 获取合作者收到的请求数据
    received_requests = collaboration_requests_dao.get_collaborator_received_requests(collaborator_id)
    
    # 按状态分组
    grouped_requests = collaboration_requests_dao.group_by_status(received_requests)
    
    return render_template('collaborator/collaboration_requests/received.html', 
                          active_tab='received',
                          pending_requests=grouped_requests['pending'],
                          accepted_requests=grouped_requests['accepted'],
                          rejected_requests=grouped_requests['rejected'])

# 消息中心相关路由
@collaborator_bp.route('/messages')
@collaborator_required
def messages():
    # 重定向到我的关注页面
    return redirect(url_for('collaborator.messages_following'))

@collaborator_bp.route('/messages/following')
@collaborator_required
def messages_following():
    collaborator_id = session.get('user_id')
    
    # 获取合作者关注的广告主列表
    query = """
        SELECT a.*
        FROM follows_collaborator_to_advertiser f
        JOIN advertisers a ON f.advertiser_id = a.id
        WHERE f.collaborator_id = %s
        ORDER BY f.created_at DESC
    """
    following_list = db.execute_query(query, (collaborator_id,))
    
    # 获取总未读消息数
    total_unread_count = get_collaborator_unread_count(collaborator_id)
    
    return render_template('collaborator/messages/following.html', 
                          active_tab='following',
                          following_list=following_list,
                          total_unread_count=total_unread_count)

@collaborator_bp.route('/messages/followers')
@collaborator_required
def messages_followers():
    collaborator_id = session.get('user_id')
    
    # 获取关注该合作者的广告主列表
    query = """
        SELECT a.*,
               (SELECT COUNT(1) FROM follows_collaborator_to_advertiser 
                WHERE collaborator_id = %s AND advertiser_id = a.id) > 0 AS is_following
        FROM follows_advertiser_to_collaborator f
        JOIN advertisers a ON f.advertiser_id = a.id
        WHERE f.collaborator_id = %s
        ORDER BY f.created_at DESC
    """
    followers_list = db.execute_query(query, (collaborator_id, collaborator_id))
    
    # 获取总未读消息数
    total_unread_count = get_collaborator_unread_count(collaborator_id)
    
    return render_template('collaborator/messages/followers.html', 
                          active_tab='followers',
                          followers_list=followers_list,
                          total_unread_count=total_unread_count)

@collaborator_bp.route('/messages/inbox')
@collaborator_required
def messages_inbox():
    collaborator_id = session.get('user_id')
    
    # 获取相互关注的好友（合作者和广告主互相关注）
    query = """
        SELECT a.*, NULL as last_message, NULL as last_message_time, 0 as unread_count
        FROM follows_collaborator_to_advertiser c2a
        JOIN follows_advertiser_to_collaborator a2c ON c2a.advertiser_id = a2c.advertiser_id
        JOIN advertisers a ON a.id = c2a.advertiser_id
        WHERE c2a.collaborator_id = %s AND a2c.collaborator_id = %s
        ORDER BY a.username
    """
    mutual_friends = db.execute_query(query, (collaborator_id, collaborator_id))
    
    # 计算每个好友的未读消息数
    total_unread_count = 0
    for friend in mutual_friends:
        unread_query = """
            SELECT COUNT(*) as count
            FROM messages_advertiser_to_collaborator
            WHERE sender_id = %s AND receiver_id = %s AND is_read = 0
        """
        unread_result = db.execute_one(unread_query, (friend['id'], collaborator_id))
        friend['unread_count'] = unread_result['count'] if unread_result else 0
        total_unread_count += friend['unread_count']
    
    # 获取选中的联系人ID
    contact_id = request.args.get('contact_id', None)
    active_contact = None
    messages = []
    
    if contact_id:
        try:
            # 获取联系人信息
            contact_id = int(contact_id)
            for friend in mutual_friends:
                if friend['id'] == contact_id:
                    active_contact = friend
                    break
                    
            if active_contact:
                # 查询聊天记录
                messages_query = """
                    SELECT id, sender_id, receiver_id, content, is_read, created_at, 'sent' as type
                    FROM messages_collaborator_to_advertiser
                    WHERE sender_id = %s AND receiver_id = %s
                    UNION
                    SELECT id, sender_id, receiver_id, content, is_read, created_at, 'received' as type
                    FROM messages_advertiser_to_collaborator
                    WHERE sender_id = %s AND receiver_id = %s
                    ORDER BY created_at ASC
                """
                raw_messages = db.execute_query(messages_query, (collaborator_id, contact_id, contact_id, collaborator_id))
                
                # 将消息标记为已读（仅接收到的消息）
                update_query = """
                    UPDATE messages_advertiser_to_collaborator
                    SET is_read = 1
                    WHERE sender_id = %s AND receiver_id = %s AND is_read = 0
                """
                db.execute(update_query, (contact_id, collaborator_id))
                
                # 格式化消息
                for msg in raw_messages:
                    is_sent = msg['type'] == 'sent'
                    time_str = msg['created_at'].strftime('%H:%M') if isinstance(msg['created_at'], datetime) else str(msg['created_at'])
                    messages.append({
                        'id': msg['id'],
                        'content': msg['content'],
                        'is_sent': is_sent,
                        'time': time_str,
                        'is_read': msg['is_read']
                    })
        except Exception as e:
            print(f"[ERROR] 合作者消息页面 - 加载消息时出错: {str(e)}")
    
    return render_template('collaborator/messages/inbox.html', 
                          active_tab='inbox',
                          mutual_friends=mutual_friends,
                          active_contact=active_contact,
                          messages=messages,
                          total_unread_count=total_unread_count)

@collaborator_bp.route('/messages/send', methods=['POST'])
@collaborator_required
def send_message_post():
    """处理表单提交的消息发送请求"""
    try:
        # 获取合作者ID
        sender_id = session.get('user_id')
        
        # 获取接收者ID和消息内容
        receiver_id = request.form.get('receiver_id', None)
        content = request.form.get('content', '').strip()
        
        # 验证数据
        if not receiver_id or not content:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': '消息内容不能为空'})
            notify_error('消息内容不能为空')
            return redirect(url_for('collaborator.messages_inbox'))
            
        receiver_id = int(receiver_id)
        
        # 验证接收者是否存在
        receiver_query = "SELECT id FROM advertisers WHERE id = %s"
        receiver = db.execute_one(receiver_query, (receiver_id,))
        
        if not receiver:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': '接收者不存在'})
            notify_error('接收者不存在')
            return redirect(url_for('collaborator.messages_inbox'))
        
        # 验证是否互相关注
        c2a_query = "SELECT COUNT(*) as count FROM follows_collaborator_to_advertiser WHERE collaborator_id = %s AND advertiser_id = %s"
        c2a_result = db.execute_one(c2a_query, (sender_id, receiver_id))
        
        a2c_query = "SELECT COUNT(*) as count FROM follows_advertiser_to_collaborator WHERE advertiser_id = %s AND collaborator_id = %s"
        a2c_result = db.execute_one(a2c_query, (receiver_id, sender_id))
        
        is_mutual = (c2a_result and c2a_result['count'] > 0) and (a2c_result and a2c_result['count'] > 0)
        
        if not is_mutual:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': '只能向好友发送消息'})
            notify_error('只能向好友发送消息')
            return redirect(url_for('collaborator.messages_inbox'))
        
        # 插入新消息
        insert_query = """
            INSERT INTO messages_collaborator_to_advertiser (sender_id, receiver_id, content, is_read, created_at)
            VALUES (%s, %s, %s, 0, NOW())
        """
        result = db.execute(insert_query, (sender_id, receiver_id, content))
        
        if not result:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': '发送消息失败，请稍后重试'})
            notify_error('发送消息失败，请稍后重试')
            return redirect(url_for('collaborator.messages_inbox', contact_id=receiver_id))
            
        # 如果是Ajax请求，返回JSON响应
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
            
        # 否则重定向回聊天页面
        return redirect(url_for('collaborator.messages_inbox', contact_id=receiver_id))
        
    except Exception as e:
        print(f"[ERROR] 合作者发送消息表单处理 - 出错: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': '服务器内部错误，请稍后重试'})
        notify_error('服务器内部错误，请稍后重试')
        return redirect(url_for('collaborator.messages_inbox'))

# 个人中心相关路由
@collaborator_bp.route('/profile')
@collaborator_required
def profile():
    # 重定向到基本资料页面
    return redirect(url_for('collaborator.profile_basic'))

@collaborator_bp.route('/profile/basic')
@collaborator_required
def profile_basic():
    user_id = session.get('user_id')
    collaborator = user_dao.get_user_by_id(user_id, 'collaborator')
    
    # 添加交互数据统计
    stats = {
        'likes_count': collaborator.get('likes_count', 0),
        'favorites_count': collaborator.get('favorites_count', 0),
        'shares_count': collaborator.get('shares_count', 0),
        'comments_count': collaborator.get('comments_count', 0),
        'clicks_count': collaborator.get('clicks_count', 0),
        'previous_collaboration_count': collaborator.get('previous_collaboration_count', 0)
    }
    
    return render_template('collaborator/profile/basic.html', 
                          active_tab='basic', 
                          collaborator=collaborator,
                          stats=stats)

@collaborator_bp.route('/profile/edit')
@collaborator_required
def profile_edit():
    user_id = session.get('user_id')
    collaborator = user_dao.get_user_by_id(user_id, 'collaborator')
    return render_template('collaborator/profile/edit.html', active_tab='edit', collaborator=collaborator)

@collaborator_bp.route('/profile/change_password', methods=['POST'])
@collaborator_required
def change_password():
    user_id = session.get('user_id')
    
    # 获取表单数据
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # 验证表单数据
    if not all([old_password, new_password, confirm_password]):
        flash('请填写所有密码字段', 'error')
        return redirect(url_for('collaborator.profile_edit'))
    
    # 验证当前密码
    collaborator = user_dao.get_user_by_id(user_id, 'collaborator')
    if old_password != collaborator['password']:  # 实际应用中应使用安全的密码验证
        flash('当前密码不正确', 'error')
        return redirect(url_for('collaborator.profile_edit'))
    
    # 验证新密码与确认密码是否匹配
    if new_password != confirm_password:
        flash('新密码与确认密码不匹配', 'error')
        return redirect(url_for('collaborator.profile_edit'))
    
    # 更新密码
    query = "UPDATE collaborators SET password = %s WHERE id = %s"
    success = db.execute(query, (new_password, user_id))  # 实际应用中应对密码进行哈希处理
    
    if success:
        flash('密码已成功更新', 'success')
    else:
        flash('新密码与旧密码相同', 'error')
    
    return redirect(url_for('collaborator.profile_edit'))

@collaborator_bp.route('/profile/finance')
@collaborator_required
def profile_finance():
    user_id = session.get('user_id')
    collaborator = user_dao.get_user_by_id(user_id, 'collaborator')
    
    # 获取余额交易记录
    query = """
        SELECT created_at, amount, description, 
               CASE WHEN amount > 0 THEN '收入' WHEN amount < 0 THEN '支出' ELSE '其他' END as type,
               'success' as status
        FROM balance_transactions_collaborator 
        WHERE collaborator_id = %s
        ORDER BY created_at DESC LIMIT 10
    """
    recharge_records = db.execute_query(query, (user_id,))
    
    # 计算总收入
    income_query = """
        SELECT COALESCE(SUM(budget), 0) as total_income
        FROM ad_tasks at
        JOIN collaboration_requests_collaborator crc ON at.id = crc.ad_task_id
        WHERE crc.collaborator_id = %s AND crc.status = 'accepted' AND at.status = 'completed'
    """
    income_result = db.execute_one(income_query, (user_id,))
    total_income = income_result['total_income'] if income_result else 0
    
    # 计算平均收入
    avg_income = 0
    if collaborator.get('previous_collaboration_count', 0) > 0:
        avg_income = float(total_income) / collaborator.get('previous_collaboration_count')
    
    return render_template('collaborator/profile/finance.html', 
                          active_tab='finance',
                          collaborator=collaborator,
                          recharge_records=recharge_records,
                          total_income=total_income,
                          avg_income=avg_income)

@collaborator_bp.route('/recharge', methods=['POST'])
@collaborator_required
def recharge():
    user_id = session.get('user_id')
    amount = request.form.get('amount', 0)
    payment_method = request.form.get('payment_method', 'alipay')
    
    try:
        # 金额转换为浮点数
        amount = float(amount)
        
        # 验证金额
        if amount <= 0:
            flash('充值金额必须大于0', 'error')
            return redirect(url_for('collaborator.profile_finance'))
            
        # 插入充值记录
        insert_query = """
            INSERT INTO recharge_records (user_id, user_type, amount, payment_method, status, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """
        db.execute(insert_query, (user_id, 'collaborator', amount, payment_method, 'success'))
        
        # 更新用户余额
        user_dao.update_user_balance(user_id, 'collaborator', amount)
        
        flash('充值成功！', 'success')
    except ValueError:
        flash('请输入有效的金额', 'error')
    except Exception as e:
        print(f"充值处理错误: {str(e)}")
        flash('处理充值时出错，请稍后重试', 'error')
    
    return redirect(url_for('collaborator.profile_finance'))

@collaborator_bp.route('/profile/save', methods=['POST'])
@collaborator_required
def profile_save():
    user_id = session.get('user_id')
    print(f"处理合作者ID {user_id} 的个人资料保存请求")
    
    # 获取表单数据
    platform = request.form.get('platform')
    phone_number = request.form.get('phone_number')
    followers_count = request.form.get('followers_count', 0)
    content_format = request.form.get('content_format')
    content_style = request.form.get('content_style')
    content_domain = request.form.get('content_domain')
    
    # 准备更新数据
    update_data = {
        'platform': platform,
        'phone_number': phone_number,
        'followers_count': followers_count,
        'content_format': content_format,
        'content_style': content_style,
        'content_domain': content_domain
    }
    
    # 处理头像上传
    if 'avatar_upload' in request.files:
        print("表单中包含avatar_upload字段")
        avatar_file = request.files['avatar_upload']
        if avatar_file and avatar_file.filename:
            print(f"收到文件上传: {avatar_file.filename}")
            # 确保文件名安全
            from werkzeug.utils import secure_filename
            import os
            import uuid
            from app.config.settings import UPLOAD_FOLDER
            
            # 检查文件类型
            allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
            file_ext = os.path.splitext(avatar_file.filename)[1].lower().lstrip('.')
            
            print(f"文件扩展名: {file_ext}")
            
            if file_ext not in allowed_extensions:
                flash(f'不支持的文件类型，请上传 {", ".join(allowed_extensions)} 格式的图片', 'error')
                return redirect(url_for('collaborator.profile_edit'))
            
            # 获取当前用户的头像信息
            current_collaborator = user_dao.get_user_by_id(user_id, 'collaborator')
            current_avatar = current_collaborator.get('avatar_url')
            
            print(f"当前头像: {current_avatar}")
            
            # 删除旧头像文件（如果不是默认头像）
            if current_avatar and current_avatar != 'default_collaborator.png':
                old_avatar_path = os.path.join(UPLOAD_FOLDER, 'avatars', current_avatar)
                print(f"尝试删除旧头像: {old_avatar_path}")
                if os.path.exists(old_avatar_path):
                    try:
                        os.remove(old_avatar_path)
                        print(f"成功删除旧头像")
                    except Exception as e:
                        # 删除失败，仅记录日志，不影响后续操作
                        print(f"无法删除旧头像文件: {old_avatar_path}, 错误: {str(e)}")
            
            filename = secure_filename(avatar_file.filename)
            # 添加用户ID前缀和随机字符串，避免文件名冲突
            unique_filename = f"collaborator_{user_id}_{uuid.uuid4().hex[:8]}{os.path.splitext(filename)[1]}"
            
            # 确保目录存在
            avatar_dir = os.path.join(UPLOAD_FOLDER, 'avatars')
            print(f"头像保存目录: {avatar_dir}")
            os.makedirs(avatar_dir, exist_ok=True)
            
            # 保存文件
            filepath = os.path.join(avatar_dir, unique_filename)
            print(f"保存头像到: {filepath}")
            avatar_file.save(filepath)
            print(f"头像文件已保存")
            
            # 更新数据库中的头像URL
            update_data['avatar_url'] = unique_filename
            
            # 更新会话中的头像URL
            session['avatar_url'] = unique_filename
        else:
            print("表单中avatar_upload字段为空或未提供文件名")
    else:
        print("表单中没有avatar_upload字段")
    
    # 更新数据库
    success = user_dao.update_collaborator(user_id, update_data)
    
    if success:
        print("数据库更新成功")
        flash('个人资料已成功更新', 'success')
    else:
        print("数据库更新失败")
        flash('更新个人资料时出错，请稍后重试', 'error')
    
    return redirect(url_for('collaborator.profile_basic'))

@collaborator_bp.route('/ad_opportunities/history')
@collaborator_required
def ad_opportunities_history():
    # 获取用户ID
    user_id = session.get('user_id')
    
    # 获取浏览历史总数
    total_history = ad_tasks_dao.count_view_history(user_id)
    
    # 使用通用分页工具
    pagination_data = create_pagination(
        total_items=total_history,
        per_page=12,
        record_name='浏览历史'
    )
    
    # 获取当前页的浏览历史
    page = pagination_data['page']
    per_page = pagination_data['per_page']
    view_history = ad_tasks_dao.get_view_history(user_id, page, per_page)
    
    # 处理日期数据，确保deadline是date对象
    for task in view_history:
        if task.get('deadline') and isinstance(task['deadline'], str):
            try:
                task['deadline'] = datetime.strptime(task['deadline'], '%Y-%m-%d').date()
            except ValueError:
                pass
    
    # 当前时间，用于计算任务截止天数
    now = date.today()
    
    return render_template('collaborator/ad_opportunities/history.html', 
                          active_tab='history',
                          ad_tasks=view_history,
                          pagination=pagination_data['pagination'],
                          now=now)

# 取消合作请求的API
@collaborator_bp.route('/api/cancel_request/<int:request_id>', methods=['POST'])
@collaborator_required
def cancel_request(request_id):
    """取消发送的合作请求"""
    try:
        # 获取当前用户ID
        collaborator_id = session.get('user_id')
        
        # 验证请求是否存在且属于当前用户
        query = """
            SELECT id, status FROM collaboration_requests_collaborator 
            WHERE id = %s AND collaborator_id = %s AND status = 'pending'
        """
        requests = db.execute_query(query, (request_id, collaborator_id))
        
        if not requests:
            return jsonify({
                'status': 'error',
                'message': '请求不存在或无权操作'
            }), 404
        
        # 更新请求状态为canceled
        result = collaboration_requests_dao.update_collaborator_request_status(request_id, 'canceled')
        
        if result:
            # 设置下一次请求时显示的通知
            session['show_cancel_success'] = True
            
            return jsonify({
                'status': 'success',
                'message': '已成功取消合作请求'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '取消请求失败，请稍后重试'
            }), 500
    except Exception as e:
        print(f"取消合作请求出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '服务器内部错误'
        }), 500

@collaborator_bp.route('/api/accept_invitation/<int:request_id>', methods=['POST'])
@collaborator_required
def accept_invitation(request_id):
    """处理合作者接受广告主邀请的API"""
    try:
        # 获取合作者ID
        collaborator_id = session.get('user_id')
        print(f"合作者{collaborator_id}尝试接受邀请{request_id}")
        
        # 验证请求是否存在且属于当前合作者
        query = """
            SELECT id, ad_task_id FROM collaboration_requests_advertiser 
            WHERE id = %s AND collaborator_id = %s AND status = 'pending'
        """
        results = db.execute_query(query, (request_id, collaborator_id))
        
        if not results:
            print(f"邀请{request_id}不存在或不属于合作者{collaborator_id}")
            return jsonify({
                'status': 'error',
                'message': '无效的邀请或您无权操作此邀请'
            }), 403
        
        # 获取任务ID
        task_id = results[0]['ad_task_id']
        print(f"找到对应的广告任务ID：{task_id}")
        
        # 检查任务状态
        task_query = """
            SELECT id, status FROM ad_tasks 
            WHERE id = %s
        """
        task_results = db.execute_query(task_query, (task_id,))
        
        if not task_results:
            print(f"广告任务{task_id}不存在")
            return jsonify({
                'status': 'error',
                'message': '该广告任务不存在，无法接受邀请'
            }), 404
            
        print(f"广告任务{task_id}状态为：{task_results[0]['status']}")
        if task_results[0]['status'] == 'in_progress':
            # 任务已被接受，删除该请求记录
            delete_query = """
                DELETE FROM collaboration_requests_advertiser 
                WHERE id = %s
            """
            db.execute(delete_query, (request_id,))
            
            print(f"广告任务{task_id}已处于进行中状态，删除重复请求")
            return jsonify({
                'status': 'error',
                'message': '该广告任务已被接受，无法重复接受邀请'
            }), 400
        
        # 更新请求状态为已接受
        response_message = "感谢您的邀请，我很乐意与您合作"
        result = collaboration_requests_dao.update_advertiser_request_status(
            request_id, 'accepted', response_message
        )
        
        if result:
            # 更新任务状态为进行中
            task_update_query = """
                UPDATE ad_tasks SET status = 'in_progress' WHERE id = %s
            """
            db.execute(task_update_query, (task_id,))
            
            print(f"成功接受邀请并将广告任务{task_id}状态更新为in_progress")
            # 通知操作成功
            notify_success('已成功接受合作邀请', duration=3000)
            return jsonify({
                'status': 'success',
                'message': '已成功接受合作邀请'
            })
        else:
            print(f"更新邀请状态失败")
            return jsonify({
                'status': 'error',
                'message': '操作失败，请稍后重试'
            }), 500
            
    except Exception as e:
        print(f"接受邀请时发生异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@collaborator_bp.route('/api/reject_invitation/<int:request_id>', methods=['POST'])
@collaborator_required
def reject_invitation(request_id):
    """处理合作者拒绝广告主邀请的API"""
    try:
        # 获取合作者ID
        collaborator_id = session.get('user_id')
        
        # 验证请求是否存在且属于当前合作者
        query = """
            SELECT id, ad_task_id FROM collaboration_requests_advertiser 
            WHERE id = %s AND collaborator_id = %s AND status = 'pending'
        """
        results = db.execute_query(query, (request_id, collaborator_id))
        
        if not results:
            return jsonify({
                'status': 'error',
                'message': '无效的邀请或您无权操作此邀请'
            }), 403
        
        # 获取任务ID
        task_id = results[0]['ad_task_id']
        
        # 检查任务状态
        task_query = """
            SELECT id, status FROM ad_tasks 
            WHERE id = %s
        """
        task_results = db.execute_query(task_query, (task_id,))
        
        if not task_results:
            return jsonify({
                'status': 'error',
                'message': '该广告任务不存在，无法拒绝邀请'
            }), 404
            
        if task_results[0]['status'] == 'in_progress':
            # 任务已被接受，删除该请求记录
            delete_query = """
                DELETE FROM collaboration_requests_advertiser 
                WHERE id = %s
            """
            db.execute(delete_query, (request_id,))
            
            return jsonify({
                'status': 'error',
                'message': '该广告任务已被接受，无法拒绝邀请'
            }), 400
        
        # 更新请求状态为已拒绝
        response_message = "非常抱歉，我目前无法接受您的合作邀请"
        result = collaboration_requests_dao.update_advertiser_request_status(
            request_id, 'rejected', response_message
        )
        
        if result:
            # 通知操作成功
            notify_success('已拒绝合作邀请', duration=3000)
            return jsonify({
                'status': 'success',
                'message': '已拒绝合作邀请'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '操作失败，请稍后重试'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@collaborator_bp.route('/api/submit_completion/<int:task_id>', methods=['POST'])
@collaborator_required
def submit_completion(task_id):
    """提交项目成果，通知广告主可以标记为已完成"""
    try:
        # 获取合作者ID
        collaborator_id = session.get('user_id')
        
        # 验证任务是否存在且合作者正在参与
        task_query = """
            SELECT at.id, at.advertiser_id, at.status 
            FROM ad_tasks at
            JOIN collaboration_requests_collaborator cr ON at.id = cr.ad_task_id AND cr.status = 'accepted'
            WHERE at.id = %s AND cr.collaborator_id = %s AND at.status = 'in_progress'
        """
        tasks = db.execute_query(task_query, (task_id, collaborator_id))
        
        if not tasks:
            notify_error('无效的任务或您无权操作该任务')
            return jsonify({
                'status': 'error',
                'message': '无效的任务或您无权操作该任务'
            }), 403
        
        # 获取广告主ID
        advertiser_id = tasks[0]['advertiser_id']
        
        # 记录成果提交日志（这里可以扩展为实际存储提交内容）
        log_query = """
            INSERT INTO project_logs (task_id, user_id, user_type, action, content, created_at)
            VALUES (%s, %s, 'collaborator', 'completion_submit', '合作者提交了项目成果，请查看并确认', NOW())
        """
        db.execute(log_query, (task_id, collaborator_id))
        
        # 通知广告主成果已提交
        # TODO: 这里可以扩展为发送实际通知
        
        notify_success('已成功提交项目成果，等待广告主确认')
        return jsonify({
            'status': 'success',
            'message': '已成功提交项目成果，等待广告主确认'
        })
        
    except Exception as e:
        print(f"提交项目成果时出错: {str(e)}")
        notify_error('服务器内部错误')
        return jsonify({
            'status': 'error',
            'message': '服务器内部错误'
        }), 500

@collaborator_bp.route('/ad_opportunities/advertiser/<int:advertiser_id>')
@collaborator_required
def advertiser_detail(advertiser_id):
    # 获取广告主详情
    advertiser = user_dao.get_advertiser_by_id(advertiser_id)
    
    if not advertiser:
        notify_error('未找到该广告主信息')
        return redirect(url_for('collaborator.ad_opportunities_list'))
    
    # 获取该广告主近期的广告任务
    recent_tasks_query = """
        SELECT id, title, budget, created_at, status 
        FROM ad_tasks 
        WHERE advertiser_id = %s AND status = 'published'
        ORDER BY created_at DESC 
        LIMIT 5
    """
    recent_tasks = db.execute_query(recent_tasks_query, (advertiser_id,))
    
    # 计算合作接受率
    cooperation_rate_query = """
        SELECT 
            COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted_count,
            COUNT(*) as total_count
        FROM collaboration_requests_advertiser
        WHERE advertiser_id = %s
    """
    rate_data = db.execute_one(cooperation_rate_query, (advertiser_id,))
    
    cooperation_rate = "0%"
    if rate_data and rate_data['total_count'] > 0:
        accept_rate = (rate_data['accepted_count'] / rate_data['total_count']) * 100
        cooperation_rate = f"{accept_rate:.1f}%"
    
    # 检查当前用户是否关注了该广告主
    collaborator_id = session.get('user_id')
    is_following = False
    
    try:
        follow_query = """
            SELECT id FROM follows_collaborator_to_advertiser 
            WHERE collaborator_id = %s AND advertiser_id = %s
        """
        follow_result = db.execute_one(follow_query, (collaborator_id, advertiser_id))
        is_following = bool(follow_result)
    except Exception as e:
        print(f"检查关注状态时出错: {str(e)}")
    
    return render_template('collaborator/ad_opportunities/advertiser_detail.html',
                          active_tab='list',
                          advertiser=advertiser,
                          recent_tasks=recent_tasks,
                          cooperation_rate=cooperation_rate,
                          is_following=is_following)

@collaborator_bp.route('/api/follow/add/<int:advertiser_id>', methods=['POST'])
@collaborator_required
def add_follow(advertiser_id):
    """合作者关注广告主"""
    try:
        collaborator_id = session.get('user_id')
        
        # 检查是否已经关注
        check_query = "SELECT id FROM follows_collaborator_to_advertiser WHERE collaborator_id = %s AND advertiser_id = %s"
        exist = db.execute_one(check_query, (collaborator_id, advertiser_id))
        
        if exist:
            return jsonify({'status': 'success', 'message': '已经关注过该广告主'})
        
        # 添加关注关系
        insert_query = "INSERT INTO follows_collaborator_to_advertiser (collaborator_id, advertiser_id) VALUES (%s, %s)"
        db.execute(insert_query, (collaborator_id, advertiser_id))
        
        return jsonify({'status': 'success', 'message': '关注成功'})
    except Exception as e:
        print(f"添加关注出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'操作失败: {str(e)}'})

@collaborator_bp.route('/api/follow/remove/<int:advertiser_id>', methods=['POST'])
@collaborator_required
def remove_follow(advertiser_id):
    """合作者取消关注广告主"""
    try:
        collaborator_id = session.get('user_id')
        
        # 删除关注关系
        delete_query = "DELETE FROM follows_collaborator_to_advertiser WHERE collaborator_id = %s AND advertiser_id = %s"
        db.execute(delete_query, (collaborator_id, advertiser_id))
        
        return jsonify({'status': 'success', 'message': '已取消关注'})
    except Exception as e:
        print(f"取消关注出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'操作失败: {str(e)}'})

@collaborator_bp.route('/api/get_messages/<int:receiver_id>')
@collaborator_required
def get_messages(receiver_id):
    """获取与指定用户的聊天记录"""
    try:
        print(f"[DEBUG] 合作者获取消息 - 开始处理请求，接收者ID: {receiver_id}")
        # 获取合作者ID
        sender_id = session.get('user_id')
        print(f"[DEBUG] 合作者获取消息 - 发送者ID: {sender_id}")
        
        # 直接使用两个简单查询检查是否互相关注
        # 检查合作者是否关注了广告主
        c2a_query = "SELECT COUNT(*) as count FROM follows_collaborator_to_advertiser WHERE collaborator_id = %s AND advertiser_id = %s"
        try:
            c2a_result = db.execute_one(c2a_query, (sender_id, receiver_id))
            print(f"[DEBUG] 合作者获取消息 - 合作者关注广告主检查结果: {c2a_result}")
        except Exception as e:
            print(f"[ERROR] 合作者获取消息 - 合作者关注广告主检查出错: {str(e)}")
            c2a_result = None
        
        # 检查广告主是否关注了合作者
        a2c_query = "SELECT COUNT(*) as count FROM follows_advertiser_to_collaborator WHERE advertiser_id = %s AND collaborator_id = %s"
        try:
            a2c_result = db.execute_one(a2c_query, (receiver_id, sender_id))
            print(f"[DEBUG] 合作者获取消息 - 广告主关注合作者检查结果: {a2c_result}")
        except Exception as e:
            print(f"[ERROR] 合作者获取消息 - 广告主关注合作者检查出错: {str(e)}")
            a2c_result = None
        
        # 如果两边都有关注记录，则认为是好友关系
        is_mutual = (c2a_result and c2a_result['count'] > 0) and (a2c_result and a2c_result['count'] > 0)
        print(f"[DEBUG] 合作者获取消息 - 最终互相关注检查结果: {is_mutual}")
        
        if not is_mutual:
            print(f"[DEBUG] 合作者获取消息 - 未通过好友关系检查，拒绝请求")
            return jsonify({
                'status': 'error',
                'message': '只能查看与好友的聊天记录'
            }), 403
        
        # 查询聊天记录
        query = """
            SELECT id, sender_id, receiver_id, content, is_read, created_at, 'sent' as type
            FROM messages_collaborator_to_advertiser
            WHERE sender_id = %s AND receiver_id = %s
            UNION
            SELECT id, sender_id, receiver_id, content, is_read, created_at, 'received' as type
            FROM messages_advertiser_to_collaborator
            WHERE sender_id = %s AND receiver_id = %s
            ORDER BY created_at ASC
        """
        try:
            messages = db.execute_query(query, (sender_id, receiver_id, receiver_id, sender_id))
            print(f"[DEBUG] 合作者获取消息 - 查询到 {len(messages)} 条消息")
        except Exception as e:
            print(f"[ERROR] 合作者获取消息 - 查询消息记录出错: {str(e)}")
            raise
        
        # 将消息标记为已读（仅接收到的消息）
        update_query = """
            UPDATE messages_advertiser_to_collaborator
            SET is_read = 1
            WHERE sender_id = %s AND receiver_id = %s AND is_read = 0
        """
        try:
            db.execute(update_query, (receiver_id, sender_id))
            print(f"[DEBUG] 合作者获取消息 - 已将消息标记为已读")
        except Exception as e:
            print(f"[ERROR] 合作者获取消息 - 标记消息为已读出错: {str(e)}")
        
        # 格式化消息数据
        formatted_messages = []
        for msg in messages:
            try:
                # 消息类型决定显示位置: sent显示在右侧，received显示在左侧
                is_sent = msg['type'] == 'sent'
                created_time = msg['created_at']
                
                # 格式化时间（根据需要调整）
                if isinstance(created_time, datetime):
                    time_str = created_time.strftime('%H:%M')
                else:
                    time_str = str(created_time)
                
                formatted_messages.append({
                    'id': msg['id'],
                    'content': msg['content'],
                    'is_sent': is_sent,  # 这是关键属性，决定消息显示在左侧还是右侧
                    'time': time_str,
                    'is_read': msg['is_read']
                })
            except Exception as e:
                print(f"[ERROR] 合作者获取消息 - 格式化消息 {msg['id']} 出错: {str(e)}")
        
        print(f"[DEBUG] 合作者获取消息 - 成功返回 {len(formatted_messages)} 条格式化消息")
        return jsonify({
            'status': 'success',
            'data': formatted_messages
        })
    except Exception as e:
        print(f"[ERROR] 合作者获取消息 - 处理请求时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500

@collaborator_bp.route('/api/send_message', methods=['POST'])
@collaborator_required
def send_message():
    """处理AJAX提交的消息发送请求"""
    try:
        # 获取合作者ID
        sender_id = session.get('user_id')
        
        # 获取参数
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '无效的请求数据'
            }), 400
            
        receiver_id = data.get('receiver_id')
        content = data.get('content', '').strip()
        
        # 验证参数
        if not receiver_id or not content:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            }), 400
            
        receiver_id = int(receiver_id)
            
        # 验证接收者是否存在
        receiver_query = "SELECT id FROM advertisers WHERE id = %s"
        receiver = db.execute_one(receiver_query, (receiver_id,))
        
        if not receiver:
            return jsonify({
                'status': 'error',
                'message': '接收者不存在'
            }), 404
            
        # 验证是否互相关注
        c2a_query = "SELECT COUNT(*) as count FROM follows_collaborator_to_advertiser WHERE collaborator_id = %s AND advertiser_id = %s"
        c2a_result = db.execute_one(c2a_query, (sender_id, receiver_id))
        
        a2c_query = "SELECT COUNT(*) as count FROM follows_advertiser_to_collaborator WHERE advertiser_id = %s AND collaborator_id = %s"
        a2c_result = db.execute_one(a2c_query, (receiver_id, sender_id))
        
        is_mutual = (c2a_result and c2a_result['count'] > 0) and (a2c_result and a2c_result['count'] > 0)
        
        if not is_mutual:
            return jsonify({
                'status': 'error',
                'message': '只能向好友发送消息'
            }), 403
            
        # 插入新消息
        insert_query = """
            INSERT INTO messages_collaborator_to_advertiser (sender_id, receiver_id, content, is_read, created_at)
            VALUES (%s, %s, %s, 0, NOW())
        """
        db.execute(insert_query, (sender_id, receiver_id, content))
        
        # 获取插入的消息
        message_query = """
            SELECT id, sender_id, receiver_id, content, is_read, created_at
            FROM messages_collaborator_to_advertiser
            WHERE sender_id = %s AND receiver_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        message = db.execute_one(message_query, (sender_id, receiver_id))
        
        if not message:
            return jsonify({
                'status': 'error',
                'message': '发送消息失败'
            }), 500
            
        # 格式化消息
        formatted_message = {
            'id': message['id'],
            'content': message['content'],
            'is_sent': True,  # 消息的发送者是当前用户
            'is_read': message['is_read'],
            'time': message['created_at'].strftime('%H:%M')
        }
        
        return jsonify({
            'status': 'success',
            'message': '消息发送成功',
            'data': formatted_message
        })
        
    except Exception as e:
        print(f"[ERROR] 合作者消息API - 处理请求时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500

@collaborator_bp.route('/withdraw', methods=['POST'])
@collaborator_required
def withdraw():
    user_id = session.get('user_id')
    amount = request.form.get('amount', 0)
    withdraw_method = request.form.get('withdraw_method', 'alipay')
    account = request.form.get('account', '')
    
    try:
        # 金额转换为浮点数
        amount = float(amount)
        
        # 验证金额
        if amount <= 0:
            flash('提现金额必须大于0', 'error')
            return redirect(url_for('collaborator.profile_finance'))
        
        # 获取当前用户余额
        collaborator = user_dao.get_user_by_id(user_id, 'collaborator')
        current_balance = float(collaborator.get('balance', 0))
        
        # 验证余额是否充足
        if amount > current_balance:
            flash('提现金额不能大于当前余额', 'error')
            return redirect(url_for('collaborator.profile_finance'))
        
        # 插入余额变动记录
        transaction_query = """
            INSERT INTO balance_transactions_collaborator 
            (collaborator_id, amount, description, created_at)
            VALUES (%s, %s, %s, NOW())
        """
        description = f"提现 - {withdraw_method} ({account})"
        db.execute(transaction_query, (user_id, -amount, description))
        
        # 更新用户余额 (减去提现金额)
        update_query = "UPDATE collaborators SET balance = balance - %s WHERE id = %s"
        db.execute(update_query, (amount, user_id))
        
        flash('提现申请已提交，资金将在1-3个工作日内到账', 'success')
    except ValueError:
        flash('请输入有效的金额', 'error')
    except Exception as e:
        print(f"提现处理错误: {str(e)}")
        flash('处理提现时出错，请稍后重试', 'error')
    
    return redirect(url_for('collaborator.profile_finance'))

# 添加获取未读消息总数的方法
def get_collaborator_unread_count(collaborator_id):
    """获取合作者的总未读消息数"""
    query = """
        SELECT COUNT(*) as count
        FROM messages_advertiser_to_collaborator
        WHERE receiver_id = %s AND is_read = 0
    """
    result = db.execute_one(query, (collaborator_id,))
    return result['count'] if result else 0

# 通知相关API路由
@collaborator_bp.route('/api/notifications/mark_read', methods=['POST'])
@collaborator_required
def mark_notification_read():
    """标记通知为已读"""
    try:
        notification_id = request.json.get('notification_id')
        collaborator_id = session.get('user_id')
        
        if not notification_id:
            return jsonify({'status': 'error', 'message': '通知ID不能为空'}), 400
        
        # 更新数据库
        query = """
            UPDATE system_notifications_collaborator 
            SET is_read = 1 
            WHERE id = %s AND collaborator_id = %s
        """
        db.execute(query, (notification_id, collaborator_id))
        
        # 简化判断逻辑，不再检查rowcount
        return jsonify({'status': 'success', 'message': '通知已标记为已读'})
            
    except Exception as e:
        print(f"标记通知为已读时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': '服务器内部错误'}), 500