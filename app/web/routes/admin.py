from flask import Blueprint, render_template, redirect, url_for, jsonify, request, flash, session, abort
from app.web.auth_decorators import admin_required
from app.dao.advertiser_dao import AdvertiserDAO
from app.dao.collaborator_dao import CollaboratorDAO
from app.dao.ad_task_dao import AdTaskDAO
from app.dao.collaboration_requests_dao import CollaborationRequestsDAO
from app.dao.database import db

admin_bp = Blueprint('admin', __name__)

# 仪表盘概览相关路由
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # 重定向到实时监控页面
    return redirect(url_for('admin.dashboard_realtime'))

@admin_bp.route('/dashboard/realtime')
@admin_required
def dashboard_realtime():
    return render_template('admin/dashboard_overview/realtime.html', active_tab='realtime')

@admin_bp.route('/dashboard/send_notifications')
@admin_required
def dashboard_send_notifications():
    """发送系统通知页面"""
    # 不实现记录发送通知历史的功能，直接传递空列表
    recent_notifications = []
    
    return render_template('admin/dashboard_overview/send_notifications.html', 
                           active_tab='send_notifications',
                           recent_notifications=recent_notifications)

@admin_bp.route('/send_notification', methods=['POST'])
@admin_required
def send_notification():
    """处理发送通知的请求"""
    try:
        recipient_type = request.form.get('recipient_type')
        notification_title = request.form.get('notification_title')
        notification_content = request.form.get('notification_content')
        admin_id = session.get('user_id')
        
        if not recipient_type or not notification_title or not notification_content:
            flash('请填写所有必要字段', 'error')
            return redirect(url_for('admin.dashboard_send_notifications'))
        
        # 根据接收者类型处理
        if recipient_type == 'all_advertisers':
            # 给所有广告主发送通知
            query = """
                INSERT INTO system_notifications_advertiser 
                (advertiser_id, title, content, is_read, created_at)
                SELECT id, %s, %s, 0, NOW()
                FROM advertisers
            """
            db.execute(query, (notification_title, notification_content))
            success_message = '已成功向所有广告主发送通知'
            
        elif recipient_type == 'all_collaborators':
            # 给所有合作者发送通知
            query = """
                INSERT INTO system_notifications_collaborator 
                (collaborator_id, title, content, is_read, created_at)
                SELECT id, %s, %s, 0, NOW()
                FROM collaborators
            """
            db.execute(query, (notification_title, notification_content))
            success_message = '已成功向所有合作者发送通知'
            
        elif recipient_type == 'all':
            # 给所有用户发送通知
            query_advertisers = """
                INSERT INTO system_notifications_advertiser 
                (advertiser_id, title, content, is_read, created_at)
                SELECT id, %s, %s, 0, NOW()
                FROM advertisers
            """
            db.execute(query_advertisers, (notification_title, notification_content))
            
            query_collaborators = """
                INSERT INTO system_notifications_collaborator 
                (collaborator_id, title, content, is_read, created_at)
                SELECT id, %s, %s, 0, NOW()
                FROM collaborators
            """
            db.execute(query_collaborators, (notification_title, notification_content))
            success_message = '已成功向所有用户发送通知'
            
        elif recipient_type == 'specific_advertiser':
            # 给指定广告主发送通知
            user_id = request.form.get('user_id')
            if not user_id:
                flash('请输入广告主ID', 'error')
                return redirect(url_for('admin.dashboard_send_notifications'))
            
            # 检查用户是否存在
            check_query = "SELECT id FROM advertisers WHERE id = %s"
            user = db.execute_one(check_query, (user_id,))
            if not user:
                flash('指定的广告主不存在', 'error')
                return redirect(url_for('admin.dashboard_send_notifications'))
            
            query = """
                INSERT INTO system_notifications_advertiser 
                (advertiser_id, title, content, is_read, created_at)
                VALUES (%s, %s, %s, 0, NOW())
            """
            db.execute(query, (user_id, notification_title, notification_content))
            success_message = f'已成功向广告主 #{user_id} 发送通知'
            
        elif recipient_type == 'specific_collaborator':
            # 给指定合作者发送通知
            user_id = request.form.get('user_id')
            if not user_id:
                flash('请输入合作者ID', 'error')
                return redirect(url_for('admin.dashboard_send_notifications'))
            
            # 检查用户是否存在
            check_query = "SELECT id FROM collaborators WHERE id = %s"
            user = db.execute_one(check_query, (user_id,))
            if not user:
                flash('指定的合作者不存在', 'error')
                return redirect(url_for('admin.dashboard_send_notifications'))
            
            query = """
                INSERT INTO system_notifications_collaborator 
                (collaborator_id, title, content, is_read, created_at)
                VALUES (%s, %s, %s, 0, NOW())
            """
            db.execute(query, (user_id, notification_title, notification_content))
            success_message = f'已成功向合作者 #{user_id} 发送通知'
            
        else:
            flash('无效的接收者类型', 'error')
            return redirect(url_for('admin.dashboard_send_notifications'))
        
        # 不记录发送历史，直接显示成功消息
        flash(success_message, 'success')
        return redirect(url_for('admin.dashboard_send_notifications'))
    
    except Exception as e:
        flash(f'发送通知时出错: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard_send_notifications'))

@admin_bp.route('/dashboard_overview/realtime')
@admin_required
def dashboard_overview_realtime():
    """实时数据监控页面"""
    return render_template('admin/dashboard_overview/realtime.html')

# 用户管理相关路由
@admin_bp.route('/user_management')
@admin_required
def user_management():
    # 重定向到广告主列表页面
    return redirect(url_for('admin.user_management_advertisers'))

@admin_bp.route('/user_management/advertisers')
@admin_required
def user_management_advertisers():
    return render_template('admin/user_management/advertisers.html', active_tab='advertisers')

@admin_bp.route('/user_management/collaborators')
@admin_required
def user_management_collaborators():
    return render_template('admin/user_management/collaborators.html', active_tab='collaborators')

@admin_bp.route('/user_management/banned')
@admin_required
def user_management_banned():
    return render_template('admin/user_management/banned.html', active_tab='banned')

@admin_bp.route('/user_management/feedback')
@admin_required
def user_management_feedback():
    return render_template('admin/user_management/feedback.html', active_tab='feedback')

# 内容管理相关路由
@admin_bp.route('/content_management')
@admin_required
def content_management():
    # 重定向到广告任务列表页面
    return redirect(url_for('admin.content_management_ad_tasks'))

@admin_bp.route('/content_management/ad_tasks')
@admin_required
def content_management_ad_tasks():
    return render_template('admin/content_management/ad_tasks.html', active_tab='ad_tasks')

@admin_bp.route('/content_management/advertiser_requests')
@admin_required
def content_management_advertiser_requests():
    return render_template('admin/content_management/advertiser_requests.html', active_tab='advertiser_requests')

@admin_bp.route('/content_management/collaborator_requests')
@admin_required
def content_management_collaborator_requests():
    return render_template('admin/content_management/collaborator_requests.html', active_tab='collaborator_requests')

@admin_bp.route('/content_management/ongoing_projects')
@admin_required
def content_management_ongoing_projects():
    return render_template('admin/content_management/ongoing_projects.html', active_tab='ongoing_projects')

# 数据分析相关路由
@admin_bp.route('/data_analysis')
@admin_required
def data_analysis():
    # 重定向到用户分析页面
    return redirect(url_for('admin.data_analysis_users'))

@admin_bp.route('/data_analysis/users')
@admin_required
def data_analysis_users():
    return render_template('admin/data_analysis/users.html', active_tab='users')

@admin_bp.route('/data_analysis/transactions')
@admin_required
def data_analysis_transactions():
    return render_template('admin/data_analysis/transactions.html', active_tab='transactions')

@admin_bp.route('/data_analysis/content')
@admin_required
def data_analysis_content():
    """内容分析页面"""
    return render_template('admin/data_analysis/content.html')

@admin_bp.route('/data_analysis/conversion')
@admin_required
def data_analysis_conversion():
    return render_template('admin/data_analysis/conversion.html', active_tab='conversion')

@admin_bp.route('/data_analysis/recommendation')
@admin_required
def data_analysis_recommendation():
    return render_template('admin/data_analysis/recommendation.html', active_tab='recommendation')

# 财务管理相关路由
@admin_bp.route('/financial_management')
@admin_required
def financial_management():
    # 重定向到广告主交易记录页面
    return redirect(url_for('admin.financial_management_advertiser_transactions'))

@admin_bp.route('/financial_management/advertiser_transactions')
@admin_required
def financial_management_advertiser_transactions():
    return render_template('admin/financial_management/advertiser_transactions.html', active_tab='advertiser_transactions')

@admin_bp.route('/financial_management/collaborator_transactions')
@admin_required
def financial_management_collaborator_transactions():
    return render_template('admin/financial_management/collaborator_transactions.html', active_tab='collaborator_transactions')

# 系统设置相关路由
@admin_bp.route('/system_settings')
@admin_required
def system_settings():
    # 重定向到基础配置页面
    return redirect(url_for('admin.system_settings_basic'))

@admin_bp.route('/system_settings/basic')
@admin_required
def system_settings_basic():
    return render_template('admin/system_settings/basic.html', active_tab='basic')

