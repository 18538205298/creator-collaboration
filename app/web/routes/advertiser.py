from flask import Blueprint, render_template, redirect, url_for, session, request, flash, jsonify, g
from app.web.auth_decorators import advertiser_required
from app.dao.user_dao import user_dao
from app.dao.collaborator_dao import collaborator_dao
from app.web.utils.notifications import notify_success, notify_error
from flask_paginate import get_page_parameter
from app.web.pagination import create_pagination
from werkzeug.utils import secure_filename
from app.config.settings import UPLOAD_FOLDER
from app.dao.database import db
import os
import uuid
from app.dao.collaboration_requests_dao import collaboration_requests_dao
from datetime import datetime, timedelta
from functools import wraps

advertiser_bp = Blueprint('advertiser', __name__)

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
        advertiser_id = session.get('user_id')
        if not advertiser_id:
            return result
        
        # 获取未读消息总数
        unread_count = get_advertiser_unread_count(advertiser_id)
        
        # 将未读消息总数添加到模板上下文
        if hasattr(result, '_TemplateReference__context'):
            ctx = result._TemplateReference__context
            ctx['total_unread_count'] = unread_count
        
        return result
    
    return wrapper

# 修改所有路由装饰器，添加未读消息总数装饰器
advertiser_bp.before_request(lambda: None)

@advertiser_bp.before_request
def before_request():
    # 如果是广告主登录页面或不需要登录的页面，则不处理
    if not session.get('user_id') or not session.get('user_type') == 'advertiser':
        return
    
    # 获取用户ID
    advertiser_id = session.get('user_id')
    
    # 获取未读消息总数
    unread_count = get_advertiser_unread_count(advertiser_id)
    
    # 将未读消息总数保存到g对象中，以便在模板中使用
    g.total_unread_count = unread_count

# 添加获取待处理请求数量的方法
def get_advertiser_pending_requests_count(advertiser_id):
    """获取广告主收到的待处理请求数量"""
    query = """
        SELECT COUNT(*) as count
        FROM collaboration_requests_collaborator
        WHERE advertiser_id = %s AND status = 'pending'
    """
    result = db.execute_one(query, (advertiser_id,))
    return result['count'] if result else 0

# 修改模板过滤器，添加全局变量
@advertiser_bp.context_processor
def inject_unread_count():
    unread_count = getattr(g, 'total_unread_count', 0)
    # 如果用户已登录，则获取待处理请求数量
    pending_requests_count = 0
    if session.get('user_id') and session.get('user_type') == 'advertiser':
        advertiser_id = session.get('user_id')
        pending_requests_count = get_advertiser_pending_requests_count(advertiser_id)
    
    return {
        'total_unread_count': unread_count,
        'pending_requests_count': pending_requests_count
    }

# 首页相关路由
@advertiser_bp.route('/home')
@advertiser_required
def home():
    # 明确重定向到概览页面
    return redirect(url_for('advertiser.home_overview'))

