from flask import Flask
import locale
from markupsafe import Markup
from datetime import datetime

def setup_extensions(app: Flask):
    """初始化Flask扩展和自定义过滤器"""
    
    # 注册自定义过滤器
    register_filters(app)

def register_filters(app: Flask):
    """注册Jinja2自定义过滤器"""
    
    # 日期格式化过滤器
    @app.template_filter('date')
    def date_filter(value, format='%Y-%m-%d'):
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    value = datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    return value
        return value.strftime(format)
    
    # 日期时间格式化过滤器
    @app.template_filter('date_time')
    def date_time_filter(value, format='%Y-%m-%d %H:%M'):
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    value = datetime.strptime(value, '%Y-%m-%d %H:%M')
                except ValueError:
                    return value
        return value.strftime(format)
    
    # 数字格式化过滤器
    @app.template_filter('number_format')
    def number_format_filter(value):
        if value is None:
            return '0'
        try:
            locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_ALL, 'Chinese_China.936')
            except:
                pass
        
        try:
            value = float(value)
            if value.is_integer():
                return locale.format_string("%d", int(value), grouping=True)
            else:
                return locale.format_string("%.2f", value, grouping=True)
        except (ValueError, TypeError):
            return str(value)
    
    # 换行符转HTML过滤器
    @app.template_filter('nl2br')
    def nl2br_filter(value):
        if value is None:
            return ''
        value = str(value).replace('\r\n', '\n').replace('\r', '\n')
        return Markup(value.replace('\n', '<br>')) 