@admin_bp.route('/system_settings/update_default_avatar/<user_type>', methods=['POST'])
@admin_required
def update_default_avatar(user_type):
    if user_type not in ['advertiser', 'collaborator']:
        flash('无效的用户类型', 'error')
        return redirect(url_for('admin.system_settings_basic'))
    
    if 'avatar_file' not in request.files:
        flash('未选择文件', 'error')
        return redirect(url_for('admin.system_settings_basic'))
    
    avatar_file = request.files['avatar_file']
    if not avatar_file or avatar_file.filename == '':
        flash('未选择文件', 'error')
        return redirect(url_for('admin.system_settings_basic'))
    
    # 检查文件类型
    import os
    if not avatar_file.filename.lower().endswith('.png'):
        flash('仅支持PNG格式的图片', 'error')
        return redirect(url_for('admin.system_settings_basic'))
    
    # 保存文件路径
    from app.config.settings import PROJECT_ROOT
    avatar_path = os.path.join(PROJECT_ROOT, 'app/web/static/img')
    filename = f'default_{user_type}.png'
    target_path = os.path.join(avatar_path, filename)
    
    try:
        # 保存文件
        avatar_file.save(target_path)
        flash(f'{user_type.capitalize()}默认头像更新成功', 'success')
    except Exception as e:
        flash(f'头像保存失败: {str(e)}', 'error')
    
    return redirect(url_for('admin.system_settings_basic'))

