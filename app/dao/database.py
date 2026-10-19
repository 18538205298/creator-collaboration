import pymysql
from pymysql.cursors import DictCursor
from app.config.settings import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_PORT, MYSQL_CHARSET

class Database:
    def __init__(self):
        self.conn = None
    
    def connect(self):
        """创建数据库连接并返回连接对象"""
        if self.conn is None:
            self.conn = pymysql.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                db=MYSQL_DB,
                port=MYSQL_PORT,
                charset=MYSQL_CHARSET,
                cursorclass=DictCursor
            )
        return self.conn
    
    def execute_query(self, query, params=None):
        """执行SELECT查询并返回结果"""
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        except Exception as e:
            print(f"查询错误: {e}")
            return []
    
    def execute_one(self, query, params=None):
        """执行SELECT查询并返回单条结果"""
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchone()
        except Exception as e:
            print(f"查询错误: {e}")
            return None
    
    def execute(self, query, params=None):
        """执行INSERT/UPDATE/DELETE操作并返回影响的行数"""
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(query, params or ())
                conn.commit()
                return affected_rows
        except Exception as e:
            conn.rollback()
            print(f"执行错误: {e}")
            return 0
    
    def get_last_insert_id(self):
        """获取最后插入的自增ID"""
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT LAST_INSERT_ID() as id")
                result = cursor.fetchone()
                return result['id'] if result else 0
        except Exception as e:
            print(f"获取最后插入ID错误: {e}")
            return 0
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    # 添加别名方法，以兼容其他代码中的调用
    def fetch_one(self, query, params=None):
        """execute_one的别名方法，保持兼容性"""
        return self.execute_one(query, params)
    
    def fetch_all(self, query, params=None):
        """execute_query的别名方法，保持兼容性"""
        return self.execute_query(query, params)

# 创建全局数据库实例供应用使用
db = Database() 