@advertiser_bp.route('/home/overview')
@advertiser_required
def home_overview():
    # 获取用户ID
    advertiser_id = session.get('user_id')
    
    # 获取广告主基本信息
    advertiser = user_dao.get_user_by_id(advertiser_id, 'advertiser')
    
    # 获取任务统计数据
    tasks_query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) as draft,
            SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) as published,
            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
        FROM ad_tasks
        WHERE advertiser_id = %s
    """
    tasks_stats = db.execute_one(tasks_query, (advertiser_id,))
    
    # 任务浏览量统计
    views_query = """
        SELECT COUNT(*) as count
        FROM view_history_collaborator vhc
        JOIN ad_tasks at ON vhc.task_id = at.id
        WHERE at.advertiser_id = %s
    """
    views_stats = db.execute_one(views_query, (advertiser_id,))
    
    # 收藏的合作者数量
    favorite_collaborators_query = """
        SELECT COUNT(*) as count
        FROM favorites_advertiser
        WHERE advertiser_id = %s
    """
    favorite_collaborators_stats = db.execute_one(favorite_collaborators_query, (advertiser_id,))
    
    # 关注的合作者数量
    followed_collaborators_query = """
        SELECT COUNT(*) as count
        FROM follows_advertiser_to_collaborator
        WHERE advertiser_id = %s
    """
    followed_collaborators_stats = db.execute_one(followed_collaborators_query, (advertiser_id,))
    
    # 获取合作请求统计
    requests_advertiser_query = """
        SELECT 
            COUNT(*) as sent,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
        FROM collaboration_requests_advertiser
        WHERE advertiser_id = %s
    """
    advertiser_requests = db.execute_one(requests_advertiser_query, (advertiser_id,))
    
    requests_collaborator_query = """
        SELECT COUNT(*) as received
        FROM collaboration_requests_collaborator
        WHERE advertiser_id = %s
    """
    collaborator_requests = db.execute_one(requests_collaborator_query, (advertiser_id,))
    
    # 获取消息统计
    sent_messages_query = """
        SELECT COUNT(*) as count
        FROM messages_advertiser_to_collaborator
        WHERE sender_id = %s
    """
    sent_messages = db.execute_one(sent_messages_query, (advertiser_id,))
    
    received_messages_query = """
        SELECT COUNT(*) as count, SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as unread
        FROM messages_collaborator_to_advertiser
        WHERE receiver_id = %s
    """
    received_messages = db.execute_one(received_messages_query, (advertiser_id,))
    
    # 计算消息回复率
    total_received = received_messages['count'] if received_messages else 0
    total_sent = sent_messages['count'] if sent_messages else 0
    
    if total_received > 0:
        message_response_rate = f"{(total_sent / total_received * 100):.1f}%"
    else:
        message_response_rate = "0%"
    
    # 获取最新广告任务
    recent_tasks_query = """
        SELECT id, title, budget, status, deadline, views_count, applications_count, created_at
        FROM ad_tasks
        WHERE advertiser_id = %s
        ORDER BY created_at DESC
        LIMIT 5
    """
    recent_tasks = db.execute_query(recent_tasks_query, (advertiser_id,))
    
    # 获取收藏的合作者信息
    favorite_collaborators_data_query = """
        SELECT c.id, c.username, c.platform, c.avatar_url, c.followers_count, c.likes_count,
               c.content_domain, c.content_style, c.previous_collaboration_count
        FROM favorites_advertiser fa
        JOIN collaborators c ON fa.collaborator_id = c.id
        WHERE fa.advertiser_id = %s
        ORDER BY fa.created_at DESC
        LIMIT 8
    """
    favorite_collaborators = db.execute_query(favorite_collaborators_data_query, (advertiser_id,))
    
    # 为任务状态添加显示名称
    for task in recent_tasks:
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
    
    # 准备模板数据
    template_data = {
        'active_tab': 'overview',
        'total_tasks_count': tasks_stats['total'] if tasks_stats and 'total' in tasks_stats else 0,
        'active_tasks_count': (tasks_stats.get('published') or 0) + (tasks_stats.get('in_progress') or 0),
        'completed_tasks_count': tasks_stats['completed'] if tasks_stats and 'completed' in tasks_stats else 0,
        'draft_tasks_count': tasks_stats['draft'] if tasks_stats and 'draft' in tasks_stats else 0,
        'published_tasks_count': tasks_stats['published'] if tasks_stats and 'published' in tasks_stats else 0,
        'inprogress_tasks_count': tasks_stats['in_progress'] if tasks_stats and 'in_progress' in tasks_stats else 0,
        'cancelled_tasks_count': tasks_stats['cancelled'] if tasks_stats and 'cancelled' in tasks_stats else 0,
        'received_applications_count': collaborator_requests['received'] if collaborator_requests and 'received' in collaborator_requests else 0,
        'sent_invitations_count': advertiser_requests['sent'] if advertiser_requests and 'sent' in advertiser_requests else 0,
        'pending_requests_count': advertiser_requests['pending'] if advertiser_requests and 'pending' in advertiser_requests else 0,
        'total_views_count': views_stats['count'] if views_stats and 'count' in views_stats else 0,
        'favorite_collaborators_count': favorite_collaborators_stats['count'] if favorite_collaborators_stats and 'count' in favorite_collaborators_stats else 0,
        'followed_collaborators_count': followed_collaborators_stats['count'] if followed_collaborators_stats and 'count' in followed_collaborators_stats else 0,
        'sent_messages_count': total_sent,
        'received_messages_count': total_received,
        'unread_messages_count': received_messages['unread'] if received_messages and 'unread' in received_messages else 0,
        'message_response_rate': message_response_rate,
        'recent_tasks': recent_tasks,
        'favorite_collaborators': favorite_collaborators
    }
    
    return render_template('advertiser/home/overview.html', **template_data)

@advertiser_bp.route('/home/recommended')
@advertiser_required
def home_recommended():
    # 获取当前广告主ID
    advertiser_id = session.get('user_id')
    if not advertiser_id:
        advertiser_id = 101  # 默认使用ID为101的广告主进行测试
    
    # 初始化推荐服务
    from app.domain.advertiser.recommender_service import AdvertiserRecommenderService
    recommender_service = AdvertiserRecommenderService()
    
    # 使用推荐服务获取推荐合作者
    try:
        trending_collaborators = recommender_service.get_trending_collaborators(limit=3)
        print(f"获取到 {len(trending_collaborators) if trending_collaborators else 0} 个热门合作者")
    except Exception as e:
        print(f"获取热门合作者出错: {str(e)}")
        trending_collaborators = []
    
    try:
        new_collaborators = recommender_service.get_new_rising_collaborators(limit=2)
        print(f"获取到 {len(new_collaborators) if new_collaborators else 0} 个新晋合作者")
    except Exception as e:
        print(f"获取新晋合作者出错: {str(e)}")
        new_collaborators = []
    
    # 自定义推荐合作者 - 基于广告主的特定需求
    try:
        recommended_collaborators = recommender_service.get_recommended_collaborators(advertiser_id, limit=5)
        print(f"获取到 {len(recommended_collaborators) if recommended_collaborators else 0} 个推荐合作者")
    except Exception as e:
        print(f"获取推荐合作者出错: {str(e)}")
        recommended_collaborators = []
    
    # 如果没有获取到任何推荐数据，则提供一些模拟数据确保界面有内容显示
    if not trending_collaborators and not new_collaborators and not recommended_collaborators:
        print("所有推荐列表为空，使用模拟数据")
        # 模拟数据
        mock_collaborator = {
            'id': 1,
            'username': '测试合作者',
            'avatar_url': None,
            'followers_count': 25000,
            'likes_count': 100000,
            'content_domain': '测试领域',
            'content_style': '测试风格',
            'platform': '测试平台',
            'previous_collaboration_count': 5
        }
        recommended_collaborators = [mock_collaborator.copy() for _ in range(3)]
        trending_collaborators = [mock_collaborator.copy() for _ in range(2)]
        trending_collaborators[0]['username'] = '热门合作者1'
        trending_collaborators[1]['username'] = '热门合作者2'
        new_collaborators = [mock_collaborator.copy() for _ in range(2)]
        new_collaborators[0]['username'] = '新晋合作者1'
        new_collaborators[1]['username'] = '新晋合作者2'
    
    return render_template(
        'advertiser/home/recommended.html', 
        active_tab='recommended',
        trending_collaborators=trending_collaborators,
        new_collaborators=new_collaborators,
        recommended_collaborators=recommended_collaborators
    )

@advertiser_bp.route('/home/notifications')
@advertiser_required
def home_notifications():
    # 获取当前广告主ID
    advertiser_id = session.get('user_id')
    
    # 从数据库获取系统通知
    query = """
        SELECT * FROM system_notifications_advertiser 
        WHERE advertiser_id = %s 
        ORDER BY created_at DESC
    """
    notifications = db.execute_query(query, (advertiser_id,))
    
    return render_template('advertiser/home/notifications.html', 
                           active_tab='notifications',
                           notifications=notifications)

# 广告任务相关路由
@advertiser_bp.route('/ad_tasks')
@advertiser_required
def ad_tasks():
    # 重定向到广告任务创建页面
    return redirect(url_for('advertiser.ad_tasks_create'))

@advertiser_bp.route('/ad_tasks/create')
@advertiser_required
def ad_tasks_create():
    return render_template('advertiser/ad_tasks/create.html', active_tab='create')

@advertiser_bp.route('/ad_tasks/pending')
@advertiser_required
def ad_tasks_pending():
    # 获取用户ID
    advertiser_id = session.get('user_id')
    
    # 获取该广告主状态为published的任务
    query = """
        SELECT at.*, 
               c.username as collaborator_name, 
               c.avatar_url as collaborator_avatar,
               c.platform as collaborator_platform,
               c.id as collaborator_id,
               at.created_at as collaboration_start_time
        FROM ad_tasks at
        LEFT JOIN collaboration_requests_collaborator cr ON at.id = cr.ad_task_id
        LEFT JOIN collaborators c ON cr.collaborator_id = c.id
        WHERE at.advertiser_id = %s AND at.status = 'published'
        ORDER BY at.created_at DESC
    """
    
    pending_tasks = db.execute_query(query, (advertiser_id,))
    
    return render_template('advertiser/ad_tasks/pending.html', 
                          active_tab='pending',
                          pending_tasks=pending_tasks)

@advertiser_bp.route('/ad_tasks/completed')
@advertiser_required
def ad_tasks_completed():
    # 获取用户ID
    advertiser_id = session.get('user_id')
    
    # 获取该广告主状态为completed的任务
    query = """
        SELECT at.*, 
               c.username as collaborator_name, 
               c.avatar_url as collaborator_avatar,
               c.platform as collaborator_platform,
               c.id as collaborator_id,
               cr.created_at as collaboration_start_time
        FROM ad_tasks at
        LEFT JOIN collaboration_requests_collaborator cr ON at.id = cr.ad_task_id AND cr.status = 'accepted'
        LEFT JOIN collaborators c ON cr.collaborator_id = c.id
        WHERE at.advertiser_id = %s AND at.status = 'completed'
        ORDER BY at.updated_at DESC
    """
    
    completed_tasks = db.execute_query(query, (advertiser_id,))
    
    return render_template('advertiser/ad_tasks/completed.html', 
                          active_tab='completed',
                          completed_tasks=completed_tasks)

@advertiser_bp.route('/ad_tasks/ongoing')
@advertiser_required
def ad_tasks_ongoing():
    # 获取用户ID
    advertiser_id = session.get('user_id')
    
    # 获取该广告主状态为in_progress的任务
    query = """
        SELECT at.*, 
               c.username as collaborator_name, 
               c.avatar_url as collaborator_avatar,
               c.platform as collaborator_platform,
               c.id as collaborator_id,
               COALESCE(crc.created_at, cra.created_at) as collaboration_start_time
        FROM ad_tasks at
        LEFT JOIN (
            SELECT ad_task_id, collaborator_id, created_at 
            FROM collaboration_requests_collaborator 
            WHERE status = 'accepted'
        ) crc ON at.id = crc.ad_task_id
        LEFT JOIN (
            SELECT ad_task_id, collaborator_id, created_at 
            FROM collaboration_requests_advertiser 
            WHERE status = 'accepted'
        ) cra ON at.id = cra.ad_task_id
        LEFT JOIN collaborators c ON COALESCE(crc.collaborator_id, cra.collaborator_id) = c.id
        WHERE at.advertiser_id = %s AND at.status = 'in_progress'
        ORDER BY COALESCE(crc.created_at, cra.created_at) DESC
    """
    
    ongoing_tasks = db.execute_query(query, (advertiser_id,))
    
    return render_template('advertiser/ad_tasks/ongoing.html', 
                          active_tab='ongoing',
                          ongoing_tasks=ongoing_tasks)

@advertiser_bp.route('/ad_tasks/cancelled')
@advertiser_required
def ad_tasks_cancelled():
    # 获取用户ID
    advertiser_id = session.get('user_id')
    
    # 获取该广告主状态为cancelled的任务
    query = """
        SELECT at.*, 
               c.username as collaborator_name, 
               c.avatar_url as collaborator_avatar,
               c.platform as collaborator_platform,
               c.id as collaborator_id,
               cr.created_at as collaboration_start_time
        FROM ad_tasks at
        LEFT JOIN collaboration_requests_collaborator cr ON at.id = cr.ad_task_id AND cr.status = 'accepted'
        LEFT JOIN collaborators c ON cr.collaborator_id = c.id
        WHERE at.advertiser_id = %s AND at.status = 'cancelled'
        ORDER BY at.updated_at DESC
    """
    
    cancelled_tasks = db.execute_query(query, (advertiser_id,))
    
    return render_template('advertiser/ad_tasks/cancelled.html', 
                          active_tab='cancelled',
                          cancelled_tasks=cancelled_tasks)

# 合作者查找相关路由
@advertiser_bp.route('/collaborator_search')
@advertiser_required
def collaborator_search():
    # 重定向到合作者列表页面
    return redirect(url_for('advertiser.collaborator_search_list'))

@advertiser_bp.route('/collaborator_search/list')
@advertiser_required
def collaborator_search_list():
    try:
        # 获取筛选参数
        platform = request.args.get('platform', '')
        content_format = request.args.get('content_format', '')
        content_domain = request.args.get('content_domain', '')
        min_followers = request.args.get('min_followers', '')
        content_style = request.args.get('content_style', '')
        keyword = request.args.get('keyword', '')
        
        # 构建筛选参数字典
        filters = {}
        if platform:
            filters['platform'] = platform
        if content_format:
            filters['content_format'] = content_format
        if content_domain:
            filters['content_domain'] = content_domain
        if min_followers and min_followers.isdigit():
            filters['min_followers'] = int(min_followers)
        if content_style:
            filters['content_style'] = content_style
        if keyword:
            filters['search_keyword'] = keyword  # 注意：这里使用search_keyword
        
        # 获取当前页码
        page = request.args.get('page', 1, type=int)
        per_page = 12
        offset = (page - 1) * per_page
        
        # 使用正确的静态方法调用
        from app.dao.collaborator_dao import CollaboratorDAO
        
        # 先尝试使用get_collaborators_count获取总数
        try:
            total = CollaboratorDAO.get_collaborators_count()
        except:
            # 如果出错，回退到获取所有合作者并计数
            all_collaborators = CollaboratorDAO.get_all_collaborators()
            total = len(all_collaborators) if all_collaborators else 0
        
        # 获取分页后的数据
        collaborators = CollaboratorDAO.get_collaborators_by_filters(
            filters=filters, 
            limit=per_page, 
            offset=offset
        )
        
        # 创建分页对象
        pagination_data = create_pagination(
            total_items=total,
            per_page=per_page,
            record_name='合作者'
        )
        
        # 获取当前用户收藏的合作者ID列表
        user_id = session.get('user_id')
        # 实例化CollaboratorDAO
        dao = CollaboratorDAO()
        favorite_collaborator_ids = dao.get_user_favorite_collaborator_ids(user_id) or []
        
        return render_template('advertiser/collaborator_search/list.html', 
                           active_tab='list',
                           collaborators=collaborators or [],
                           pagination=pagination_data['pagination'],
                           favorite_collaborator_ids=favorite_collaborator_ids)
    except Exception as e:
        print(f"加载合作者列表页面出错: {str(e)}")
        notify_error('加载页面时发生错误，请稍后重试')
        return redirect(url_for('advertiser.home'))

@advertiser_bp.route('/collaborator_search/detail/<int:id>')
@advertiser_required
def collaborator_detail(id):
    try:
        # 获取指定ID的合作者详细信息
        collaborator = user_dao.get_collaborator_by_id(id)
        
        if not collaborator:
            notify_error('未找到该合作者')
            return redirect(url_for('advertiser.collaborator_search_list'))
        
        # 获取用户ID
        advertiser_id = session.get('user_id')
        
        # 记录浏览历史
        try:
            now = datetime.now()
            # 检查是否已有浏览记录
            check_query = """
                SELECT id FROM view_history_advertiser 
                WHERE advertiser_id = %s AND collaborator_id = %s
            """
            history = db.execute_one(check_query, (advertiser_id, id))
            
            if history:
                # 更新最近浏览时间
                update_query = """
                    UPDATE view_history_advertiser 
                    SET viewed_at = %s
                    WHERE advertiser_id = %s AND collaborator_id = %s
                """
                db.execute(update_query, (now, advertiser_id, id))
            else:
                # 创建新的浏览记录
                insert_query = """
                    INSERT INTO view_history_advertiser (advertiser_id, collaborator_id, viewed_at)
                    VALUES (%s, %s, %s)
                """
                db.execute(insert_query, (advertiser_id, id, now))
        except Exception as e:
            print(f"记录浏览历史时出错: {str(e)}")
        
        # 检查是否收藏
        try:
            favorite_query = """
                SELECT id FROM favorites_advertiser 
                WHERE advertiser_id = %s AND collaborator_id = %s
            """
            is_favorite = bool(db.execute_one(favorite_query, (advertiser_id, id)))
        except Exception as e:
            print(f"检查收藏状态时出错: {str(e)}")
            is_favorite = False
        
        # 检查是否关注
        try:
            follow_query = """
                SELECT id FROM follows_advertiser_to_collaborator 
                WHERE advertiser_id = %s AND collaborator_id = %s
            """
            is_following = bool(db.execute_one(follow_query, (advertiser_id, id)))
        except Exception as e:
            print(f"检查关注状态时出错: {str(e)}")
            is_following = False
        
        # 准备详细数据以供模板渲染，确保数据安全
        stats = {
            'likes_count': collaborator.get('likes_count', 0) or 0,
            'favorites_count': collaborator.get('favorites_count', 0) or 0,
            'shares_count': collaborator.get('shares_count', 0) or 0,
            'comments_count': collaborator.get('comments_count', 0) or 0,
            'clicks_count': collaborator.get('clicks_count', 0) or 0,
            'previous_collaboration_count': collaborator.get('previous_collaboration_count', 0) or 0
        }
        
        return render_template('advertiser/collaborator_search/detail.html',
                          active_tab='list',
                          collaborator=collaborator,
                          stats=stats,
                          is_favorite=is_favorite,
                          is_following=is_following)
    except Exception as e:
        print(f"查看合作者详情页面出错: {str(e)}")
        notify_error('加载页面时发生错误，请稍后重试')
        return redirect(url_for('advertiser.collaborator_search_list'))

@advertiser_bp.route('/api/favorite/add/<int:collaborator_id>', methods=['POST'])
@advertiser_required
def add_favorite(collaborator_id):
    try:
        user_id = session.get('user_id')
        # 创建DAO实例
        from app.dao.collaborator_dao import CollaboratorDAO
        dao = CollaboratorDAO()
        result = dao.add_favorite(user_id, collaborator_id)
        if result:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "添加收藏失败"}), 500
    except Exception as e:
        print(f"添加收藏出错: {str(e)}")
        return jsonify({"status": "error", "message": "服务器错误"}), 500

@advertiser_bp.route('/api/favorite/remove/<int:collaborator_id>', methods=['POST'])
@advertiser_required
def remove_favorite(collaborator_id):
    try:
        user_id = session.get('user_id')
        # 创建DAO实例
        from app.dao.collaborator_dao import CollaboratorDAO
        dao = CollaboratorDAO()
        result = dao.remove_favorite(user_id, collaborator_id)
        if result:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "取消收藏失败"}), 500
    except Exception as e:
        print(f"取消收藏出错: {str(e)}")
        return jsonify({"status": "error", "message": "服务器错误"}), 500

@advertiser_bp.route('/collaborator_search/favorites')
@advertiser_required
def collaborator_search_favorites():
    try:
        # 获取用户ID
        user_id = session.get('user_id')
        
        # 创建DAO实例
        from app.dao.collaborator_dao import CollaboratorDAO
        dao = CollaboratorDAO()
        
        # 获取收藏合作者总数
        total_favorites = dao.count_favorite_collaborators(user_id)
        
        # 使用通用分页工具
        pagination_data = create_pagination(
            total_items=total_favorites,
            per_page=12,
            record_name='收藏合作者'
        )
        
        # 获取当前页的收藏合作者
        page = pagination_data['page']
        per_page = pagination_data['per_page']
        
        favorite_collaborators = []
        if total_favorites > 0:
            favorites, _ = dao.get_favorite_collaborators(user_id, page, per_page)
            favorite_collaborators = favorites or []
        
        return render_template('advertiser/collaborator_search/favorites.html', 
                          active_tab='favorites',
                          collaborators=favorite_collaborators,
                          pagination=pagination_data['pagination'])
    except Exception as e:
        print(f"查看收藏合作者列表出错: {str(e)}")
        notify_error('加载收藏列表时出错，请稍后重试')
        return redirect(url_for('advertiser.home'))

@advertiser_bp.route('/collaborator_search/history')
@advertiser_required
def collaborator_search_history():
    try:
        # 获取用户ID
        user_id = session.get('user_id')
        
        # 创建DAO实例
        from app.dao.collaborator_dao import CollaboratorDAO
        dao = CollaboratorDAO()
        
        # 获取浏览历史总数
        total_history = dao.count_view_history(user_id)
        
        # 使用通用分页工具
        pagination_data = create_pagination(
            total_items=total_history,
            per_page=12,
            record_name='浏览历史'
        )
        
        # 获取当前页的浏览历史
        page = pagination_data['page']
        per_page = pagination_data['per_page']
        
        view_history = []
        if total_history > 0:
            history = dao.get_view_history(user_id, page, per_page)
            view_history = history or []
        
        return render_template('advertiser/collaborator_search/history.html', 
                          active_tab='history',
                          collaborators=view_history,
                          pagination=pagination_data['pagination'])
    except Exception as e:
        print(f"查看浏览历史出错: {str(e)}")
        notify_error('加载浏览历史时出错，请稍后重试')
        return redirect(url_for('advertiser.home'))

# 合作请求相关路由
@advertiser_bp.route('/collaboration_requests')
@advertiser_required
def collaboration_requests():
    # 重定向到已发送请求页面
    return redirect(url_for('advertiser.collaboration_requests_sent'))

@advertiser_bp.route('/collaboration_requests/sent')
@advertiser_required
def collaboration_requests_sent():
    # 检查是否需要显示取消成功的flash消息
    if session.pop('show_cancel_success', False):
        notify_success('合作请求已成功取消', duration=3000)
    
    # 获取用户ID
    advertiser_id = session.get('user_id')
    
    # 获取该广告主发送的所有合作请求
    sent_requests = collaboration_requests_dao.get_advertiser_sent_requests(advertiser_id)
    
    # 按状态分组
    grouped_requests = collaboration_requests_dao.group_by_status(sent_requests)
    
    return render_template('advertiser/collaboration_requests/sent.html', 
                          active_tab='sent',
                          pending_requests=grouped_requests['pending'],
                          accepted_requests=grouped_requests['accepted'],
                          rejected_requests=grouped_requests['rejected'],
                          canceled_requests=grouped_requests['canceled'])

@advertiser_bp.route('/collaboration_requests/received')
@advertiser_required
def collaboration_requests_received():
    # 获取用户ID
    advertiser_id = session.get('user_id')
    
    # 获取该广告主收到的所有合作请求
    received_requests = collaboration_requests_dao.get_advertiser_received_requests(advertiser_id)
    
    # 按状态分组
    grouped_requests = collaboration_requests_dao.group_by_status(received_requests)
    
    return render_template('advertiser/collaboration_requests/received.html', 
                          active_tab='received',
                          pending_requests=grouped_requests['pending'],
                          accepted_requests=grouped_requests['accepted'],
                          rejected_requests=grouped_requests['rejected'],
                          canceled_requests=grouped_requests['canceled'])

# 消息中心相关路由
@advertiser_bp.route('/messages')
@advertiser_required
def messages():
    # 重定向到我的关注页面
    return redirect(url_for('advertiser.messages_following'))

@advertiser_bp.route('/messages/following')
@advertiser_required
def messages_following():
    advertiser_id = session.get('user_id')
    
    # 获取广告主关注的合作者列表
    query = """
        SELECT c.*
        FROM follows_advertiser_to_collaborator f
        JOIN collaborators c ON f.collaborator_id = c.id
        WHERE f.advertiser_id = %s
        ORDER BY f.created_at DESC
    """
    following_list = db.execute_query(query, (advertiser_id,))
    
    # 获取总未读消息数
    total_unread_count = get_advertiser_unread_count(advertiser_id)
    
    return render_template('advertiser/messages/following.html', 
                          active_tab='following',
                          following_list=following_list,
                          total_unread_count=total_unread_count)

@advertiser_bp.route('/messages/followers')
@advertiser_required
def messages_followers():
    advertiser_id = session.get('user_id')
    
    # 获取关注该广告主的合作者列表，并检查广告主是否已关注这些合作者
    query = """
        SELECT c.*,
               (SELECT COUNT(1) FROM follows_advertiser_to_collaborator 
                WHERE advertiser_id = %s AND collaborator_id = c.id) > 0 AS is_following
        FROM follows_collaborator_to_advertiser f
        JOIN collaborators c ON f.collaborator_id = c.id
        WHERE f.advertiser_id = %s
        ORDER BY f.created_at DESC
    """
    followers_list = db.execute_query(query, (advertiser_id, advertiser_id))
    
    # 获取总未读消息数
    total_unread_count = get_advertiser_unread_count(advertiser_id)
    
    return render_template('advertiser/messages/followers.html', 
                          active_tab='followers',
                          followers_list=followers_list,
                          total_unread_count=total_unread_count)

@advertiser_bp.route('/messages/inbox')
@advertiser_required
def messages_inbox():
    advertiser_id = session.get('user_id')
    
    # 获取相互关注的好友（广告主和合作者互相关注）
    query = """
        SELECT c.*, NULL as last_message, NULL as last_message_time, 0 as unread_count
        FROM follows_advertiser_to_collaborator a2c
        JOIN follows_collaborator_to_advertiser c2a ON a2c.collaborator_id = c2a.collaborator_id
        JOIN collaborators c ON c.id = a2c.collaborator_id
        WHERE a2c.advertiser_id = %s AND c2a.advertiser_id = %s
        ORDER BY c.username
    """
    mutual_friends = db.execute_query(query, (advertiser_id, advertiser_id))
    
    # 计算每个好友的未读消息数
    total_unread_count = 0
    for friend in mutual_friends:
        unread_query = """
            SELECT COUNT(*) as count
            FROM messages_collaborator_to_advertiser
            WHERE sender_id = %s AND receiver_id = %s AND is_read = 0
        """
        unread_result = db.execute_one(unread_query, (friend['id'], advertiser_id))
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
                    FROM messages_advertiser_to_collaborator
                    WHERE sender_id = %s AND receiver_id = %s
                    UNION
                    SELECT id, sender_id, receiver_id, content, is_read, created_at, 'received' as type
                    FROM messages_collaborator_to_advertiser
                    WHERE sender_id = %s AND receiver_id = %s
                    ORDER BY created_at ASC
                """
                raw_messages = db.execute_query(messages_query, (advertiser_id, contact_id, contact_id, advertiser_id))
                
                # 将消息标记为已读（仅接收到的消息）
                update_query = """
                    UPDATE messages_collaborator_to_advertiser
                    SET is_read = 1
                    WHERE sender_id = %s AND receiver_id = %s AND is_read = 0
                """
                db.execute(update_query, (contact_id, advertiser_id))
                
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
            print(f"[ERROR] 广告主消息页面 - 加载消息时出错: {str(e)}")
    
    return render_template('advertiser/messages/inbox.html', 
                          active_tab='inbox',
                          mutual_friends=mutual_friends,
                          active_contact=active_contact,
                          messages=messages,
                          total_unread_count=total_unread_count)

