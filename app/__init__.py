from flask import Flask
from app.config.settings import SECRET_KEY, DEBUG, UPLOAD_FOLDER
import os

def create_app():
    """应用工厂函数，用于创建Flask应用实例"""
    app = Flask(__name__, static_folder='web/static', template_folder='web/templates')
    
    # 配置应用
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['DEBUG'] = DEBUG
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['JSON_AS_ASCII'] = False  # 确保JSON响应支持中文
    app.config['JSONIFY_MIMETYPE'] = 'application/json;charset=utf-8'  # 显式设置MIME类型
    app.config['APPLICATION_ROOT'] = os.getenv('APPLICATION_ROOT', '/')  # 支持子路径部署
    
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 自定义过滤器
    @app.template_filter('date')
    def format_date(value):
        """格式化日期为YYYY-MM-DD格式"""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return value.strftime('%Y-%m-%d')
    
    # 注册蓝图
    # 只导入api蓝图，用于任务详情API
    from app.web.routes.api import api_bp
    app.register_blueprint(api_bp)
    
    # 如果有现有的蓝图，则导入并注册
    try:
        # 尝试导入现有蓝图
        from app.web.routes import index_bp, advertiser_bp, collaborator_bp, admin_bp
        app.register_blueprint(index_bp)
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(advertiser_bp, url_prefix='/advertiser')
        app.register_blueprint(collaborator_bp, url_prefix='/collaborator')
    except ImportError as e:
        print(f"注意: 部分蓝图导入失败 - {str(e)}")
    
    # 初始化数据库连接
    from app.dao.db import db
    
    # 初始化扩展和自定义过滤器（如果存在）
    try:
        from app.web.extensions import setup_extensions
        setup_extensions(app)
    except ImportError:
        print("注意: 未找到扩展模块")
    
    # 注册应用关闭时的数据库连接释放
    @app.teardown_appcontext
    def close_db_connection(exception=None):
        pass  # 由于我们的db实现不需要显式关闭，这里留空
    
    return app