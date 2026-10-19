import pymysql
from app.config.settings import DB_CONFIG

class Database:
    """数据库操作类，提供基础的数据库增删改查功能"""
    
    def __init__(self, config=None):
        self.config = config or DB_CONFIG
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            connection = pymysql.connect(
                host=self.config['host'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return connection
        except Exception as e:
            print(f"数据库连接失败: {str(e)}")
            return None
    
    def fetch_one(self, sql, params=None):
        """执行查询并返回单条记录"""
        connection = None
        try:
            connection = self.get_connection()
            if not connection:
                return None
                
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchone()
                return result
        except Exception as e:
            print(f"查询单条记录失败: {str(e)}")
            return None
        finally:
            if connection:
                connection.close()
    
    def fetch_all(self, sql, params=None):
        """执行查询并返回所有记录"""
        connection = None
        try:
            connection = self.get_connection()
            if not connection:
                return []
                
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                results = cursor.fetchall()
                return results
        except Exception as e:
            print(f"查询所有记录失败: {str(e)}")
            return []
        finally:
            if connection:
                connection.close()
    
    def execute(self, sql, params=None):
        """执行插入、更新或删除操作"""
        connection = None
        try:
            connection = self.get_connection()
            if not connection:
                return False
                
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                connection.commit()
                return cursor.lastrowid or cursor.rowcount  # 返回自增ID或影响的行数
        except Exception as e:
            if connection:
                connection.rollback()
            print(f"执行SQL操作失败: {str(e)}")
            return False
        finally:
            if connection:
                connection.close()
    
    def execute_insert(self, sql, params=None):
        """执行插入操作并返回插入ID"""
        connection = None
        try:
            connection = self.get_connection()
            if not connection:
                return None
                
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                connection.commit()
                return cursor.lastrowid  # 返回自增ID
        except Exception as e:
            if connection:
                connection.rollback()
            print(f"执行插入操作失败: {str(e)}")
            return None
        finally:
            if connection:
                connection.close()
    
    def execute_many(self, sql, params_list):
        """批量执行插入、更新或删除操作"""
        connection = None
        try:
            connection = self.get_connection()
            if not connection:
                return False
                
            with connection.cursor() as cursor:
                cursor.executemany(sql, params_list)
                connection.commit()
                return cursor.rowcount  # 返回影响的行数
        except Exception as e:
            if connection:
                connection.rollback()
            print(f"批量执行SQL操作失败: {str(e)}")
            return False
        finally:
            if connection:
                connection.close()

# 创建全局数据库操作实例
db = Database() 