@advertiser_bp.route('/messages/send', methods=['POST'])
@advertiser_required
def send_message_post():
    """处理表单提交的消息发送请求"""
    try:
        # 获取广告主ID
        sender_id = session.get('user_id')
        
        # 获取接收者ID和消息内容
        receiver_id = request.form.get('receiver_id', None)
        content = request.form.get('content', '').strip()
        
        # 验证数据
        if not receiver_id or not content:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': '消息内容不能为空'})
            notify_error('消息内容不能为空')
            return redirect(url_for('advertiser.messages_inbox'))
            
        receiver_id = int(receiver_id)
        
        # 验证接收者是否存在
        receiver_query = "SELECT id FROM collaborators WHERE id = %s"
        receiver = db.execute_one(receiver_query, (receiver_id,))
        
        if not receiver:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': '接收者不存在'})
            notify_error('接收者不存在')
            return redirect(url_for('advertiser.messages_inbox'))
        
        # 验证是否互相关注
        a2c_query = "SELECT COUNT(*) as count FROM follows_advertiser_to_collaborator WHERE advertiser_id = %s AND collaborator_id = %s"
        a2c_result = db.execute_one(a2c_query, (sender_id, receiver_id))
        
        c2a_query = "SELECT COUNT(*) as count FROM follows_collaborator_to_advertiser WHERE collaborator_id = %s AND advertiser_id = %s"
        c2a_result = db.execute_one(c2a_query, (receiver_id, sender_id))
        
        is_mutual = (a2c_result and a2c_result['count'] > 0) and (c2a_result and c2a_result['count'] > 0)
        
        if not is_mutual:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': '只能向好友发送消息'})
            notify_error('只能向好友发送消息')
            return redirect(url_for('advertiser.messages_inbox'))
        
        # 插入新消息
        insert_query = """
            INSERT INTO messages_advertiser_to_collaborator (sender_id, receiver_id, content, is_read, created_at)
            VALUES (%s, %s, %s, 0, NOW())
        """
        result = db.execute(insert_query, (sender_id, receiver_id, content))
        
        if not result:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': '发送消息失败，请稍后重试'})
            notify_error('发送消息失败，请稍后重试')
            return redirect(url_for('advertiser.messages_inbox', contact_id=receiver_id))
            
        # 如果是Ajax请求，返回JSON响应
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
            
        # 否则重定向回聊天页面
        return redirect(url_for('advertiser.messages_inbox', contact_id=receiver_id))
        
    except Exception as e:
        print(f"[ERROR] 广告主发送消息表单处理 - 出错: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': '服务器内部错误，请稍后重试'})
        notify_error('服务器内部错误，请稍后重试')
        return redirect(url_for('advertiser.messages_inbox'))

# 个人中心相关路由
@advertiser_bp.route('/profile')
@advertiser_required
def profile():
    # 重定向到基本资料页面
    return redirect(url_for('advertiser.profile_basic'))

@advertiser_bp.route('/profile/basic')
@advertiser_required
def profile_basic():
    user_id = session.get('user_id')
    advertiser = user_dao.get_user_by_id(user_id, 'advertiser')
    
    # 计算已完成广告任务的数量和总预算
    completed_tasks_query = """
        SELECT COUNT(*) as completed_count, COALESCE(SUM(budget), 0) as total_budget
        FROM ad_tasks
        WHERE advertiser_id = %s AND status = 'completed'
    """
    task_stats = db.execute_one(completed_tasks_query, (user_id,))
    
    # 计算平均预算
    completed_count = int(task_stats['completed_count']) if task_stats else 0
    total_budget = float(task_stats['total_budget']) if task_stats else 0
    average_budget = 0
    if completed_count > 0:
        average_budget = round(total_budget / completed_count, 2)
    
    # 准备统计数据
    stats = {
        'balance': float(advertiser.get('balance', 0.00)),
        'previous_collaboration_count': completed_count,
        'average_budget': average_budget,
    }
    
    return render_template('advertiser/profile/basic.html', 
                          active_tab='basic', 
                          advertiser=advertiser,
                          stats=stats)

@advertiser_bp.route('/profile/edit')
@advertiser_required
def profile_edit():
    user_id = session.get('user_id')
    advertiser = user_dao.get_user_by_id(user_id, 'advertiser')
    return render_template('advertiser/profile/edit.html', active_tab='edit', advertiser=advertiser)

@advertiser_bp.route('/profile/save', methods=['POST'])
@advertiser_required
def profile_save():
    user_id = session.get('user_id')
    print(f"处理广告主ID {user_id} 的个人资料保存请求")
    
    # 获取表单数据
    company_name = request.form.get('company_name')
    industry = request.form.get('industry')
    email = request.form.get('email')
    phone_number = request.form.get('phone_number')
    
    # 准备更新数据
    update_data = {
        'company_name': company_name,
        'industry': industry,
        'email': email,
        'phone_number': phone_number
    }
    
    # 处理密码修改
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if old_password and new_password and confirm_password:
        # 验证当前密码
        advertiser = user_dao.get_user_by_id(user_id, 'advertiser')
        if old_password != advertiser['password']:  # 实际应用中应使用安全的密码验证
            # 密码错误
            flash('当前密码不正确', 'error')
            return redirect(url_for('advertiser.profile_edit'))
            
        if new_password != confirm_password:
            # 新密码与确认密码不匹配
            flash('新密码与确认密码不匹配', 'error')
            return redirect(url_for('advertiser.profile_edit'))
            
        # 更新密码
        update_data['password'] = new_password  # 实际应用中应对密码进行哈希处理
    
    # 处理头像上传
    if 'avatar_upload' in request.files:
        print("表单中包含avatar_upload字段")
        avatar_file = request.files['avatar_upload']
        if avatar_file and avatar_file.filename:
            print(f"收到文件上传: {avatar_file.filename}")
            # 检查文件类型
            allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
            file_ext = os.path.splitext(avatar_file.filename)[1].lower().lstrip('.')
            
            print(f"文件扩展名: {file_ext}")
            
            if file_ext not in allowed_extensions:
                flash(f'不支持的文件类型，请上传 {", ".join(allowed_extensions)} 格式的图片', 'error')
                return redirect(url_for('advertiser.profile_edit'))
            
            # 获取当前用户的头像信息
            current_advertiser = user_dao.get_user_by_id(user_id, 'advertiser')
            current_avatar = current_advertiser.get('avatar_url')
            
            print(f"当前头像: {current_avatar}")
            
            # 删除旧头像文件（如果不是默认头像）
            if current_avatar and current_avatar != 'default_advertiser.png':
                old_avatar_path = os.path.join(UPLOAD_FOLDER, 'avatars', current_avatar)
                print(f"尝试删除旧头像: {old_avatar_path}")
                if os.path.exists(old_avatar_path):
                    try:
                        os.remove(old_avatar_path)
                        print(f"成功删除旧头像")
                    except Exception as e:
                        # 删除失败，仅记录日志，不影响后续操作
                        print(f"无法删除旧头像文件: {old_avatar_path}, 错误: {str(e)}")
            
            # 确保文件名安全
            filename = secure_filename(avatar_file.filename)
            # 添加用户ID前缀和随机字符串，避免文件名冲突
            unique_filename = f"advertiser_{user_id}_{uuid.uuid4().hex[:8]}{os.path.splitext(filename)[1]}"
            
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
    query = f"UPDATE advertisers SET "
    query += ", ".join([f"{key} = %s" for key in update_data.keys()])
    query += " WHERE id = %s"
    
    params = list(update_data.values())
    params.append(user_id)
    
    print(f"执行SQL更新: {query}")
    print(f"SQL参数: {params}")
    
    success = db.execute(query, params)
    
    if success:
        print("数据库更新成功")
        flash('个人资料已成功更新', 'success')
    else:
        print("数据库更新失败")
        flash('更新个人资料时出错，请稍后重试', 'error')
    
    return redirect(url_for('advertiser.profile_basic'))

@advertiser_bp.route('/profile/finance')
@advertiser_required
def profile_finance():
    user_id = session.get('user_id')
    advertiser = user_dao.get_user_by_id(user_id, 'advertiser')
    
    # 获取余额交易记录
    query = """
        SELECT created_at, amount, description, 
               CASE WHEN amount > 0 THEN '收入' WHEN amount < 0 THEN '支出' ELSE '其他' END as type,
               'success' as status
        FROM balance_transactions_advertiser 
        WHERE advertiser_id = %s
        ORDER BY created_at DESC LIMIT 10
    """
    recharge_records = db.execute_query(query, (user_id,))
    
    # 计算总支出（已完成任务的预算总和）
    spent_query = """
        SELECT COALESCE(SUM(budget), 0) as total_spent, COUNT(*) as completed_count
        FROM ad_tasks
        WHERE advertiser_id = %s AND status = 'completed'
    """
    spent_result = db.execute_one(spent_query, (user_id,))
    
    total_spent = float(spent_result['total_spent']) if spent_result else 0
    completed_count = int(spent_result['completed_count']) if spent_result else 0
    
    # 计算平均预算
    average_budget = 0
    if completed_count > 0:
        average_budget = round(total_spent / completed_count, 2)
    
    return render_template('advertiser/profile/finance.html', 
                           active_tab='finance',
                           advertiser=advertiser,
                           recharge_records=recharge_records,
                           total_spent=total_spent,
                           completed_count=completed_count,
                           average_budget=average_budget)

@advertiser_bp.route('/recharge', methods=['POST'])
@advertiser_required
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
            return redirect(url_for('advertiser.profile_finance'))
        
        # 插入余额变动记录
        transaction_query = """
            INSERT INTO balance_transactions_advertiser 
            (advertiser_id, amount, description, created_at)
            VALUES (%s, %s, %s, NOW())
        """
        description = f"充值 - {payment_method}"
        db.execute(transaction_query, (user_id, amount, description))
        
        # 更新用户余额
        update_query = "UPDATE advertisers SET balance = balance + %s WHERE id = %s"
        db.execute(update_query, (amount, user_id))
        
        flash('充值成功！', 'success')
    except ValueError:
        flash('请输入有效的金额', 'error')
    except Exception as e:
        print(f"充值处理错误: {str(e)}")
        flash('处理充值时出错，请稍后重试', 'error')
    
    return redirect(url_for('advertiser.profile_finance'))

@advertiser_bp.route('/profile/change_password', methods=['POST'])
@advertiser_required
def change_password():
    user_id = session.get('user_id')
    
    # 获取表单数据
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # 验证表单数据
    if not all([old_password, new_password, confirm_password]):
        flash('请填写所有密码字段', 'error')
        return redirect(url_for('advertiser.profile_edit'))
    
    # 验证当前密码
    advertiser = user_dao.get_user_by_id(user_id, 'advertiser')
    if old_password != advertiser['password']:  # 实际应用中应使用安全的密码验证
        flash('当前密码不正确', 'error')
        return redirect(url_for('advertiser.profile_edit'))
    
    # 验证新密码与确认密码是否匹配
    if new_password != confirm_password:
        flash('新密码与确认密码不匹配', 'error')
        return redirect(url_for('advertiser.profile_edit'))
    
    # 更新密码
    query = "UPDATE advertisers SET password = %s WHERE id = %s"
    success = db.execute(query, (new_password, user_id))  # 实际应用中应对密码进行哈希处理
    
    if success:
        flash('密码已成功更新', 'success')
    else:
        flash('新密码与旧密码相同', 'error')
    
    return redirect(url_for('advertiser.profile_edit'))

# 添加发送邀请路由
@advertiser_bp.route('/send_invitation/<int:id>')
@advertiser_required
def send_invitation(id):
    # 此处仅简单重定向，实际实现需要完成邀请发送逻辑
    # TODO: 实现发送邀请功能
    return redirect(url_for('advertiser.collaboration_requests_sent'))

# 获取已发布广告任务的API路由
@advertiser_bp.route('/api/tasks/published')
@advertiser_required
def get_published_tasks():
    """获取当前广告主已发布的广告任务列表，用于邀请合作选择"""
    user_id = session.get('user_id')
    
    # 查询已发布状态的广告任务
    query = """
        SELECT id, title, description, budget, deadline, status
        FROM ad_tasks
        WHERE advertiser_id = %s AND status = 'published'
        ORDER BY created_at DESC
    """
    
    tasks = db.execute_query(query, (user_id,))
    
    return jsonify({
        'status': 'success',
        'tasks': tasks
    })

# 发送邀请的API路由
@advertiser_bp.route('/api/send_invitation', methods=['POST'])
@advertiser_required
def api_send_invitation():
    """处理发送邀请的API请求"""
    try:
        user_id = session.get('user_id')
        data = request.json
        
        print(f"收到邀请请求: {data}")
        
        # 获取请求数据并转换为整数
        collaborator_id = int(data.get('collaborator_id', 0))
        ad_task_id = int(data.get('ad_task_id', 0))
        invitation_content = data.get('invitation_content', '')
        
        # 验证数据
        if not collaborator_id or not ad_task_id or not invitation_content:
            print(f"邀请数据验证失败: collaborator_id={collaborator_id}, ad_task_id={ad_task_id}, content_length={len(invitation_content)}")
            return jsonify({
                'status': 'error',
                'message': '请求参数不完整'
            }), 400
        
        # 验证任务是否属于当前广告主
        task_query = "SELECT id FROM ad_tasks WHERE id = %s AND advertiser_id = %s"
        tasks = db.execute_query(task_query, (ad_task_id, user_id))
        task = tasks[0] if tasks else None
        
        if not task:
            print(f"任务验证失败: ad_task_id={ad_task_id}, user_id={user_id}")
            return jsonify({
                'status': 'error',
                'message': '无权操作该广告任务'
            }), 403
        
        # 验证是否已经发送过邀请
        exists_query = """
            SELECT id FROM collaboration_requests_advertiser 
            WHERE advertiser_id = %s AND collaborator_id = %s AND ad_task_id = %s
            AND status IN ('pending', 'accepted')
        """
        
        existing_requests = db.execute_query(exists_query, (user_id, collaborator_id, ad_task_id))
        existing_request = existing_requests[0] if existing_requests else None
        
        if existing_request:
            print(f"重复邀请: existing_request_id={existing_request['id']}")
            return jsonify({
                'status': 'error',
                'message': '已经向该合作者发送过邀请，请勿重复操作'
            }), 400
        
        # 插入新的邀请记录，确保包含所有必填字段
        insert_query = """
            INSERT INTO collaboration_requests_advertiser 
            (advertiser_id, collaborator_id, ad_task_id, invitation_content, status, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """
        
        success = db.execute(insert_query, (user_id, collaborator_id, ad_task_id, invitation_content, 'pending'))
        
        if success:
            print(f"邀请发送成功: collaborator_id={collaborator_id}, ad_task_id={ad_task_id}")
            return jsonify({
                'status': 'success',
                'message': '邀请已成功发送'
            })
        else:
            print(f"邀请发送失败: 数据库操作未成功")
            return jsonify({
                'status': 'error',
                'message': '发送邀请失败，请稍后再试'
            }), 500
    except Exception as e:
        # 捕获所有异常，记录日志，并返回友好的错误消息
        print(f"邀请发送异常: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'status': 'error',
            'message': '服务器处理请求时出错，请稍后再试'
        }), 500

