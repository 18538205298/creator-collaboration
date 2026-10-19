from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from app.domain.auth.services import auth_service
from app.web.utils.notifications import notify_success, notify_error, notify_info, notify_warning
from app.web.utils.notifications import notify_primary, notify_secondary, notify_system
from app.dao.user_dao import user_dao
from app.dao.database import db

index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    return render_template('index/index.html')

@index_bp.route('/notifications-demo')
def notifications_demo():
    """通知系统演示页面"""
    # 所有消息均为2秒显示且不可手动关闭
    notify_success('这是一条成功消息 - 2秒后自动关闭且不可手动关闭')
    notify_info('这是一条信息提示 - 2秒后自动关闭且不可手动关闭')
    notify_warning('这是一条警告消息 - 2秒后自动关闭且不可手动关闭')
    notify_error('这是一条错误消息 - 2秒后自动关闭且不可手动关闭')
    notify_primary('这是一条主要消息 - 2秒后自动关闭且不可手动关闭')
    notify_secondary('这是一条次要消息 - 2秒后自动关闭且不可手动关闭')
    notify_system('这是一条系统消息 - 2秒后自动关闭且不可手动关闭')
    
    # 如果需要自定义时长或可关闭性，仍可通过参数指定
    # notify_success('自定义显示时长为5秒', duration=5000, dismissible=True)
    
    return render_template('index/index.html')

@index_bp.route('/login')
def login():
    return render_template('index/login.html')

@index_bp.route('/login_submit', methods=['POST'])
def login_submit():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    
    # 使用指定角色验证登录
    user = auth_service.verify_login(username, password, role)
    
    if not user:
        notify_error('用户名或密码错误')
        return redirect(url_for('index.login'))
    
    # 登录成功，存储用户信息到会话
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['user_type'] = user['role']  # 添加user_type
    
    # 添加头像信息到会话
    if 'avatar_url' in user:
        session['avatar_url'] = user['avatar_url']
    
    # 登录成功通知
    notify_success(f'欢迎回来，{user["username"]}')
    
    # 根据角色重定向到相应页面
    if user['role'] == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif user['role'] == 'collaborator':
        return redirect(url_for('collaborator.home'))
    else:  # advertiser
        return redirect(url_for('advertiser.home'))

@index_bp.route('/register')
def register():
    return render_template('index/register.html')

@index_bp.route('/register_submit', methods=['POST'])
def register_submit():
    username = request.form.get('username')
    email = request.form.get('email')
    phone_number = request.form.get('phone_number')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    role = request.form.get('role', 'collaborator')
    
    # 简单的表单验证
    if not all([username, email, password, confirm_password]):
        notify_warning('所有字段都为必填项')
        return redirect(url_for('index.register'))
    
    if password != confirm_password:
        notify_error('两次输入的密码不一致')
        return redirect(url_for('index.register'))
    
    # 验证用户名长度
    if len(username) < 4 or len(username) > 20:
        notify_error('用户名长度必须在4-20个字符之间')
        return redirect(url_for('index.register'))
    
    # 验证密码强度
    if len(password) < 8:
        notify_error('密码长度至少为8位')
        return redirect(url_for('index.register'))
    
    # 检查用户名和邮箱是否已存在
    if user_dao.get_user_by_username(username):
        notify_error('用户名已被注册')
        return redirect(url_for('index.register'))
    
    if user_dao.get_user_by_email(email):
        notify_error('邮箱已被注册')
        return redirect(url_for('index.register'))
    
    # 准备注册数据
    user_data = {
        'username': username,
        'email': email,
        'password': password,
        'phone_number': phone_number
    }
    
    # 根据角色注册用户
    if role == 'advertiser':
        # 广告主默认公司名称
        user_data['company_name'] = '未设置'
        query = """
        INSERT INTO advertisers (username, email, password, phone_number, company_name, created_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        """
        params = (username, email, password, phone_number, user_data['company_name'])
    else:  # 默认为合作者
        query = """
        INSERT INTO collaborators (username, email, password, phone_number, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        """
        params = (username, email, password, phone_number)
    
    # 执行注册
    try:
        result = db.execute(query, params)
        if result:
            notify_success('注册成功，请登录')
            return redirect(url_for('index.login'))
        else:
            notify_error('注册失败，请稍后重试')
            return redirect(url_for('index.register'))
    except Exception as e:
        print(f"注册错误: {e}")
        notify_error('注册过程中出现错误，请稍后重试')
        return redirect(url_for('index.register'))

@index_bp.route('/admin_login')
def admin_login():
    return render_template('index/admin_login.html')

@index_bp.route('/admin_login_submit', methods=['POST'])
def admin_login_submit():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # 指定角色为admin进行验证
    user = auth_service.verify_login(username, password, 'admin')
    
    if not user:
        notify_error('管理员账号或密码错误')
        return redirect(url_for('index.admin_login'))
    
    # 登录成功，存储管理员信息到会话
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = 'admin'
    session['user_type'] = 'admin'  # 添加user_type，与普通用户登录保持一致
    
    # 管理员登录成功通知
    notify_success(f'欢迎回来，管理员 {user["username"]}')
    
    return redirect(url_for('admin.dashboard'))

@index_bp.route('/logout')
def logout():
    username = session.get('username', '')
    # 清除会话数据
    session.clear()
    notify_info(f'已成功退出登录，再见 {username}')
    return redirect(url_for('index.index')) 