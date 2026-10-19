from functools import wraps
from flask import session, redirect, url_for
from app.web.utils.notifications import notify_error, notify_warning

def login_required(f):
    """确保用户已登录的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            notify_warning('请先登录再访问该页面')
            return redirect(url_for('index.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """确保用户是管理员的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            notify_warning('请先登录再访问该页面')
            return redirect(url_for('index.login'))
        if session.get('role') != 'admin':
            notify_error('只有管理员才能访问该页面')
            return redirect(url_for('index.index'))
        return f(*args, **kwargs)
    return decorated_function

def advertiser_required(f):
    """确保用户是广告主的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            notify_warning('请先登录再访问该页面')
            return redirect(url_for('index.login'))
        if session.get('role') != 'advertiser':
            notify_error('只有广告主才能访问该页面')
            return redirect(url_for('index.index'))
        return f(*args, **kwargs)
    return decorated_function

def collaborator_required(f):
    """确保用户是合作者的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            notify_warning('请先登录再访问该页面')
            return redirect(url_for('index.login'))
        if session.get('role') != 'collaborator':
            notify_error('只有合作者才能访问该页面')
            return redirect(url_for('index.index'))
        return f(*args, **kwargs)
    return decorated_function 