# 取消合作请求的API
@advertiser_bp.route('/api/cancel_request/<int:request_id>', methods=['POST'])
@advertiser_required
def cancel_request(request_id):
    """取消发送的合作请求"""
    try:
        # 获取当前用户ID
        advertiser_id = session.get('user_id')
        
        # 验证请求是否存在且属于当前用户
        query = """
            SELECT id, status FROM collaboration_requests_advertiser 
            WHERE id = %s AND advertiser_id = %s AND status = 'pending'
        """
        requests = db.execute_query(query, (request_id, advertiser_id))
        
        if not requests:
            return jsonify({
                'status': 'error',
                'message': '请求不存在或无权操作'
            }), 404
        
        # 更新请求状态为canceled
        result = collaboration_requests_dao.update_advertiser_request_status(request_id, 'canceled')
        
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

@advertiser_bp.route('/api/accept_request/<int:request_id>', methods=['POST'])
@advertiser_required
def accept_request(request_id):
    """处理广告主接受合作者申请的API"""
    try:
        # 获取广告主ID
        advertiser_id = session.get('user_id')
        
        # 验证请求是否存在且属于当前广告主
        query = """
            SELECT id, ad_task_id FROM collaboration_requests_collaborator 
            WHERE id = %s AND advertiser_id = %s AND status = 'pending'
        """
        results = db.execute_query(query, (request_id, advertiser_id))
        
        if not results:
            return jsonify({
                'status': 'error',
                'message': '无效的请求或您无权操作此请求'
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
                'message': '该广告任务不存在，无法接受申请'
            }), 404
            
        if task_results[0]['status'] == 'in_progress':
            # 任务已被接受，删除该请求记录
            delete_query = """
                DELETE FROM collaboration_requests_collaborator 
                WHERE id = %s
            """
            db.execute(delete_query, (request_id,))
            
            return jsonify({
                'status': 'error',
                'message': '该广告任务已被接受，无法重复接受申请'
            }), 400
        
        # 更新请求状态为已接受
        response_message = "感谢您的申请，我们决定接受您的合作请求"
        result = collaboration_requests_dao.update_collaborator_request_status(
            request_id, 'accepted', response_message
        )
        
        if result:
            # 更新任务状态为进行中
            task_update_query = """
                UPDATE ad_tasks SET status = 'in_progress' WHERE id = %s
            """
            db.execute(task_update_query, (task_id,))
            
            # 通知操作成功
            notify_success('已成功接受合作申请', duration=3000)
            return jsonify({
                'status': 'success',
                'message': '已成功接受合作申请'
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

@advertiser_bp.route('/api/reject_request/<int:request_id>', methods=['POST'])
@advertiser_required
def reject_request(request_id):
    """处理广告主拒绝合作者申请的API"""
    try:
        # 获取广告主ID
        advertiser_id = session.get('user_id')
        
        # 验证请求是否存在且属于当前广告主
        query = """
            SELECT id, ad_task_id FROM collaboration_requests_collaborator 
            WHERE id = %s AND advertiser_id = %s AND status = 'pending'
        """
        results = db.execute_query(query, (request_id, advertiser_id))
        
        if not results:
            return jsonify({
                'status': 'error',
                'message': '无效的请求或您无权操作此请求'
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
                'message': '该广告任务不存在，无法拒绝申请'
            }), 404
            
        if task_results[0]['status'] == 'in_progress':
            # 任务已被接受，删除该请求记录
            delete_query = """
                DELETE FROM collaboration_requests_collaborator 
                WHERE id = %s
            """
            db.execute(delete_query, (request_id,))
            
            return jsonify({
                'status': 'error',
                'message': '该广告任务已被接受，无法拒绝申请'
            }), 400
        
        # 更新请求状态为已拒绝
        response_message = "非常抱歉，我们暂时无法接受您的合作申请"
        result = collaboration_requests_dao.update_collaborator_request_status(
            request_id, 'rejected', response_message
        )
        
        if result:
            # 通知操作成功
            notify_success('已拒绝合作申请', duration=3000)
            return jsonify({
                'status': 'success',
                'message': '已拒绝合作申请'
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

@advertiser_bp.route('/api/create_ad_task', methods=['POST'])
@advertiser_required
def api_create_ad_task():
    """处理创建广告任务的API请求"""
    try:
        # 获取广告主ID
        advertiser_id = session.get('user_id')
        data = request.json
        
        # 获取必填字段
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        budget = data.get('budget', 0)
        deadline = data.get('deadline', '')
        status = data.get('status', 'draft')
        
        # 获取可选字段
        target_audience = data.get('target_audience', '')
        platform_requirements = data.get('platform_requirements', '')
        content_format = data.get('content_format', '')
        content_style = data.get('content_style', '')
        requirements = data.get('requirements', '')
        
        # 验证必填字段
        if not title or not description or not budget or not deadline:
            notify_error('请填写所有必填字段')
            return jsonify({
                'status': 'error',
                'message': '请填写所有必填字段'
            }), 400
        
        # 验证预算格式
        try:
            budget = float(budget)
            if budget <= 0:
                notify_error('预算金额必须大于0')
                return jsonify({
                    'status': 'error',
                    'message': '预算金额必须大于0'
                }), 400
        except ValueError:
            notify_error('预算金额格式不正确')
            return jsonify({
                'status': 'error',
                'message': '预算金额格式不正确'
            }), 400
        
        # 验证截止日期格式
        try:
            # 检查日期格式是否正确
            deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
            
            # 检查截止日期是否在今天之后
            today = datetime.today().date()
            if deadline_date <= today:
                notify_error('截止日期必须在今天之后')
                return jsonify({
                    'status': 'error',
                    'message': '截止日期必须在今天之后'
                }), 400
        except ValueError:
            notify_error('截止日期格式不正确')
            return jsonify({
                'status': 'error',
                'message': '截止日期格式不正确'
            }), 400
        
        # 插入数据库
        insert_query = """
            INSERT INTO ad_tasks 
            (advertiser_id, title, description, budget, status, deadline, 
            target_audience, platform_requirements, content_format, content_style, requirements)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            advertiser_id, title, description, budget, status, deadline,
            target_audience, platform_requirements, content_format, content_style, requirements
        )
        
        result = db.execute(insert_query, params)
        
        if result:
            # 根据状态返回不同的消息，使用flash通知
            message = '广告任务已成功发布'
            notify_success(message, duration=3000)
            return jsonify({
                'status': 'success',
                'message': message
            })
        else:
            notify_error('创建广告任务失败，请稍后重试')
            return jsonify({
                'status': 'error',
                'message': '创建广告任务失败，请稍后重试'
            }), 500
            
    except Exception as e:
        print(f"创建广告任务出错: {str(e)}")
        notify_error('服务器内部错误，请稍后再试')
        return jsonify({
            'status': 'error',
            'message': '服务器内部错误'
        }), 500

@advertiser_bp.route('/api/complete_task/<int:task_id>', methods=['POST'])
@advertiser_required
def complete_task(task_id):
    """将任务标记为已完成"""
    try:
        # 获取广告主ID
        advertiser_id = session.get('user_id')
        
        print(f"尝试完成任务: task_id={task_id}, advertiser_id={advertiser_id}")
        
        # 验证任务是否存在且属于当前广告主，并获取任务预算和合作者信息
        task_query = """
            SELECT at.id, at.budget, COALESCE(crc.collaborator_id, cra.collaborator_id) as collaborator_id
            FROM ad_tasks at
            LEFT JOIN (
                SELECT ad_task_id, collaborator_id, created_at 
                FROM collaboration_requests_collaborator 
                WHERE status = 'accepted'
            ) crc ON at.id = crc.ad_task_id
            LEFT JOIN (
                SELECT ad_task_id, collaborator_id, created_at 
                FROM collaboration_requests_advertiser 
                WHERE status = 'accepted'
            ) cra ON at.id = cra.ad_task_id
            WHERE at.id = %s AND at.advertiser_id = %s AND at.status = 'in_progress'
            AND COALESCE(crc.collaborator_id, cra.collaborator_id) IS NOT NULL
        """
        tasks = db.execute_query(task_query, (task_id, advertiser_id))
        
        print(f"任务查询结果: {tasks}")
        
        if not tasks:
            print(f"无效任务: task_id={task_id}, advertiser_id={advertiser_id}")
            notify_error('无效的任务或您无权操作该任务')
            return jsonify({
                'status': 'error',
                'message': '无效的任务或您无权操作该任务'
            }), 403
        
        # 获取任务预算和合作者ID
        task_budget = float(tasks[0]['budget'])
        collaborator_id = tasks[0]['collaborator_id']
        
        print(f"任务预算: {task_budget}, 合作者ID: {collaborator_id}")
        
        # 检查广告主余额是否足够支付
        balance_query = """
            SELECT balance FROM advertisers WHERE id = %s
        """
        advertiser_balance = db.execute_query(balance_query, (advertiser_id,))
        
        if not advertiser_balance:
            print(f"找不到广告主余额: advertiser_id={advertiser_id}")
            notify_error('无法获取余额信息')
            return jsonify({
                'status': 'error',
                'message': '无法获取余额信息'
            }), 500
            
        current_balance = float(advertiser_balance[0]['balance'])
        print(f"广告主当前余额: {current_balance}")
        
        if current_balance < task_budget:
            print(f"余额不足: 当前余额={current_balance}, 需要={task_budget}")
            notify_error('余额不足，请先充值后再完成任务', duration=5000, dismissible=True)
            return jsonify({
                'status': 'error',
                'message': '余额不足，请先充值后再完成任务'
            }), 400
        
        # 获取数据库连接
        conn = db.connect()
        
        try:
            # 开始事务，关闭自动提交
            conn.autocommit(False)
            
            # 1. 扣除广告主账户余额
            deduct_advertiser_query = """
                UPDATE advertisers SET balance = balance - %s WHERE id = %s
            """
            with conn.cursor() as cursor:
                cursor.execute(deduct_advertiser_query, (task_budget, advertiser_id))
            
            # 2. 增加合作者账户余额
            add_collaborator_query = """
                UPDATE collaborators SET balance = balance + %s WHERE id = %s
            """
            with conn.cursor() as cursor:
                cursor.execute(add_collaborator_query, (task_budget, collaborator_id))
            
            # 3. 为广告主添加余额变动记录(支出)
            advertiser_transaction_query = """
                INSERT INTO balance_transactions_advertiser 
                (advertiser_id, amount, description, created_at)
                VALUES (%s, %s, %s, NOW())
            """
            description = f"支付任务费用 - 任务ID: {task_id}"
            with conn.cursor() as cursor:
                cursor.execute(advertiser_transaction_query, (advertiser_id, -task_budget, description))
            
            # 4. 为合作者添加余额变动记录(收入)
            collaborator_transaction_query = """
                INSERT INTO balance_transactions_collaborator 
                (collaborator_id, amount, description, created_at)
                VALUES (%s, %s, %s, NOW())
            """
            description = f"获得任务收入 - 任务ID: {task_id}"
            with conn.cursor() as cursor:
                cursor.execute(collaborator_transaction_query, (collaborator_id, task_budget, description))
            
            # 5. 更新任务状态为已完成
            update_query = """
                UPDATE ad_tasks 
                SET status = 'completed', updated_at = NOW() 
                WHERE id = %s
            """
            with conn.cursor() as cursor:
                cursor.execute(update_query, (task_id,))
            
            # 提交事务
            conn.commit()
            
            print(f"任务完成成功: task_id={task_id}")
            notify_success('任务已成功标记为已完成，广告费用已自动支付给合作者')
            return jsonify({
                'status': 'success',
                'message': '任务已成功标记为已完成，广告费用已自动支付给合作者'
            })
            
        except Exception as e:
            # 回滚事务
            conn.rollback()
            print(f"事务处理出错: {str(e)}")
            raise
            
    except Exception as e:
        print(f"标记任务完成时出错: {str(e)}")
        notify_error('服务器内部错误')
        return jsonify({
            'status': 'error',
            'message': '服务器内部错误'
        }), 500

@advertiser_bp.route('/api/archive_task/<int:task_id>', methods=['POST'])
@advertiser_required
def archive_task(task_id):
    """归档已完成的任务"""
    try:
        # 获取广告主ID
        advertiser_id = session.get('user_id')
        
        # 验证任务是否存在且属于当前广告主
        task_query = """
            SELECT id FROM ad_tasks 
            WHERE id = %s AND advertiser_id = %s AND status = 'completed'
        """
        tasks = db.execute_query(task_query, (task_id, advertiser_id))
        
        if not tasks:
            notify_error('无效的任务或您无权操作该任务')
            return jsonify({
                'status': 'error',
                'message': '无效的任务或您无权操作该任务'
            }), 403
        
        # 创建归档记录
        archive_query = """
            INSERT INTO archived_projects (project_id, user_id, user_type, created_at)
            VALUES (%s, %s, 'advertiser', NOW())
        """
        result = db.execute(archive_query, (task_id, advertiser_id))
        
        if result:
            notify_success('项目已成功归档')
            return jsonify({
                'status': 'success',
                'message': '项目已成功归档'
            })
        else:
            notify_error('操作失败，请稍后重试')
            return jsonify({
                'status': 'error',
                'message': '操作失败，请稍后重试'
            }), 500
            
    except Exception as e:
        print(f"归档任务时出错: {str(e)}")
        notify_error('服务器内部错误')
        return jsonify({
            'status': 'error',
            'message': '服务器内部错误'
        }), 500

@advertiser_bp.route('/api/cancel_task/<int:task_id>', methods=['POST'])
@advertiser_required
def cancel_task(task_id):
    """将任务取消"""
    try:
        # 获取广告主ID
        advertiser_id = session.get('user_id')
        
        # 获取任务状态
        task_query = """
            SELECT id, status FROM ad_tasks 
            WHERE id = %s AND advertiser_id = %s
        """
        tasks = db.execute_query(task_query, (task_id, advertiser_id))
        
        if not tasks:
            notify_error('无效的任务或您无权操作该任务')
            return jsonify({
                'status': 'error',
                'message': '无效的任务或您无权操作该任务'
            }), 403
        
        task_status = tasks[0]['status']
        
        # 验证任务当前状态是否可以取消
        if task_status not in ['published', 'in_progress']:
            notify_error('当前任务状态无法执行此操作')
            return jsonify({
                'status': 'error',
                'message': '当前任务状态无法执行此操作'
            }), 400
        
        # 更新任务状态为已取消
        update_query = """
            UPDATE ad_tasks 
            SET status = 'cancelled', updated_at = NOW() 
            WHERE id = %s
        """
        
        result = db.execute(update_query, (task_id,))
        
        if result:
            notify_success('任务已成功取消')
            return jsonify({
                'status': 'success',
                'message': '任务已成功取消'
            })
        else:
            notify_error('操作失败，请稍后重试')
            return jsonify({
                'status': 'error',
                'message': '操作失败，请稍后重试'
            }), 500
            
    except Exception as e:
        print(f"取消任务出错: {str(e)}")
        notify_error('服务器内部错误')
        return jsonify({
            'status': 'error',
            'message': '服务器内部错误'
        }), 500

@advertiser_bp.route('/api/restore_task/<int:task_id>', methods=['POST'])
@advertiser_required
def restore_task(task_id):
    """恢复已取消的任务为草稿状态"""
    try:
        # 获取广告主ID
        advertiser_id = session.get('user_id')
        
        # 验证任务是否存在且属于当前广告主
        task_query = """
            SELECT id FROM ad_tasks 
            WHERE id = %s AND advertiser_id = %s AND status = 'cancelled'
        """
        tasks = db.execute_query(task_query, (task_id, advertiser_id))
        
        if not tasks:
            notify_error('无效的任务或您无权操作该任务')
            return jsonify({
                'status': 'error',
                'message': '无效的任务或您无权操作该任务'
            }), 403
        
        # 更新任务状态为草稿
        update_query = """
            UPDATE ad_tasks 
            SET status = 'draft', updated_at = NOW() 
            WHERE id = %s
        """
        
        result = db.execute(update_query, (task_id,))
        
        if result:
            notify_success('任务已成功恢复为草稿状态')
            return jsonify({
                'status': 'success',
                'message': '任务已成功恢复为草稿状态'
            })
        else:
            notify_error('操作失败，请稍后重试')
            return jsonify({
                'status': 'error',
                'message': '操作失败，请稍后重试'
            }), 500
            
    except Exception as e:
        print(f"恢复任务出错: {str(e)}")
        notify_error('服务器内部错误')
        return jsonify({
            'status': 'error',
            'message': '服务器内部错误'
        }), 500

@advertiser_bp.route('/api/follow/add/<int:collaborator_id>', methods=['POST'])
@advertiser_required
def add_follow(collaborator_id):
    """广告主关注合作者"""
    try:
        advertiser_id = session.get('user_id')
        
        # 检查是否已经关注
        check_query = "SELECT id FROM follows_advertiser_to_collaborator WHERE advertiser_id = %s AND collaborator_id = %s"
        exist = db.execute_one(check_query, (advertiser_id, collaborator_id))
        
        if exist:
            return jsonify({'status': 'success', 'message': '已经关注过该合作者'})
        
        # 添加关注关系
        insert_query = "INSERT INTO follows_advertiser_to_collaborator (advertiser_id, collaborator_id) VALUES (%s, %s)"
        db.execute(insert_query, (advertiser_id, collaborator_id))
        
        return jsonify({'status': 'success', 'message': '关注成功'})
    except Exception as e:
        print(f"添加关注出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'操作失败: {str(e)}'})

@advertiser_bp.route('/api/follow/remove/<int:collaborator_id>', methods=['POST'])
@advertiser_required
def remove_follow(collaborator_id):
    """广告主取消关注合作者"""
    try:
        advertiser_id = session.get('user_id')
        
        # 删除关注关系
        delete_query = "DELETE FROM follows_advertiser_to_collaborator WHERE advertiser_id = %s AND collaborator_id = %s"
        db.execute(delete_query, (advertiser_id, collaborator_id))
        
        return jsonify({'status': 'success', 'message': '已取消关注'})
    except Exception as e:
        print(f"取消关注出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'操作失败: {str(e)}'})

@advertiser_bp.route('/api/send_message', methods=['POST'])
@advertiser_required
def send_message():
    """处理AJAX提交的消息发送请求"""
    try:
        # 获取广告主ID
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
        receiver_query = "SELECT id FROM collaborators WHERE id = %s"
        receiver = db.execute_one(receiver_query, (receiver_id,))
        
        if not receiver:
            return jsonify({
                'status': 'error',
                'message': '接收者不存在'
            }), 404
            
        # 验证是否互相关注
        a2c_query = "SELECT COUNT(*) as count FROM follows_advertiser_to_collaborator WHERE advertiser_id = %s AND collaborator_id = %s"
        a2c_result = db.execute_one(a2c_query, (sender_id, receiver_id))
        
        c2a_query = "SELECT COUNT(*) as count FROM follows_collaborator_to_advertiser WHERE collaborator_id = %s AND advertiser_id = %s"
        c2a_result = db.execute_one(c2a_query, (receiver_id, sender_id))
        
        is_mutual = (a2c_result and a2c_result['count'] > 0) and (c2a_result and c2a_result['count'] > 0)
        
        if not is_mutual:
            return jsonify({
                'status': 'error',
                'message': '只能向好友发送消息'
            }), 403
            
        # 插入新消息
        insert_query = """
            INSERT INTO messages_advertiser_to_collaborator (sender_id, receiver_id, content, is_read, created_at)
            VALUES (%s, %s, %s, 0, NOW())
        """
        db.execute(insert_query, (sender_id, receiver_id, content))
        
        # 获取插入的消息
        message_query = """
            SELECT id, sender_id, receiver_id, content, is_read, created_at
            FROM messages_advertiser_to_collaborator
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
        print(f"[ERROR] 广告主消息API - 处理请求时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500

@advertiser_bp.route('/api/get_messages/<int:receiver_id>')
@advertiser_required
def get_messages(receiver_id):
    """获取与指定用户的聊天记录"""
    try:
        print(f"[DEBUG] 广告主获取消息 - 开始处理请求，接收者ID: {receiver_id}")
        # 获取广告主ID
        sender_id = session.get('user_id')
        print(f"[DEBUG] 广告主获取消息 - 发送者ID: {sender_id}")
        
        # 直接使用两个简单查询检查是否互相关注
        # 检查广告主是否关注了合作者
        a2c_query = "SELECT COUNT(*) as count FROM follows_advertiser_to_collaborator WHERE advertiser_id = %s AND collaborator_id = %s"
        try:
            a2c_result = db.execute_one(a2c_query, (sender_id, receiver_id))
            print(f"[DEBUG] 广告主获取消息 - 广告主关注合作者检查结果: {a2c_result}")
        except Exception as e:
            print(f"[ERROR] 广告主获取消息 - 广告主关注合作者检查出错: {str(e)}")
            a2c_result = None
        
        # 检查合作者是否关注了广告主
        c2a_query = "SELECT COUNT(*) as count FROM follows_collaborator_to_advertiser WHERE collaborator_id = %s AND advertiser_id = %s"
        try:
            c2a_result = db.execute_one(c2a_query, (receiver_id, sender_id))
            print(f"[DEBUG] 广告主获取消息 - 合作者关注广告主检查结果: {c2a_result}")
        except Exception as e:
            print(f"[ERROR] 广告主获取消息 - 合作者关注广告主检查出错: {str(e)}")
            c2a_result = None
        
        # 如果两边都有关注记录，则认为是好友关系
        is_mutual = (a2c_result and a2c_result['count'] > 0) and (c2a_result and c2a_result['count'] > 0)
        print(f"[DEBUG] 广告主获取消息 - 最终互相关注检查结果: {is_mutual}")
        
        if not is_mutual:
            print(f"[DEBUG] 广告主获取消息 - 未通过好友关系检查，拒绝请求")
            return jsonify({
                'status': 'error',
                'message': '只能查看与好友的聊天记录'
            }), 403
        
        # 查询聊天记录
        query = """
            SELECT id, sender_id, receiver_id, content, is_read, created_at, 'sent' as type
            FROM messages_advertiser_to_collaborator
            WHERE sender_id = %s AND receiver_id = %s
            UNION
            SELECT id, sender_id, receiver_id, content, is_read, created_at, 'received' as type
            FROM messages_collaborator_to_advertiser
            WHERE sender_id = %s AND receiver_id = %s
            ORDER BY created_at ASC
        """
        try:
            messages = db.execute_query(query, (sender_id, receiver_id, receiver_id, sender_id))
            print(f"[DEBUG] 广告主获取消息 - 查询到 {len(messages)} 条消息")
        except Exception as e:
            print(f"[ERROR] 广告主获取消息 - 查询消息记录出错: {str(e)}")
            raise
        
        # 将消息标记为已读（仅接收到的消息）
        update_query = """
            UPDATE messages_collaborator_to_advertiser
            SET is_read = 1
            WHERE sender_id = %s AND receiver_id = %s AND is_read = 0
        """
        try:
            db.execute(update_query, (receiver_id, sender_id))
            print(f"[DEBUG] 广告主获取消息 - 已将消息标记为已读")
        except Exception as e:
            print(f"[ERROR] 广告主获取消息 - 标记消息为已读出错: {str(e)}")
        
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
                print(f"[ERROR] 广告主获取消息 - 格式化消息 {msg['id']} 出错: {str(e)}")
        
        print(f"[DEBUG] 广告主获取消息 - 成功返回 {len(formatted_messages)} 条格式化消息")
        return jsonify({
            'status': 'success',
            'data': formatted_messages
        })
    except Exception as e:
        print(f"[ERROR] 广告主获取消息 - 处理请求时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500

# 添加获取未读消息总数的方法
def get_advertiser_unread_count(advertiser_id):
    """获取广告主的总未读消息数"""
    query = """
        SELECT COUNT(*) as count
        FROM messages_collaborator_to_advertiser
        WHERE receiver_id = %s AND is_read = 0
    """
    result = db.execute_one(query, (advertiser_id,))
    return result['count'] if result else 0

@advertiser_bp.route('/withdraw', methods=['POST'])
@advertiser_required
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
            return redirect(url_for('advertiser.profile_finance'))
        
        # 获取当前用户余额
        advertiser = user_dao.get_user_by_id(user_id, 'advertiser')
        current_balance = float(advertiser.get('balance', 0))
        
        # 验证余额是否充足
        if amount > current_balance:
            flash('提现金额不能大于当前余额', 'error')
            return redirect(url_for('advertiser.profile_finance'))
        
        # 插入余额变动记录
        transaction_query = """
            INSERT INTO balance_transactions_advertiser 
            (advertiser_id, amount, description, created_at)
            VALUES (%s, %s, %s, NOW())
        """
        description = f"提现 - {withdraw_method} ({account})"
        db.execute(transaction_query, (user_id, -amount, description))
        
        # 更新用户余额 (减去提现金额)
        update_query = "UPDATE advertisers SET balance = balance - %s WHERE id = %s"
        db.execute(update_query, (amount, user_id))
        
        flash('提现申请已提交，资金将在1-3个工作日内到账', 'success')
    except ValueError:
        flash('请输入有效的金额', 'error')
    except Exception as e:
        print(f"提现处理错误: {str(e)}")
        flash('处理提现时出错，请稍后重试', 'error')
    
    return redirect(url_for('advertiser.profile_finance'))

# 通知相关API路由
@advertiser_bp.route('/api/notifications/mark_read', methods=['POST'])
@advertiser_required
def mark_notification_read():
    """标记通知为已读"""
    try:
        notification_id = request.json.get('notification_id')
        advertiser_id = session.get('user_id')
        
        if not notification_id:
            return jsonify({'status': 'error', 'message': '通知ID不能为空'}), 400
        
        # 更新数据库
        query = """
            UPDATE system_notifications_advertiser 
            SET is_read = 1 
            WHERE id = %s AND advertiser_id = %s
        """
        db.execute(query, (notification_id, advertiser_id))
        
        # 简化判断逻辑，不再检查rowcount
        return jsonify({'status': 'success', 'message': '通知已标记为已读'})
            
    except Exception as e:
        print(f"标记通知为已读时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': '服务器内部错误'}), 500