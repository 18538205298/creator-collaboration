# 系统配置文件，存放所有环境变量和配置项 # 数据库配置和系统设置集中管理

import os
from datetime import timedelta
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

# 数据库配置（支持环境变量）
MYSQL_HOST = os.getenv('DB_HOST', 'localhost')
MYSQL_USER = os.getenv('DB_USER', 'root')
MYSQL_PASSWORD = os.getenv('DB_PASSWORD', 'REDACTED_LOCAL_SECRET')
MYSQL_DB = os.getenv('DB_NAME', 'AdConnectDB')
MYSQL_PORT = int(os.getenv('DB_PORT', 3306))
MYSQL_CHARSET = 'utf8mb4'

# 统一的数据库配置字典
DB_CONFIG = {
    'host': MYSQL_HOST,
    'user': MYSQL_USER,
    'password': MYSQL_PASSWORD,
    'database': MYSQL_DB,
    'port': MYSQL_PORT,
    'charset': MYSQL_CHARSET
}

# 应用配置
SECRET_KEY = os.getenv('SECRET_KEY', 'REDACTED_LOCAL_SECRET')  # 用于会话安全的密钥
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'  # 开发环境设置为True，生产环境设置为False
SESSION_COOKIE_HTTPONLY = True
PERMANENT_SESSION_LIFETIME = timedelta(days=7)

# 分页配置
ITEMS_PER_PAGE = 20  # 每页显示条目数

# 上传文件存储路径配置
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'app/web/static/img/avatars')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# 日期格式化
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S' 