# API路由 - 广告主管理
@admin_bp.route('/api/advertisers')
@admin_required
def api_advertisers():
    """获取所有广告主列表"""
    try:
        advertisers = AdvertiserDAO.get_all_advertisers()
        return jsonify(advertisers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/advertisers/<int:advertiser_id>')
@admin_required
def api_advertiser_detail(advertiser_id):
    """获取广告主详情"""
    try:
        advertiser = AdvertiserDAO.get_advertiser_by_id(advertiser_id)
        if advertiser:
            return jsonify({"success": True, "advertiser": advertiser})
        else:
            return jsonify({"success": False, "message": "广告主不存在"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/advertisers', methods=['POST'])
@admin_required
def api_create_advertiser():
    """创建广告主"""
    try:
        data = request.json
        # 检查用户名是否已存在
        existing_user = AdvertiserDAO.get_advertiser_by_username(data.get('username'))
        if existing_user:
            return jsonify({"success": False, "message": "用户名已存在"}), 400
        
        # 创建广告主
        advertiser_id = AdvertiserDAO.create_advertiser(data)
        if advertiser_id:
            return jsonify({"success": True, "id": advertiser_id})
        else:
            return jsonify({"success": False, "message": "创建广告主失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/advertisers/<int:advertiser_id>', methods=['PUT'])
@admin_required
def api_update_advertiser(advertiser_id):
    """更新广告主信息"""
    try:
        data = request.json
        # 检查广告主是否存在
        existing_advertiser = AdvertiserDAO.get_advertiser_by_id(advertiser_id)
        if not existing_advertiser:
            return jsonify({"success": False, "message": "广告主不存在"}), 404
        
        # 如果修改了用户名，检查新用户名是否已存在
        if 'username' in data and data['username'] != existing_advertiser['username']:
            name_check = AdvertiserDAO.get_advertiser_by_username(data['username'])
            if name_check and name_check['id'] != advertiser_id:
                return jsonify({"success": False, "message": "用户名已存在"}), 400
        
        # 更新广告主信息
        success = AdvertiserDAO.update_advertiser(advertiser_id, data)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "更新广告主失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/advertisers/<int:advertiser_id>', methods=['DELETE'])
@admin_required
def api_delete_advertiser(advertiser_id):
    """删除广告主"""
    try:
        # 检查广告主是否存在
        existing_advertiser = AdvertiserDAO.get_advertiser_by_id(advertiser_id)
        if not existing_advertiser:
            return jsonify({"success": False, "message": "广告主不存在"}), 404
        
        # 删除广告主
        success = AdvertiserDAO.delete_advertiser(advertiser_id)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "删除广告主失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# API路由 - 合作者管理
@admin_bp.route('/api/collaborators')
@admin_required
def api_collaborators():
    """获取所有合作者列表"""
    try:
        collaborators = CollaboratorDAO.get_all_collaborators()
        return jsonify(collaborators)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/collaborators/<int:collaborator_id>')
@admin_required
def api_collaborator_detail(collaborator_id):
    """获取合作者详情"""
    try:
        collaborator = CollaboratorDAO.get_collaborator_by_id(collaborator_id)
        if collaborator:
            return jsonify({"success": True, "collaborator": collaborator})
        else:
            return jsonify({"success": False, "message": "合作者不存在"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/collaborators/<int:collaborator_id>', methods=['PUT'])
@admin_required
def api_update_collaborator(collaborator_id):
    """更新合作者信息"""
    try:
        data = request.json
        # 检查合作者是否存在
        existing_collaborator = CollaboratorDAO.get_collaborator_by_id(collaborator_id)
        if not existing_collaborator:
            return jsonify({"success": False, "message": "合作者不存在"}), 404
        
        # 如果修改了用户名，检查新用户名是否已存在
        if 'username' in data and data['username'] != existing_collaborator['username']:
            name_check = CollaboratorDAO.get_collaborator_by_username(data['username'])
            if name_check and name_check['id'] != collaborator_id:
                return jsonify({"success": False, "message": "用户名已存在"}), 400
        
        # 更新合作者信息
        success = CollaboratorDAO.update_collaborator(collaborator_id, data)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "更新合作者失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/collaborators/<int:collaborator_id>', methods=['DELETE'])
@admin_required
def api_delete_collaborator(collaborator_id):
    """删除合作者"""
    try:
        # 检查合作者是否存在
        existing_collaborator = CollaboratorDAO.get_collaborator_by_id(collaborator_id)
        if not existing_collaborator:
            return jsonify({"success": False, "message": "合作者不存在"}), 404
        
        # 删除合作者
        success = CollaboratorDAO.delete_collaborator(collaborator_id)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "删除合作者失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# API路由 - 广告任务管理
@admin_bp.route('/api/ad_tasks')
@admin_required
def api_ad_tasks():
    """获取所有广告任务列表"""
    try:
        # 获取所有状态的广告任务
        tasks = AdTaskDAO.get_all_tasks()
        
        # 为每个任务添加广告主信息
        for task in tasks:
            # 添加广告主信息
            advertiser = AdvertiserDAO.get_advertiser_by_id(task['advertiser_id'])
            if advertiser:
                task['advertiser_name'] = advertiser['username']
                task['company_name'] = advertiser['company_name']
            
            # 对于进行中或已完成的任务，添加合作者ID
            if task['status'] in ['in_progress', 'completed']:
                collaboration = AdTaskDAO.get_task_collaboration(task['id'])
                if collaboration and 'collaborator_id' in collaboration:
                    task['collaborator_id'] = collaboration['collaborator_id']
        
        return jsonify(tasks)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/ad_tasks/<int:task_id>', methods=['DELETE'])
@admin_required
def api_delete_ad_task(task_id):
    """删除广告任务"""
    try:
        # 检查任务是否存在
        task_query = "SELECT id FROM ad_tasks WHERE id = %s"
        task = db.execute_one(task_query, (task_id,))
        
        if not task:
            return jsonify({"success": False, "message": "广告任务不存在"}), 404
        
        # 删除任务
        delete_query = "DELETE FROM ad_tasks WHERE id = %s"
        result = db.execute(delete_query, (task_id,))
        
        if result:
            return jsonify({"success": True, "message": "删除成功"})
        else:
            return jsonify({"success": False, "message": "删除失败"}), 500
    except Exception as e:
        print(f"删除广告任务失败: {str(e)}")
        return jsonify({"success": False, "message": f"系统错误: {str(e)}"}), 500

@admin_bp.route('/api/ongoing_projects')
@admin_required
def api_ongoing_projects():
    """获取进行中的广告任务"""
    try:
        # 获取状态为"in_progress"的广告任务
        tasks = AdTaskDAO.get_tasks_by_status('in_progress')
        
        # 为每个任务添加广告主和合作者信息
        for task in tasks:
            # 添加广告主信息
            advertiser = AdvertiserDAO.get_advertiser_by_id(task['advertiser_id'])
            if advertiser:
                task['advertiser_name'] = advertiser['username']
                task['company_name'] = advertiser['company_name']
            
            # 获取该任务的合作关系信息
            collaboration = AdTaskDAO.get_task_collaboration(task['id'])
            if collaboration:
                # 添加合作者信息
                collaborator = CollaboratorDAO.get_collaborator_by_id(collaboration['collaborator_id'])
                if collaborator:
                    task['collaborator_name'] = collaborator['username']
                    task['start_time'] = collaboration['start_time']
        
        return jsonify(tasks)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API路由 - 合作请求管理
@admin_bp.route('/api/collaboration_requests')
@admin_required
def api_collaboration_requests():
    """获取合作请求，支持按类型过滤"""
    try:
        # 获取请求类型参数
        request_type = request.args.get('type', None)
        
        # 创建DAO实例
        dao = CollaborationRequestsDAO()
        
        # 根据type参数返回不同请求
        if request_type == 'advertiser':
            # 只返回广告主发起的请求
            advertiser_requests = dao.get_all_advertiser_requests()
            return jsonify(advertiser_requests)
        elif request_type == 'collaborator':
            # 只返回合作者发起的请求
            collaborator_requests = dao.get_all_collaborator_requests()
            return jsonify(collaborator_requests)
        else:
            # 返回所有类型的请求
            advertiser_requests = dao.get_all_advertiser_requests()
            collaborator_requests = dao.get_all_collaborator_requests()
            
            result = {
                "advertiser_requests": advertiser_requests,
                "collaborator_requests": collaborator_requests
            }
            return jsonify(result)
    except Exception as e:
        # 记录详细错误信息
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        print(f"获取合作请求API错误: {error_msg}")
        print(f"错误详情: {error_traceback}")
        return jsonify({"error": error_msg}), 500

@admin_bp.route('/api/advertiser_requests')
@admin_required
def api_advertiser_requests():
    """获取广告主发起的邀请"""
    try:
        dao = CollaborationRequestsDAO()
        advertiser_requests = dao.get_all_advertiser_requests()
        return jsonify(advertiser_requests)
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        print(f"获取广告主邀请API错误: {error_msg}")
        print(f"错误详情: {error_traceback}")
        return jsonify({"error": error_msg}), 500

@admin_bp.route('/api/collaborator_requests')
@admin_required
def api_collaborator_requests():
    """获取合作者发起的请求"""
    try:
        dao = CollaborationRequestsDAO()
        collaborator_requests = dao.get_all_collaborator_requests()
        return jsonify(collaborator_requests)
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        print(f"获取合作者请求API错误: {error_msg}")
        print(f"错误详情: {error_traceback}")
        return jsonify({"error": error_msg}), 500

@admin_bp.route('/api/advertiser_requests/<int:request_id>', methods=['DELETE'])
@admin_required
def api_delete_advertiser_request(request_id):
    """删除广告主邀请"""
    try:
        dao = CollaborationRequestsDAO()
        success = dao.delete_advertiser_request(request_id)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "删除广告主邀请失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/collaborator_requests/<int:request_id>', methods=['DELETE'])
@admin_required
def api_delete_collaborator_request(request_id):
    """删除合作者请求"""
    try:
        dao = CollaborationRequestsDAO()
        success = dao.delete_collaborator_request(request_id)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "删除合作者请求失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# 任务合作者查询API
@admin_bp.route('/api/task_collaborator')
@admin_required
def api_get_task_collaborator():
    """获取任务关联的合作者ID"""
    try:
        task_id = request.args.get('task_id', type=int)
        if not task_id:
            return jsonify({"success": False, "message": "缺少任务ID参数"}), 400
            
        # 获取任务关联的合作关系
        collaboration = AdTaskDAO.get_task_collaboration(task_id)
        
        if collaboration and 'collaborator_id' in collaboration:
            return jsonify({
                "success": True, 
                "collaborator_id": collaboration['collaborator_id'],
                "collaborator_info": {
                    "id": collaboration['collaborator_id'],
                    "start_time": collaboration['start_time'].strftime('%Y-%m-%d %H:%M:%S') if collaboration['start_time'] else None
                }
            })
        else:
            return jsonify({"success": False, "message": "未找到关联的合作者"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# 广告主交易记录API
@admin_bp.route('/api/advertiser_transactions')
@admin_required
def api_advertiser_transactions():
    try:
        query = """
            SELECT id, advertiser_id, amount, description, created_at,
                   CASE WHEN amount > 0 THEN '收入' WHEN amount < 0 THEN '支出' ELSE '其他' END as type,
                   'success' as status
            FROM balance_transactions_advertiser 
            ORDER BY created_at DESC
        """
        transactions = db.execute_query(query)
        
        # 获取广告主用户名
        if transactions:
            advertiser_ids = set(t['advertiser_id'] for t in transactions)
            id_list = ','.join(str(id) for id in advertiser_ids if id)
            
            if id_list:
                adv_query = f"SELECT id, username FROM advertisers WHERE id IN ({id_list})"
                advertisers = db.execute_query(adv_query)
                adv_map = {adv['id']: adv['username'] for adv in advertisers}
                
                # 添加用户名到交易记录
                for t in transactions:
                    t['username'] = adv_map.get(t['advertiser_id'], f"未知用户({t['advertiser_id']})")
        
        return jsonify(transactions)
    except Exception as e:
        print(f"获取广告主交易记录失败: {str(e)}")
        return jsonify([])

# 合作者交易记录API
@admin_bp.route('/api/collaborator_transactions')
@admin_required
def api_collaborator_transactions():
    try:
        query = """
            SELECT id, collaborator_id, amount, description, created_at,
                   CASE WHEN amount > 0 THEN '收入' WHEN amount < 0 THEN '支出' ELSE '其他' END as type,
                   'success' as status
            FROM balance_transactions_collaborator 
            ORDER BY created_at DESC
        """
        transactions = db.execute_query(query)
        
        # 获取合作者用户名
        if transactions:
            collaborator_ids = set(t['collaborator_id'] for t in transactions)
            id_list = ','.join(str(id) for id in collaborator_ids if id)
            
            if id_list:
                col_query = f"SELECT id, username FROM collaborators WHERE id IN ({id_list})"
                collaborators = db.execute_query(col_query)
                col_map = {col['id']: col['username'] for col in collaborators}
                
                # 添加用户名到交易记录
                for t in transactions:
                    t['username'] = col_map.get(t['collaborator_id'], f"未知用户({t['collaborator_id']})")
        
        return jsonify(transactions)
    except Exception as e:
        print(f"获取合作者交易记录失败: {str(e)}")
        return jsonify([])

# 删除广告主交易记录API
@admin_bp.route('/api/advertiser_transactions/<int:transaction_id>', methods=['DELETE'])
@admin_required
def api_delete_advertiser_transaction(transaction_id):
    try:
        # 检查记录是否存在
        check_query = "SELECT id FROM balance_transactions_advertiser WHERE id = %s"
        transaction = db.execute_one(check_query, (transaction_id,))
        
        if not transaction:
            return jsonify({"success": False, "message": "交易记录不存在"}), 404
        
        # 删除交易记录
        delete_query = "DELETE FROM balance_transactions_advertiser WHERE id = %s"
        result = db.execute(delete_query, (transaction_id,))
        
        if result:
            return jsonify({"success": True, "message": "删除成功"})
        else:
            return jsonify({"success": False, "message": "删除失败"}), 500
    except Exception as e:
        print(f"删除广告主交易记录失败: {str(e)}")
        return jsonify({"success": False, "message": f"系统错误: {str(e)}"}), 500

# 删除合作者交易记录API
@admin_bp.route('/api/collaborator_transactions/<int:transaction_id>', methods=['DELETE'])
@admin_required
def api_delete_collaborator_transaction(transaction_id):
    try:
        # 检查记录是否存在
        check_query = "SELECT id FROM balance_transactions_collaborator WHERE id = %s"
        transaction = db.execute_one(check_query, (transaction_id,))
        
        if not transaction:
            return jsonify({"success": False, "message": "交易记录不存在"}), 404
        
        # 删除交易记录
        delete_query = "DELETE FROM balance_transactions_collaborator WHERE id = %s"
        result = db.execute(delete_query, (transaction_id,))
        
        if result:
            return jsonify({"success": True, "message": "删除成功"})
        else:
            return jsonify({"success": False, "message": "删除失败"}), 500
    except Exception as e:
        print(f"删除合作者交易记录失败: {str(e)}")
        return jsonify({"success": False, "message": f"系统错误: {str(e)}"}), 500

# API路由 - 用户数据分析
@admin_bp.route('/api/data_analysis/users/stats')
@admin_required
def api_user_stats():
    """获取用户统计概况"""
    try:
        # 获取所有广告主和合作者数量
        advertisers_count = AdvertiserDAO.get_advertisers_count()
        collaborators_count = CollaboratorDAO.get_collaborators_count()
        total_users = advertisers_count + collaborators_count
        
        # 获取近30天活跃用户数量
        active_advertisers = AdvertiserDAO.get_active_advertisers_count(days=30)
        active_collaborators = CollaboratorDAO.get_active_collaborators_count(days=30)
        active_users = active_advertisers + active_collaborators
        
        # 获取近30天新增用户数量
        new_advertisers = AdvertiserDAO.get_new_advertisers_count(days=30)
        new_collaborators = CollaboratorDAO.get_new_collaborators_count(days=30)
        new_users = new_advertisers + new_collaborators
        
        # 计算简单的转化率 (活跃用户/总用户)
        conversion_rate = round((active_users / total_users) * 100) if total_users > 0 else 0
        
        return jsonify({
            "success": True,
            "data": {
                "total_users": total_users,
                "total_advertisers": advertisers_count,
                "total_collaborators": collaborators_count,
                "active_users": active_users,
                "new_users_month": new_users,
                "conversion_rate": conversion_rate
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/data_analysis/users/growth')
@admin_required
def api_user_growth():
    """获取用户增长趋势数据"""
    try:
        # 获取过去12个月的月度用户增长数据
        months = 12
        advertiser_growth = AdvertiserDAO.get_monthly_growth(months)
        collaborator_growth = CollaboratorDAO.get_monthly_growth(months)
        
        month_labels = []
        from datetime import datetime, timedelta
        current_date = datetime.now()
        for i in range(months-1, -1, -1):
            date = current_date - timedelta(days=i*30)
            month_labels.append(date.strftime("%Y-%m"))
        
        return jsonify({
            "success": True,
            "data": {
                "labels": month_labels,
                "advertiser_data": advertiser_growth,
                "collaborator_data": collaborator_growth
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/data_analysis/users/platforms')
@admin_required
def api_platform_distribution():
    """获取合作者平台分布数据"""
    try:
        platform_data = CollaboratorDAO.get_platform_distribution()
        
        platforms = []
        counts = []
        for item in platform_data:
            platforms.append(item['platform'])
            counts.append(item['count'])
        
        return jsonify({
            "success": True,
            "data": {
                "platforms": platforms,
                "counts": counts
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/data_analysis/users/followers')
@admin_required
def api_follower_distribution():
    """获取合作者粉丝数分布数据"""
    try:
        # 粉丝数范围分布
        ranges = [
            {"name": "<1万", "min": 0, "max": 10000},
            {"name": "1-5万", "min": 10000, "max": 50000},
            {"name": "5-10万", "min": 50000, "max": 100000},
            {"name": "10-50万", "min": 100000, "max": 500000},
            {"name": "50-100万", "min": 500000, "max": 1000000},
            {"name": ">100万", "min": 1000000, "max": float('inf')}
        ]
        
        follower_data = CollaboratorDAO.get_follower_distribution(ranges)
        
        range_names = [r['name'] for r in ranges]
        counts = [r['count'] for r in follower_data]
        
        return jsonify({
            "success": True,
            "data": {
                "ranges": range_names,
                "counts": counts
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/data_analysis/users/industries')
@admin_required
def api_industry_distribution():
    """获取广告主行业分布数据"""
    try:
        industry_data = AdvertiserDAO.get_industry_distribution()
        
        industries = []
        counts = []
        for item in industry_data:
            industries.append(item['industry'] or '未指定')
            counts.append(item['count'])
        
        return jsonify({
            "success": True,
            "data": {
                "industries": industries,
                "counts": counts
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/data_analysis/users/content_domains')
@admin_required
def api_content_domain_distribution():
    """获取合作者内容领域分布数据"""
    try:
        domain_data = CollaboratorDAO.get_content_domain_distribution()
        
        domains = []
        counts = []
        for item in domain_data:
            domains.append(item['content_domain'] or '未指定')
            counts.append(item['count'])
        
        return jsonify({
            "success": True,
            "data": {
                "domains": domains,
                "counts": counts
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/data_analysis/users/budgets')
@admin_required
def api_budget_distribution():
    """获取广告主预算范围分布数据"""
    try:
        # 预算范围分布
        ranges = [
            {"name": "<1000元", "min": 0, "max": 1000},
            {"name": "1000-5000元", "min": 1000, "max": 5000},
            {"name": "5000-10000元", "min": 5000, "max": 10000},
            {"name": "10000-50000元", "min": 10000, "max": 50000},
            {"name": ">50000元", "min": 50000, "max": float('inf')}
        ]
        
        budget_data = AdvertiserDAO.get_budget_distribution(ranges)
        
        range_names = [r['name'] for r in ranges]
        counts = [r['count'] for r in budget_data]
        
        return jsonify({
            "success": True,
            "data": {
                "ranges": range_names,
                "counts": counts
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/data_analysis/users/activity')
@admin_required
def api_user_activity():
    """获取用户活跃度数据"""
    try:
        # 获取过去7天的日活跃度数据
        days = 7
        advertiser_activity = AdvertiserDAO.get_daily_activity(days)
        collaborator_activity = CollaboratorDAO.get_daily_activity(days)
        
        day_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        
        return jsonify({
            "success": True,
            "data": {
                "labels": day_labels,
                "advertiser_data": advertiser_activity,
                "collaborator_data": collaborator_activity
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# 新增的交易数据分析API端点
@admin_bp.route('/api/transactions/stats')
@admin_required
def api_transactions_stats():
    """获取交易统计概况"""
    try:
        # 获取广告主交易统计
        adv_count_query = "SELECT COUNT(*) as count FROM balance_transactions_advertiser"
        adv_count = db.execute_one(adv_count_query)
        
        adv_sum_query = "SELECT SUM(ABS(amount)) as total FROM balance_transactions_advertiser"
        adv_sum = db.execute_one(adv_sum_query)
        
        # 获取合作者交易统计
        col_count_query = "SELECT COUNT(*) as count FROM balance_transactions_collaborator"
        col_count = db.execute_one(col_count_query)
        
        col_sum_query = "SELECT SUM(ABS(amount)) as total FROM balance_transactions_collaborator"
        col_sum = db.execute_one(col_sum_query)
        
        return jsonify({
            "success": True,
            "data": {
                "advertiser_count": adv_count['count'] if adv_count else 0,
                "advertiser_amount": float(adv_sum['total']) if adv_sum and adv_sum['total'] else 0,
                "collaborator_count": col_count['count'] if col_count else 0,
                "collaborator_amount": float(col_sum['total']) if col_sum and col_sum['total'] else 0
            }
        })
    except Exception as e:
        print(f"获取交易统计数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/transactions/trend')
@admin_required
def api_transactions_trend():
    """获取交易趋势数据"""
    try:
        months = request.args.get('months', 6, type=int)
        
        # 获取最近N个月的数据
        result_data = {
            "labels": [],
            "advertiser_data": [],
            "collaborator_data": []
        }
        
        # 生成月份标签
        from datetime import datetime, timedelta
        current_date = datetime.now()
        
        for i in range(months-1, -1, -1):
            date = current_date - timedelta(days=i*30)
            month_label = date.strftime("%Y-%m")
            result_data["labels"].append(month_label)
            
            # 计算月份范围
            start_date = date.replace(day=1).strftime("%Y-%m-%d")
            if date.month == 12:
                end_date = date.replace(year=date.year+1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = date.replace(month=date.month+1, day=1) - timedelta(days=1)
            end_date = end_date.strftime("%Y-%m-%d")
            
            # 查询广告主月度交易总额
            adv_query = """
                SELECT SUM(ABS(amount)) as total FROM balance_transactions_advertiser
                WHERE DATE(created_at) BETWEEN %s AND %s
            """
            adv_result = db.execute_one(adv_query, (start_date, end_date))
            result_data["advertiser_data"].append(float(adv_result['total']) if adv_result and adv_result['total'] else 0)
            
            # 查询合作者月度交易总额
            col_query = """
                SELECT SUM(ABS(amount)) as total FROM balance_transactions_collaborator
                WHERE DATE(created_at) BETWEEN %s AND %s
            """
            col_result = db.execute_one(col_query, (start_date, end_date))
            result_data["collaborator_data"].append(float(col_result['total']) if col_result and col_result['total'] else 0)
        
        return jsonify({
            "success": True,
            "data": result_data
        })
    except Exception as e:
        print(f"获取交易趋势数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/transactions/income_expense')
@admin_required
def api_transactions_income_expense():
    """获取收支比例数据"""
    try:
        user_type = request.args.get('type', 'advertiser')
        
        if user_type == 'advertiser':
            table = 'balance_transactions_advertiser'
            id_field = 'advertiser_id'
        else:
            table = 'balance_transactions_collaborator'
            id_field = 'collaborator_id'
        
        # 查询收入总额
        income_query = f"""
            SELECT SUM(amount) as total FROM {table}
            WHERE amount > 0
        """
        income_result = db.execute_one(income_query)
        
        # 查询支出总额
        expense_query = f"""
            SELECT SUM(ABS(amount)) as total FROM {table}
            WHERE amount < 0
        """
        expense_result = db.execute_one(expense_query)
        
        income = float(income_result['total']) if income_result and income_result['total'] else 0
        expense = float(expense_result['total']) if expense_result and expense_result['total'] else 0
        
        return jsonify({
            "success": True,
            "data": {
                "income": income,
                "expense": expense
            }
        })
    except Exception as e:
        print(f"获取收支比例数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/transactions/user_distribution')
@admin_required
def api_transactions_user_distribution():
    """获取交易用户分布数据"""
    try:
        # 查询所有广告主ID
        all_adv_query = """
            SELECT id FROM advertisers
        """
        all_advertisers = db.execute_query(all_adv_query)
        adv_ids = {adv['id']: 0 for adv in all_advertisers}  # 初始化所有广告主交易次数为0
        
        # 查询所有合作者ID
        all_col_query = """
            SELECT id FROM collaborators
        """
        all_collaborators = db.execute_query(all_col_query)
        col_ids = {col['id']: 0 for col in all_collaborators}  # 初始化所有合作者交易次数为0
        
        # 查询广告主交易频率分布
        adv_query = """
            SELECT advertiser_id, COUNT(*) as tx_count 
            FROM balance_transactions_advertiser 
            GROUP BY advertiser_id
        """
        adv_results = db.execute_query(adv_query)
        
        # 更新有交易记录的广告主的交易次数
        for result in adv_results:
            if result['advertiser_id'] in adv_ids:
                adv_ids[result['advertiser_id']] = result['tx_count']
        
        # 查询合作者交易频率分布
        col_query = """
            SELECT collaborator_id, COUNT(*) as tx_count 
            FROM balance_transactions_collaborator 
            GROUP BY collaborator_id
        """
        col_results = db.execute_query(col_query)
        
        # 更新有交易记录的合作者的交易次数
        for result in col_results:
            if result['collaborator_id'] in col_ids:
                col_ids[result['collaborator_id']] = result['tx_count']
        
        # 交易频率分组
        frequency_groups = {
            '0-10笔': 0,
            '11-100笔': 0,
            '101-200笔': 0,
            '200笔以上': 0
        }
        
        # 统计广告主交易频率
        for count in adv_ids.values():
            if 0 <= count <= 10:
                frequency_groups['0-10笔'] += 1
            elif 11 <= count <= 100:
                frequency_groups['11-100笔'] += 1
            elif 101 <= count <= 200:
                frequency_groups['101-200笔'] += 1
            else:
                frequency_groups['200笔以上'] += 1
        
        # 统计合作者交易频率
        for count in col_ids.values():
            if 0 <= count <= 10:
                frequency_groups['0-10笔'] += 1
            elif 11 <= count <= 100:
                frequency_groups['11-100笔'] += 1
            elif 101 <= count <= 200:
                frequency_groups['101-200笔'] += 1
            else:
                frequency_groups['200笔以上'] += 1
        
        return jsonify({
            "success": True,
            "data": {
                "labels": list(frequency_groups.keys()),
                "counts": list(frequency_groups.values())
            }
        })
    except Exception as e:
        print(f"获取交易用户分布数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/transactions/amount_distribution')
@admin_required
def api_transactions_amount_distribution():
    """获取交易金额分布数据"""
    try:
        # 定义金额范围
        ranges = [
            {"name": "0-100元", "min": 0, "max": 100},
            {"name": "100-500元", "min": 100, "max": 500},
            {"name": "500-1000元", "min": 500, "max": 1000},
            {"name": "1000-5000元", "min": 1000, "max": 5000},
            {"name": "5000元以上", "min": 5000, "max": float('inf')}
        ]
        
        amount_distribution = {}
        
        # 查询广告主交易金额分布
        for range_item in ranges:
            min_value = range_item['min']
            max_value = range_item['max']
            
            if max_value == float('inf'):
                adv_query = """
                    SELECT COUNT(*) as count FROM balance_transactions_advertiser
                    WHERE ABS(amount) > %s
                """
                adv_result = db.execute_one(adv_query, (min_value,))
            else:
                adv_query = """
                    SELECT COUNT(*) as count FROM balance_transactions_advertiser
                    WHERE ABS(amount) > %s AND ABS(amount) <= %s
                """
                adv_result = db.execute_one(adv_query, (min_value, max_value))
            
            # 查询合作者交易金额分布
            if max_value == float('inf'):
                col_query = """
                    SELECT COUNT(*) as count FROM balance_transactions_collaborator
                    WHERE ABS(amount) > %s
                """
                col_result = db.execute_one(col_query, (min_value,))
            else:
                col_query = """
                    SELECT COUNT(*) as count FROM balance_transactions_collaborator
                    WHERE ABS(amount) > %s AND ABS(amount) <= %s
                """
                col_result = db.execute_one(col_query, (min_value, max_value))
            
            adv_count = adv_result['count'] if adv_result else 0
            col_count = col_result['count'] if col_result else 0
            amount_distribution[range_item['name']] = adv_count + col_count
        
        return jsonify({
            "success": True,
            "data": {
                "labels": list(amount_distribution.keys()),
                "counts": list(amount_distribution.values())
            }
        })
    except Exception as e:
        print(f"获取交易金额分布数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

# API路由 - 内容数据分析
@admin_bp.route('/api/content/stats')
@admin_required
def api_content_stats():
    """获取内容统计概况"""
    try:
        # 获取广告任务总数
        total_tasks_query = "SELECT COUNT(*) as count FROM ad_tasks"
        total_tasks_result = db.execute_one(total_tasks_query)
        total_tasks = total_tasks_result['count'] if total_tasks_result else 0
        
        # 获取任务总浏览量
        total_views_query = "SELECT SUM(views_count) as total FROM ad_tasks"
        total_views_result = db.execute_one(total_views_query)
        total_views = total_views_result['total'] if total_views_result and total_views_result['total'] else 0
        
        # 获取总申请数
        total_applications_query = "SELECT SUM(applications_count) as total FROM ad_tasks"
        total_applications_result = db.execute_one(total_applications_query)
        total_applications = total_applications_result['total'] if total_applications_result and total_applications_result['total'] else 0
        
        # 获取平均预算
        avg_budget_query = "SELECT AVG(budget) as average FROM ad_tasks"
        avg_budget_result = db.execute_one(avg_budget_query)
        average_budget = float(avg_budget_result['average']) if avg_budget_result and avg_budget_result['average'] else 0
        
        return jsonify({
            "success": True,
            "data": {
                "total_tasks": total_tasks,
                "total_views": total_views,
                "total_applications": total_applications,
                "average_budget": average_budget
            }
        })
    except Exception as e:
        print(f"获取内容统计数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/content/trend')
@admin_required
def api_content_trend():
    """获取内容发布和完成趋势数据"""
    try:
        # 获取请求的月份数
        months = int(request.args.get('months', 6))
        
        # 准备日期标签和数据数组
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months*30)
        
        # 生成月份标签
        labels = []
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime("%Y-%m"))
            # 移动到下个月
            month = current_date.month + 1
            year = current_date.year
            if month > 12:
                month = 1
                year += 1
            current_date = current_date.replace(year=year, month=month, day=1)
        
        # 获取每个月发布的任务数量
        published_data = []
        for i in range(len(labels)):
            if i < len(labels) - 1:
                # 当前月份的开始和结束
                month_start = labels[i] + "-01"
                month_end = labels[i+1] + "-01"
                
                # 查询当月发布的任务数
                published_query = """
                SELECT COUNT(*) as count 
                FROM ad_tasks 
                WHERE created_at >= %s AND created_at < %s
                """
                published_result = db.execute_one(published_query, (month_start, month_end))
                published_data.append(published_result['count'] if published_result else 0)
            else:
                # 最后一个月（当前月）
                month_start = labels[i] + "-01"
                
                # 查询当月发布的任务数
                published_query = """
                SELECT COUNT(*) as count 
                FROM ad_tasks 
                WHERE created_at >= %s
                """
                published_result = db.execute_one(published_query, (month_start,))
                published_data.append(published_result['count'] if published_result else 0)
        
        # 获取每个月完成的任务数量
        completed_data = []
        for i in range(len(labels)):
            if i < len(labels) - 1:
                # 当前月份的开始和结束
                month_start = labels[i] + "-01"
                month_end = labels[i+1] + "-01"
                
                # 查询当月完成的任务数
                completed_query = """
                SELECT COUNT(*) as count 
                FROM ad_tasks 
                WHERE status = 'completed' AND updated_at >= %s AND updated_at < %s
                """
                completed_result = db.execute_one(completed_query, (month_start, month_end))
                completed_data.append(completed_result['count'] if completed_result else 0)
            else:
                # 最后一个月（当前月）
                month_start = labels[i] + "-01"
                
                # 查询当月完成的任务数
                completed_query = """
                SELECT COUNT(*) as count 
                FROM ad_tasks 
                WHERE status = 'completed' AND updated_at >= %s
                """
                completed_result = db.execute_one(completed_query, (month_start,))
                completed_data.append(completed_result['count'] if completed_result else 0)
        
        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "published_data": published_data,
                "completed_data": completed_data
            }
        })
    except Exception as e:
        print(f"获取内容趋势数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/content/status_distribution')
@admin_required
def api_status_distribution():
    """获取任务状态分布数据"""
    try:
        # 查询不同状态的任务数量
        status_query = """
        SELECT status, COUNT(*) as count 
        FROM ad_tasks 
        GROUP BY status
        """
        status_results = db.execute_query(status_query)
        
        # 构建状态标签和数量数组
        labels = []
        counts = []
        
        for result in status_results:
            labels.append(result['status'])
            counts.append(result['count'])
        
        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "counts": counts
            }
        })
    except Exception as e:
        print(f"获取状态分布数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/content/format_distribution')
@admin_required
def api_format_distribution():
    """获取内容格式分布数据"""
    try:
        # 查询不同内容格式的任务数量
        format_query = """
        SELECT content_format, COUNT(*) as count 
        FROM ad_tasks 
        WHERE content_format IS NOT NULL AND content_format != ''
        GROUP BY content_format
        """
        format_results = db.execute_query(format_query)
        
        # 构建格式标签和数量数组
        labels = []
        counts = []
        
        for result in format_results:
            labels.append(result['content_format'])
            counts.append(result['count'])
        
        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "counts": counts
            }
        })
    except Exception as e:
        print(f"获取格式分布数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/content/style_distribution')
@admin_required
def api_style_distribution():
    """获取内容风格分布数据"""
    try:
        # 查询不同内容风格的任务数量
        style_query = """
        SELECT content_style, COUNT(*) as count 
        FROM ad_tasks 
        WHERE content_style IS NOT NULL AND content_style != ''
        GROUP BY content_style
        """
        style_results = db.execute_query(style_query)
        
        # 构建风格标签和数量数组
        labels = []
        counts = []
        
        for result in style_results:
            labels.append(result['content_style'])
            counts.append(result['count'])
        
        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "counts": counts
            }
        })
    except Exception as e:
        print(f"获取风格分布数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/content/budget_distribution')
@admin_required
def api_content_budget_distribution():
    """获取预算区间分布数据"""
    try:
        # 定义预算区间
        ranges = [
            {"name": "<1000元", "min": 0, "max": 1000},
            {"name": "1000-5000元", "min": 1000, "max": 5000},
            {"name": "5000-10000元", "min": 5000, "max": 10000},
            {"name": "10000-50000元", "min": 10000, "max": 50000},
            {"name": "50000-100000元", "min": 50000, "max": 100000},
            {"name": ">100000元", "min": 100000, "max": float('inf')}
        ]
        
        # 查询每个预算区间的任务数量
        range_names = []
        counts = []
        
        for range_info in ranges:
            if range_info["max"] == float('inf'):
                # 处理最大区间
                count_query = """
                SELECT COUNT(*) as count 
                FROM ad_tasks 
                WHERE budget > %s
                """
                count_result = db.execute_one(count_query, (range_info["min"],))
            else:
                # 处理普通区间
                count_query = """
                SELECT COUNT(*) as count 
                FROM ad_tasks 
                WHERE budget >= %s AND budget < %s
                """
                count_result = db.execute_one(count_query, (range_info["min"], range_info["max"]))
            
            range_names.append(range_info["name"])
            counts.append(count_result['count'] if count_result else 0)
        
        return jsonify({
            "success": True,
            "data": {
                "ranges": range_names,
                "counts": counts
            }
        })
    except Exception as e:
        print(f"获取预算分布数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/content/platform_distribution')
@admin_required
def api_content_platform_distribution():
    """获取平台要求分布数据"""
    try:
        # 查询不同平台要求的任务数量
        platform_query = """
        SELECT platform_requirements, COUNT(*) as count 
        FROM ad_tasks 
        WHERE platform_requirements IS NOT NULL AND platform_requirements != ''
        GROUP BY platform_requirements
        """
        platform_results = db.execute_query(platform_query)
        
        # 构建平台标签和数量数组
        platforms = []
        counts = []
        
        for result in platform_results:
            platforms.append(result['platform_requirements'])
            counts.append(result['count'])
        
        return jsonify({
            "success": True,
            "data": {
                "platforms": platforms,
                "counts": counts
            }
        })
    except Exception as e:
        print(f"获取平台分布数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

# API路由 - 转化率数据分析
@admin_bp.route('/api/conversion/stats')
@admin_required
def api_conversion_stats():
    """获取转化率统计概况"""
    try:
        # 获取广告任务总数
        total_tasks_query = "SELECT COUNT(*) as count FROM ad_tasks"
        total_tasks_result = db.execute_one(total_tasks_query)
        total_tasks = total_tasks_result['count'] if total_tasks_result else 0
        
        # 获取已完成任务数
        completed_tasks_query = "SELECT COUNT(*) as count FROM ad_tasks WHERE status = 'completed'"
        completed_tasks_result = db.execute_one(completed_tasks_query)
        completed_tasks = completed_tasks_result['count'] if completed_tasks_result else 0
        
        # 获取总浏览量
        total_views_query = "SELECT SUM(views_count) as total FROM ad_tasks"
        total_views_result = db.execute_one(total_views_query)
        total_views = total_views_result['total'] if total_views_result and total_views_result['total'] else 0
        
        # 获取总申请数
        total_applications_query = "SELECT SUM(applications_count) as total FROM ad_tasks"
        total_applications_result = db.execute_one(total_applications_query)
        total_applications = total_applications_result['total'] if total_applications_result and total_applications_result['total'] else 0
        
        # 计算浏览到申请的转化率
        view_to_application_rate = round((total_applications / total_views) * 100, 2) if total_views > 0 else 0
        
        # 计算申请到合作的转化率
        application_to_collaboration_rate = round((completed_tasks / total_applications) * 100, 2) if total_applications > 0 else 0
        
        # 计算整体转化率
        overall_conversion_rate = round((completed_tasks / total_tasks) * 100, 2) if total_tasks > 0 else 0
        
        return jsonify({
            "success": True,
            "data": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "total_views": total_views,
                "total_applications": total_applications,
                "view_to_application_rate": view_to_application_rate,
                "application_to_collaboration_rate": application_to_collaboration_rate,
                "overall_conversion_rate": overall_conversion_rate
            }
        })
    except Exception as e:
        print(f"获取转化率统计数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/conversion/trend')
@admin_required
def api_conversion_trend():
    """获取转化率趋势数据"""
    try:
        # 获取请求的月份数
        months = int(request.args.get('months', 6))
        
        # 准备日期标签和数据数组
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months*30)
        
        # 生成月份标签
        labels = []
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime("%Y-%m"))
            # 移动到下个月
            month = current_date.month + 1
            year = current_date.year
            if month > 12:
                month = 1
                year += 1
            current_date = current_date.replace(year=year, month=month, day=1)
        
        # 获取每个月的浏览次数、申请次数和完成任务数
        view_data = []
        application_data = []
        conversion_rate_data = []
        
        for i in range(len(labels)):
            if i < len(labels) - 1:
                # 当前月份的开始和结束
                month_start = labels[i] + "-01"
                month_end = labels[i+1] + "-01"
                
                # 查询当月浏览次数
                views_query = """
                SELECT SUM(views_count) as total
                FROM ad_tasks 
                WHERE created_at >= %s AND created_at < %s
                """
                views_result = db.execute_one(views_query, (month_start, month_end))
                month_views = views_result['total'] if views_result and views_result['total'] else 0
                view_data.append(month_views)
                
                # 查询当月申请次数
                applications_query = """
                SELECT SUM(applications_count) as total
                FROM ad_tasks 
                WHERE created_at >= %s AND created_at < %s
                """
                applications_result = db.execute_one(applications_query, (month_start, month_end))
                month_applications = applications_result['total'] if applications_result and applications_result['total'] else 0
                application_data.append(month_applications)
                
                # 计算当月转化率
                month_conversion_rate = round((month_applications / month_views) * 100, 2) if month_views > 0 else 0
                conversion_rate_data.append(month_conversion_rate)
            else:
                # 最后一个月（当前月）
                month_start = labels[i] + "-01"
                
                # 查询当月浏览次数
                views_query = """
                SELECT SUM(views_count) as total
                FROM ad_tasks 
                WHERE created_at >= %s
                """
                views_result = db.execute_one(views_query, (month_start,))
                month_views = views_result['total'] if views_result and views_result['total'] else 0
                view_data.append(month_views)
                
                # 查询当月申请次数
                applications_query = """
                SELECT SUM(applications_count) as total
                FROM ad_tasks 
                WHERE created_at >= %s
                """
                applications_result = db.execute_one(applications_query, (month_start,))
                month_applications = applications_result['total'] if applications_result and applications_result['total'] else 0
                application_data.append(month_applications)
                
                # 计算当月转化率
                month_conversion_rate = round((month_applications / month_views) * 100, 2) if month_views > 0 else 0
                conversion_rate_data.append(month_conversion_rate)
        
        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "views_data": view_data,
                "applications_data": application_data,
                "conversion_rate_data": conversion_rate_data
            }
        })
    except Exception as e:
        print(f"获取转化率趋势数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/conversion/platform')
@admin_required
def api_conversion_platform():
    """获取不同平台的转化率数据"""
    try:
        # 查询不同平台的任务数、浏览数和申请数
        platform_query = """
        SELECT platform_requirements, 
               COUNT(*) as task_count,
               SUM(views_count) as views_count,
               SUM(applications_count) as applications_count
        FROM ad_tasks 
        WHERE platform_requirements IS NOT NULL AND platform_requirements != ''
        GROUP BY platform_requirements
        """
        platform_results = db.execute_query(platform_query)
        
        platforms = []
        conversion_rates = []
        
        for result in platform_results:
            platform = result['platform_requirements']
            views = result['views_count'] if result['views_count'] else 0
            applications = result['applications_count'] if result['applications_count'] else 0
            
            # 计算该平台的转化率
            conversion_rate = round((applications / views) * 100, 2) if views > 0 else 0
            
            platforms.append(platform)
            conversion_rates.append(conversion_rate)
        
        return jsonify({
            "success": True,
            "data": {
                "platforms": platforms,
                "conversion_rates": conversion_rates
            }
        })
    except Exception as e:
        print(f"获取平台转化率数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/conversion/budget')
@admin_required
def api_conversion_budget():
    """获取不同预算区间的转化率数据"""
    try:
        # 定义预算区间
        ranges = [
            {"name": "<1000元", "min": 0, "max": 1000},
            {"name": "1000-5000元", "min": 1000, "max": 5000},
            {"name": "5000-10000元", "min": 5000, "max": 10000},
            {"name": "10000-50000元", "min": 10000, "max": 50000},
            {"name": ">50000元", "min": 50000, "max": float('inf')}
        ]
        
        range_names = []
        views_counts = []
        applications_counts = []
        conversion_rates = []
        
        for range_info in ranges:
            if range_info["max"] == float('inf'):
                # 处理最大区间
                budget_query = """
                SELECT SUM(views_count) as views, SUM(applications_count) as applications
                FROM ad_tasks 
                WHERE budget > %s
                """
                budget_result = db.execute_one(budget_query, (range_info["min"],))
            else:
                # 处理普通区间
                budget_query = """
                SELECT SUM(views_count) as views, SUM(applications_count) as applications
                FROM ad_tasks 
                WHERE budget >= %s AND budget < %s
                """
                budget_result = db.execute_one(budget_query, (range_info["min"], range_info["max"]))
            
            views = budget_result['views'] if budget_result and budget_result['views'] else 0
            applications = budget_result['applications'] if budget_result and budget_result['applications'] else 0
            
            # 计算该预算区间的转化率
            conversion_rate = round((applications / views) * 100, 2) if views > 0 else 0
            
            range_names.append(range_info["name"])
            views_counts.append(views)
            applications_counts.append(applications)
            conversion_rates.append(conversion_rate)
        
        return jsonify({
            "success": True,
            "data": {
                "ranges": range_names,
                "views": views_counts,
                "applications": applications_counts,
                "conversion_rates": conversion_rates
            }
        })
    except Exception as e:
        print(f"获取预算区间转化率数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/conversion/format')
@admin_required
def api_conversion_format():
    """获取不同内容格式的转化率数据"""
    try:
        # 查询不同内容格式的任务数、浏览数和申请数
        format_query = """
        SELECT content_format, 
               COUNT(*) as task_count,
               SUM(views_count) as views_count,
               SUM(applications_count) as applications_count
        FROM ad_tasks 
        WHERE content_format IS NOT NULL AND content_format != ''
        GROUP BY content_format
        """
        format_results = db.execute_query(format_query)
        
        formats = []
        conversion_rates = []
        
        for result in format_results:
            content_format = result['content_format']
            views = result['views_count'] if result['views_count'] else 0
            applications = result['applications_count'] if result['applications_count'] else 0
            
            # 计算该内容格式的转化率
            conversion_rate = round((applications / views) * 100, 2) if views > 0 else 0
            
            formats.append(content_format)
            conversion_rates.append(conversion_rate)
        
        return jsonify({
            "success": True,
            "data": {
                "formats": formats,
                "conversion_rates": conversion_rates
            }
        })
    except Exception as e:
        print(f"获取内容格式转化率数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/conversion/style')
@admin_required
def api_conversion_style():
    """获取不同内容风格的转化率数据"""
    try:
        # 查询不同内容风格的任务数、浏览数和申请数
        style_query = """
        SELECT content_style, 
               COUNT(*) as task_count,
               SUM(views_count) as views_count,
               SUM(applications_count) as applications_count
        FROM ad_tasks 
        WHERE content_style IS NOT NULL AND content_style != ''
        GROUP BY content_style
        """
        style_results = db.execute_query(style_query)
        
        styles = []
        conversion_rates = []
        
        for result in style_results:
            content_style = result['content_style']
            views = result['views_count'] if result['views_count'] else 0
            applications = result['applications_count'] if result['applications_count'] else 0
            
            # 计算该内容风格的转化率
            conversion_rate = round((applications / views) * 100, 2) if views > 0 else 0
            
            styles.append(content_style)
            conversion_rates.append(conversion_rate)
        
        return jsonify({
            "success": True,
            "data": {
                "styles": styles,
                "conversion_rates": conversion_rates
            }
        })
    except Exception as e:
        print(f"获取内容风格转化率数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

# API路由 - 实时数据监控
@admin_bp.route('/api/dashboard/realtime/stats')
@admin_required
def api_dashboard_realtime_stats():
    """获取实时统计数据"""
    try:
        # 获取进行中任务数
        ongoing_tasks_query = """
        SELECT COUNT(*) as count 
        FROM ad_tasks 
        WHERE status = 'in_progress'
        """
        ongoing_tasks_result = db.execute_one(ongoing_tasks_query)
        ongoing_tasks = ongoing_tasks_result['count'] if ongoing_tasks_result else 0
        
        # 获取当日活跃广告主数 (通过最后登录时间)
        today_active_advertisers_query = """
        SELECT COUNT(*) as count 
        FROM advertisers 
        WHERE DATE(last_login) = CURDATE()
        """
        today_active_advertisers_result = db.execute_one(today_active_advertisers_query)
        today_active_advertisers = today_active_advertisers_result['count'] if today_active_advertisers_result else 0
        
        # 获取当日活跃合作者数 (通过最后登录时间)
        today_active_collaborators_query = """
        SELECT COUNT(*) as count 
        FROM collaborators 
        WHERE DATE(last_login) = CURDATE()
        """
        today_active_collaborators_result = db.execute_one(today_active_collaborators_query)
        today_active_collaborators = today_active_collaborators_result['count'] if today_active_collaborators_result else 0
        
        # 计算当日总活跃用户数
        online_users = today_active_advertisers + today_active_collaborators
        
        # 获取今日交易额 (通过广告主和合作者的交易记录表)
        today_adv_transactions_query = """
        SELECT SUM(ABS(amount)) as total 
        FROM balance_transactions_advertiser 
        WHERE DATE(created_at) = CURDATE()
        """
        today_adv_transactions_result = db.execute_one(today_adv_transactions_query)
        today_adv_amount = float(today_adv_transactions_result['total'] or 0) if today_adv_transactions_result else 0
        
        today_col_transactions_query = """
        SELECT SUM(ABS(amount)) as total 
        FROM balance_transactions_collaborator 
        WHERE DATE(created_at) = CURDATE()
        """
        today_col_transactions_result = db.execute_one(today_col_transactions_query)
        today_col_amount = float(today_col_transactions_result['total'] or 0) if today_col_transactions_result else 0
        
        # 计算今日总交易额
        today_transactions_amount = today_adv_amount + today_col_amount
        
        # 获取今日活动数 (广告任务创建、更新、合作请求等)
        # 广告任务今日创建数
        today_tasks_query = """
        SELECT COUNT(*) as count 
        FROM ad_tasks 
        WHERE DATE(created_at) = CURDATE()
        """
        today_tasks_result = db.execute_one(today_tasks_query)
        today_tasks = today_tasks_result['count'] if today_tasks_result else 0
        
        # 合作请求今日创建数
        today_adv_requests_query = """
        SELECT COUNT(*) as count 
        FROM collaboration_requests_advertiser 
        WHERE DATE(created_at) = CURDATE()
        """
        today_adv_requests_result = db.execute_one(today_adv_requests_query)
        today_adv_requests = today_adv_requests_result['count'] if today_adv_requests_result else 0
        
        today_col_requests_query = """
        SELECT COUNT(*) as count 
        FROM collaboration_requests_collaborator 
        WHERE DATE(created_at) = CURDATE()
        """
        today_col_requests_result = db.execute_one(today_col_requests_query)
        today_col_requests = today_col_requests_result['count'] if today_col_requests_result else 0
        
        # 计算今日总活动数
        today_activities = today_tasks + today_adv_requests + today_col_requests
        
        return jsonify({
            "success": True,
            "data": {
                "online_users": online_users,
                "today_activities": today_activities,
                "today_transactions_amount": today_transactions_amount,
                "ongoing_tasks": ongoing_tasks
            }
        })
    except Exception as e:
        print(f"获取实时统计数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/dashboard/realtime/activities')
@admin_required
def api_dashboard_realtime_activities():
    """获取最近活动数据"""
    try:
        activities = []
        
        # 获取最近10条广告任务创建/更新活动
        tasks_query = """
        SELECT 'task_action' as activity_type, 
               t.id, t.title, t.status, t.created_at, t.updated_at,
               a.id as user_id, a.username, 'advertiser' as role
        FROM ad_tasks t
        JOIN advertisers a ON t.advertiser_id = a.id
        ORDER BY GREATEST(t.created_at, t.updated_at) DESC
        LIMIT 5
        """
        tasks_results = db.execute_query(tasks_query)
        
        for result in tasks_results:
            # 判断是创建还是更新活动
            is_new = result['created_at'] == result['updated_at']
            activity_type = 'task_create' if is_new else 'task_update'
            
            # 格式化时间为友好显示
            created_at = result['created_at']
            updated_at = result['updated_at']
            time_display = format_time_ago(created_at if is_new else updated_at)
            
            activities.append({
                "id": f"task_{result['id']}",
                "user": f"{result['role']} {result['username']}",
                "type": activity_type,
                "description": f"{'创建' if is_new else '更新'}了广告任务",
                "details": f"任务: {result['title']}, 状态: {result['status']}",
                "time": time_display,
                "timestamp": (created_at if is_new else updated_at).timestamp() if created_at else 0
            })
        
        # 获取最近5条广告主发起的合作请求
        adv_requests_query = """
        SELECT 'collaboration_request' as activity_type, 
               r.id, r.ad_task_id, r.status, r.created_at,
               a.id as user_id, a.username, 'advertiser' as role,
               c.username as collaborator_name
        FROM collaboration_requests_advertiser r
        JOIN advertisers a ON r.advertiser_id = a.id
        JOIN collaborators c ON r.collaborator_id = c.id
        ORDER BY r.created_at DESC
        LIMIT 5
        """
        adv_requests_results = db.execute_query(adv_requests_query)
        
        for result in adv_requests_results:
            # 格式化时间
            created_at = result['created_at']
            time_display = format_time_ago(created_at)
            
            activities.append({
                "id": f"adv_req_{result['id']}",
                "user": f"{result['role']} {result['username']}",
                "type": "collaboration",
                "description": "发起了合作邀请",
                "details": f"给合作者: {result['collaborator_name']}, 任务ID: {result['ad_task_id']}",
                "time": time_display,
                "timestamp": created_at.timestamp() if created_at else 0
            })
        
        # 获取最近5条合作者发起的合作请求
        col_requests_query = """
        SELECT 'collaboration_response' as activity_type, 
               r.id, r.ad_task_id, r.status, r.created_at,
               c.id as user_id, c.username, 'collaborator' as role,
               a.username as advertiser_name
        FROM collaboration_requests_collaborator r
        JOIN collaborators c ON r.collaborator_id = c.id
        JOIN advertisers a ON r.advertiser_id = a.id
        ORDER BY r.created_at DESC
        LIMIT 5
        """
        col_requests_results = db.execute_query(col_requests_query)
        
        for result in col_requests_results:
            # 格式化时间
            created_at = result['created_at']
            time_display = format_time_ago(created_at)
            
            activities.append({
                "id": f"col_req_{result['id']}",
                "user": f"{result['role']} {result['username']}",
                "type": "collaboration",
                "description": "申请了广告合作",
                "details": f"给广告主: {result['advertiser_name']}, 任务ID: {result['ad_task_id']}",
                "time": time_display,
                "timestamp": created_at.timestamp() if created_at else 0
            })
        
        # 获取最近5条交易记录
        adv_transactions_query = """
        SELECT 'transaction' as activity_type, 
               t.id, t.amount, t.description, t.created_at,
               a.id as user_id, a.username, 'advertiser' as role
        FROM balance_transactions_advertiser t
        JOIN advertisers a ON t.advertiser_id = a.id
        ORDER BY t.created_at DESC
        LIMIT 5
        """
        adv_transactions_results = db.execute_query(adv_transactions_query)
        
        for result in adv_transactions_results:
            # 格式化时间
            created_at = result['created_at']
            time_display = format_time_ago(created_at)
            
            activities.append({
                "id": f"adv_tx_{result['id']}",
                "user": f"{result['role']} {result['username']}",
                "type": "transaction",
                "description": "进行了账户交易",
                "details": f"金额: {result['amount']}, {result['description']}",
                "time": time_display,
                "timestamp": created_at.timestamp() if created_at else 0
            })
            
        # 合并所有结果并按时间戳排序，取最近的10条
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        activities = activities[:10]
        
        # 移除时间戳字段（仅用于排序）
        for activity in activities:
            activity.pop('timestamp', None)
        
        return jsonify({
            "success": True,
            "data": activities
        })
    except Exception as e:
        print(f"获取最近活动数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/dashboard/realtime/transactions')
@admin_required
def api_dashboard_realtime_transactions():
    """获取最近交易记录"""
    try:
        transactions = []
        
        # 获取广告主最近5条交易记录
        adv_transactions_query = """
        SELECT t.id, t.advertiser_id as user_id, 
               CASE WHEN t.amount > 0 THEN '充值' ELSE '提现' END as type,
               t.amount, t.description, 'success' as status, t.created_at,
               a.username
        FROM balance_transactions_advertiser t
        JOIN advertisers a ON t.advertiser_id = a.id
        ORDER BY t.created_at DESC
        LIMIT 5
        """
        adv_transactions_results = db.execute_query(adv_transactions_query)
        
        for result in adv_transactions_results:
            # 格式化时间
            created_at = result['created_at']
            time_display = format_datetime(created_at)
            
            transactions.append({
                "id": f"ADV-{result['id']}",
                "user": result['username'],
                "type": result['type'],
                "amount": float(result['amount']),
                "description": result['description'],
                "status": result['status'],
                "time": time_display,
                "timestamp": created_at.timestamp() if created_at else 0
            })
        
        # 获取合作者最近5条交易记录
        col_transactions_query = """
        SELECT t.id, t.collaborator_id as user_id,
               CASE WHEN t.amount > 0 THEN '收入' ELSE '提现' END as type,
               t.amount, t.description, 'success' as status, t.created_at,
               c.username
        FROM balance_transactions_collaborator t
        JOIN collaborators c ON t.collaborator_id = c.id
        ORDER BY t.created_at DESC
        LIMIT 5
        """
        col_transactions_results = db.execute_query(col_transactions_query)
        
        for result in col_transactions_results:
            # 格式化时间
            created_at = result['created_at']
            time_display = format_datetime(created_at)
            
            transactions.append({
                "id": f"COL-{result['id']}",
                "user": result['username'],
                "type": result['type'],
                "amount": float(result['amount']),
                "description": result['description'],
                "status": result['status'],
                "time": time_display,
                "timestamp": created_at.timestamp() if created_at else 0
            })
        
        # 合并所有结果并按时间戳排序，取最近的10条
        transactions.sort(key=lambda x: x['timestamp'], reverse=True)
        transactions = transactions[:10]
        
        # 移除时间戳字段（仅用于排序）
        for tx in transactions:
            tx.pop('timestamp', None)
        
        return jsonify({
            "success": True,
            "data": transactions
        })
    except Exception as e:
        print(f"获取最近交易数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/dashboard/realtime/user_distribution')
@admin_required
def api_dashboard_realtime_user_distribution():
    """获取用户在线分布数据"""
    try:
        # 获取广告主和合作者的数量
        advertisers_query = "SELECT COUNT(*) as count FROM advertisers"
        advertisers_result = db.execute_one(advertisers_query)
        advertisers_count = advertisers_result['count'] if advertisers_result else 0
        
        collaborators_query = "SELECT COUNT(*) as count FROM collaborators"
        collaborators_result = db.execute_one(collaborators_query)
        collaborators_count = collaborators_result['count'] if collaborators_result else 0
        
        # 获取当日活跃广告主数 (通过最后登录时间)
        active_advertisers_query = """
        SELECT COUNT(*) as count 
        FROM advertisers 
        WHERE DATE(last_login) = CURDATE()
        """
        active_advertisers_result = db.execute_one(active_advertisers_query)
        active_advertisers_count = active_advertisers_result['count'] if active_advertisers_result else 0
        
        # 获取当日活跃合作者数 (通过最后登录时间)
        active_collaborators_query = """
        SELECT COUNT(*) as count 
        FROM collaborators 
        WHERE DATE(last_login) = CURDATE()
        """
        active_collaborators_result = db.execute_one(active_collaborators_query)
        active_collaborators_count = active_collaborators_result['count'] if active_collaborators_result else 0
        
        # 管理员数量
        admin_query = "SELECT COUNT(*) as count FROM admins"
        admin_result = db.execute_one(admin_query)
        admin_count = admin_result['count'] if admin_result else 0
        
        # 估算游客数量 (非活跃用户)
        visitors_count = (advertisers_count - active_advertisers_count) + (collaborators_count - active_collaborators_count)
        if visitors_count < 0:
            visitors_count = 0
        
        # 构建响应数据
        roles = ['广告主', '合作者', '管理员', '游客']
        counts = [active_advertisers_count, active_collaborators_count, admin_count, visitors_count]
        
        return jsonify({
            "success": True,
            "data": {
                "roles": roles,
                "counts": counts
            }
        })
    except Exception as e:
        print(f"获取用户在线分布数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/dashboard/realtime/activity_distribution')
@admin_required
def api_dashboard_realtime_activity_distribution():
    """获取今日活动分布数据"""
    try:
        # 修复：添加了以下代码以获取活跃用户数量，解决了未定义变量问题
        # 获取当日活跃广告主数 (通过最后登录时间)
        active_advertisers_query = """
        SELECT COUNT(*) as count 
        FROM advertisers 
        WHERE DATE(last_login) = CURDATE()
        """
        active_advertisers_result = db.execute_one(active_advertisers_query)
        active_advertisers_count = active_advertisers_result['count'] if active_advertisers_result else 0
        
        # 获取当日活跃合作者数 (通过最后登录时间)
        active_collaborators_query = """
        SELECT COUNT(*) as count 
        FROM collaborators 
        WHERE DATE(last_login) = CURDATE()
        """
        active_collaborators_result = db.execute_one(active_collaborators_query)
        active_collaborators_count = active_collaborators_result['count'] if active_collaborators_result else 0
        
        # 广告任务创建
        task_create_query = """
        SELECT COUNT(*) as count 
        FROM ad_tasks 
        WHERE DATE(created_at) = CURDATE()
        """
        task_create_result = db.execute_one(task_create_query)
        task_create_count = task_create_result['count'] if task_create_result else 0
        
        # 广告任务更新
        task_update_query = """
        SELECT COUNT(*) as count 
        FROM ad_tasks 
        WHERE DATE(updated_at) = CURDATE() AND DATE(created_at) != DATE(updated_at)
        """
        task_update_result = db.execute_one(task_update_query)
        task_update_count = task_update_result['count'] if task_update_result else 0
        
        # 合作邀请
        collab_invite_query = """
        SELECT COUNT(*) as count 
        FROM collaboration_requests_advertiser 
        WHERE DATE(created_at) = CURDATE()
        """
        collab_invite_result = db.execute_one(collab_invite_query)
        collab_invite_count = collab_invite_result['count'] if collab_invite_result else 0
        
        # 合作申请
        collab_request_query = """
        SELECT COUNT(*) as count 
        FROM collaboration_requests_collaborator 
        WHERE DATE(created_at) = CURDATE()
        """
        collab_request_result = db.execute_one(collab_request_query)
        collab_request_count = collab_request_result['count'] if collab_request_result else 0
        
        # 消息发送 (广告主到合作者)
        adv_message_query = """
        SELECT COUNT(*) as count 
        FROM messages_advertiser_to_collaborator 
        WHERE DATE(created_at) = CURDATE()
        """
        adv_message_result = db.execute_one(adv_message_query)
        adv_message_count = adv_message_result['count'] if adv_message_result else 0
        
        # 消息发送 (合作者到广告主)
        col_message_query = """
        SELECT COUNT(*) as count 
        FROM messages_collaborator_to_advertiser 
        WHERE DATE(created_at) = CURDATE()
        """
        col_message_result = db.execute_one(col_message_query)
        col_message_count = col_message_result['count'] if col_message_result else 0
        
        # 交易记录
        transaction_query = """
        SELECT COUNT(*) as count 
        FROM (
            SELECT created_at FROM balance_transactions_advertiser WHERE DATE(created_at) = CURDATE()
            UNION ALL
            SELECT created_at FROM balance_transactions_collaborator WHERE DATE(created_at) = CURDATE()
        ) as transactions
        """
        transaction_result = db.execute_one(transaction_query)
        transaction_count = transaction_result['count'] if transaction_result else 0
        
        # 构建数据
        activity_types = ['登录', '任务创建', '任务更新', '合作邀请', '合作申请', '消息', '交易']
        # 模拟登录数据（系统没有实际记录）
        login_count = active_advertisers_count + active_collaborators_count
        counts = [login_count, task_create_count, task_update_count, collab_invite_count, collab_request_count, adv_message_count + col_message_count, transaction_count]
        
        return jsonify({
            "success": True,
            "data": {
                "activity_types": activity_types,
                "counts": counts
            }
        })
    except Exception as e:
        print(f"获取今日活动分布数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/dashboard/realtime/task_status')
@admin_required
def api_dashboard_realtime_task_status():
    """获取任务状态分布数据"""
    try:
        # 获取任务按状态分布
        task_status_query = """
        SELECT status, COUNT(*) as count 
        FROM ad_tasks
        GROUP BY status
        """
        task_status_results = db.execute_query(task_status_query)
        
        statuses = []
        counts = []
        
        for result in task_status_results:
            status = result['status']
            # 美化状态名称
            if status == 'draft':
                status_name = '草稿'
            elif status == 'published':
                status_name = '已发布'
            elif status == 'in_progress':
                status_name = '进行中'
            elif status == 'completed':
                status_name = '已完成'
            elif status == 'cancelled':
                status_name = '已取消'
            else:
                status_name = status or '未知'
                
            statuses.append(status_name)
            counts.append(result['count'])
        
        return jsonify({
            "success": True,
            "data": {
                "statuses": statuses,
                "counts": counts
            }
        })
    except Exception as e:
        print(f"获取任务状态分布数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

# 辅助函数：格式化时间为"几分钟前"的形式
def format_time_ago(timestamp):
    if not timestamp:
        return '未知时间'
    
    from datetime import datetime
    now = datetime.now()
    diff = now - timestamp
    
    seconds = diff.total_seconds()
    if seconds < 60:
        return '刚刚'
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f'{minutes}分钟前'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours}小时前'
    else:
        days = int(seconds / 86400)
        return f'{days}天前'

# 辅助函数：格式化日期时间
def format_datetime(timestamp):
    if not timestamp:
        return '未知时间'
    
    from datetime import datetime, date
    today = date.today()
    
    if timestamp.date() == today:
        return f'今天 {timestamp.strftime("%H:%M")}'
    else:
        return timestamp.strftime("%m-%d %H:%M") 