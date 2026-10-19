from flask import flash

def notify_success(message, duration=2000, dismissible=False):
    """
    成功消息通知
    
    Args:
        message: 消息内容
        duration: 显示时长(毫秒)，0表示不自动关闭
        dismissible: 是否可手动关闭
    """
    flash({'message': message, 'duration': duration, 'dismissible': dismissible}, 'success')

def notify_info(message, duration=2000, dismissible=False):
    """
    信息类消息通知
    
    Args:
        message: 消息内容
        duration: 显示时长(毫秒)，0表示不自动关闭
        dismissible: 是否可手动关闭
    """
    flash({'message': message, 'duration': duration, 'dismissible': dismissible}, 'info')

def notify_warning(message, duration=2000, dismissible=False):
    """
    警告消息通知
    
    Args:
        message: 消息内容
        duration: 显示时长(毫秒)，0表示不自动关闭
        dismissible: 是否可手动关闭
    """
    flash({'message': message, 'duration': duration, 'dismissible': dismissible}, 'warning')

def notify_error(message, duration=2000, dismissible=False):
    """
    错误消息通知
    
    Args:
        message: 消息内容
        duration: 显示时长(毫秒)，0表示不自动关闭
        dismissible: 是否可手动关闭
    """
    flash({'message': message, 'duration': duration, 'dismissible': dismissible}, 'error')

def notify_primary(message, duration=2000, dismissible=False):
    """
    主要消息通知
    
    Args:
        message: 消息内容
        duration: 显示时长(毫秒)，0表示不自动关闭
        dismissible: 是否可手动关闭
    """
    flash({'message': message, 'duration': duration, 'dismissible': dismissible}, 'primary')

def notify_secondary(message, duration=2000, dismissible=False):
    """
    次要消息通知
    
    Args:
        message: 消息内容
        duration: 显示时长(毫秒)，0表示不自动关闭
        dismissible: 是否可手动关闭
    """
    flash({'message': message, 'duration': duration, 'dismissible': dismissible}, 'secondary')

def notify_system(message, duration=2000, dismissible=False):
    """
    系统消息通知
    
    Args:
        message: 消息内容
        duration: 显示时长(毫秒)，0表示不自动关闭
        dismissible: 是否可手动关闭
    """
    flash({'message': message, 'duration': duration, 'dismissible': dismissible}, 'system') 