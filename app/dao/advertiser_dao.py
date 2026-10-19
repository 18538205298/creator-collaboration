from app.dao.db import db
from app.config.settings import DB_CONFIG
from datetime import datetime, timedelta

class AdvertiserDAO:
    """广告主数据访问对象"""
    
    @staticmethod
    def get_advertiser_by_id(advertiser_id):
        """根据ID获取广告主信息"""
        try:
            sql = """
                SELECT * FROM advertisers
                WHERE id = %s
            """
            result = db.fetch_one(sql, (advertiser_id,))
            return result
        except Exception as e:
            print(f"获取广告主信息出错: {str(e)}")
            return None
    
    @staticmethod
    def get_advertiser_by_username(username):
        """根据用户名获取广告主信息"""
        try:
            sql = """
                SELECT * FROM advertisers
                WHERE username = %s
            """
            result = db.fetch_one(sql, (username,))
            return result
        except Exception as e:
            print(f"通过用户名获取广告主信息出错: {str(e)}")
            return None
    
    @staticmethod
    def authenticate(username, password):
        """广告主登录认证"""
        try:
            sql = """
                SELECT * FROM advertisers
                WHERE username = %s AND password = %s
            """
            result = db.fetch_one(sql, (username, password))
            return result
        except Exception as e:
            print(f"广告主登录认证出错: {str(e)}")
            return None
    
    @staticmethod
    def update_last_login(advertiser_id):
        """更新广告主最后登录时间"""
        try:
            sql = """
                UPDATE advertisers
                SET last_login = NOW()
                WHERE id = %s
            """
            db.execute(sql, (advertiser_id,))
            return True
        except Exception as e:
            print(f"更新广告主登录时间出错: {str(e)}")
            return False
    
    @staticmethod
    def update_advertiser_profile(advertiser_id, profile_data):
        """更新广告主个人资料"""
        try:
            set_clause = ", ".join([f"{key} = %s" for key in profile_data.keys()])
            values = list(profile_data.values())
            values.append(advertiser_id)
            
            sql = f"""
                UPDATE advertisers
                SET {set_clause}
                WHERE id = %s
            """
            
            db.execute(sql, tuple(values))
            return True
        except Exception as e:
            print(f"更新广告主资料出错: {str(e)}")
            return False
    
    @staticmethod
    def get_all_advertisers():
        """获取所有广告主列表"""
        try:
            sql = """
                SELECT * FROM advertisers
                ORDER BY id
            """
            results = db.fetch_all(sql)
            return results
        except Exception as e:
            print(f"获取所有广告主列表出错: {str(e)}")
            return []
    
    @staticmethod
    def create_advertiser(data):
        """创建新广告主"""
        try:
            # 准备需要插入的字段
            fields = []
            values = []
            placeholders = []
            
            # 必填字段
            required_fields = {
                'username': data.get('username'),
                'password': data.get('password'),
                'email': data.get('email'),
                'company_name': data.get('company_name')
            }
            
            # 检查必填字段
            for field, value in required_fields.items():
                if not value:
                    raise ValueError(f"缺少必填字段: {field}")
                fields.append(field)
                values.append(value)
                placeholders.append('%s')
            
            # 可选字段
            optional_fields = {
                'industry': data.get('industry'),
                'phone_number': data.get('phone_number'),
                'avatar_url': data.get('avatar_url')
            }
            
            for field, value in optional_fields.items():
                if value:
                    fields.append(field)
                    values.append(value)
                    placeholders.append('%s')
            
            # 添加创建时间字段
            fields.append('created_at')
            values.append('NOW()')
            placeholders.append('NOW()')
            
            # 构建SQL语句
            sql = f"""
                INSERT INTO advertisers ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
            """
            
            # 执行SQL并获取新插入的ID
            advertiser_id = db.execute_insert(sql, tuple(values))
            return advertiser_id
        except Exception as e:
            print(f"创建广告主出错: {str(e)}")
            return None
    
    @staticmethod
    def update_advertiser(advertiser_id, data):
        """更新广告主信息"""
        try:
            # 准备需要更新的字段
            update_fields = []
            values = []
            
            # 可更新字段列表
            allowed_fields = [
                'username', 'email', 'company_name', 'industry', 
                'phone_number', 'avatar_url'
            ]
            
            # 如果有密码字段，单独处理
            if 'password' in data and data['password']:
                allowed_fields.append('password')
            
            # 构建更新语句
            for field in allowed_fields:
                if field in data and data[field] is not None:
                    update_fields.append(f"{field} = %s")
                    values.append(data[field])
            
            # 如果没有要更新的字段，直接返回成功
            if not update_fields:
                return True
            
            # 添加ID到值列表
            values.append(advertiser_id)
            
            # 构建SQL语句
            sql = f"""
                UPDATE advertisers
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            # 执行SQL
            db.execute(sql, tuple(values))
            return True
        except Exception as e:
            print(f"更新广告主信息出错: {str(e)}")
            return False
    
    @staticmethod
    def delete_advertiser(advertiser_id):
        """删除广告主"""
        try:
            sql = """
                DELETE FROM advertisers
                WHERE id = %s
            """
            db.execute(sql, (advertiser_id,))
            return True
        except Exception as e:
            print(f"删除广告主出错: {str(e)}")
            return False
    
    @staticmethod
    def get_advertisers_count():
        """获取广告主总数"""
        try:
            sql = "SELECT COUNT(*) as count FROM advertisers"
            result = db.fetch_one(sql)
            return result['count'] if result else 0
        except Exception as e:
            print(f"获取广告主总数出错: {str(e)}")
            return 0
    
    @staticmethod
    def get_active_advertisers_count(days=30):
        """获取指定天数内活跃的广告主数量"""
        try:
            date_threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            sql = """
                SELECT COUNT(*) as count FROM advertisers
                WHERE last_login >= %s
            """
            result = db.fetch_one(sql, (date_threshold,))
            return result['count'] if result else 0
        except Exception as e:
            print(f"获取活跃广告主数量出错: {str(e)}")
            return 0
    
    @staticmethod
    def get_new_advertisers_count(days=30):
        """获取指定天数内新增的广告主数量"""
        try:
            date_threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            sql = """
                SELECT COUNT(*) as count FROM advertisers
                WHERE created_at >= %s
            """
            result = db.fetch_one(sql, (date_threshold,))
            return result['count'] if result else 0
        except Exception as e:
            print(f"获取新增广告主数量出错: {str(e)}")
            return 0
    
    @staticmethod
    def get_monthly_growth(months=12):
        """获取过去N个月的广告主增长数据"""
        try:
            growth_data = []
            current_date = datetime.now()
            for i in range(months):
                # 计算每个月的开始和结束日期
                end_date = (current_date - timedelta(days=30*i)).strftime('%Y-%m-%d 23:59:59')
                start_date = (current_date - timedelta(days=30*(i+1))).strftime('%Y-%m-%d 00:00:00')
                
                sql = """
                    SELECT COUNT(*) as count FROM advertisers
                    WHERE created_at BETWEEN %s AND %s
                """
                result = db.fetch_one(sql, (start_date, end_date))
                growth_data.insert(0, result['count'] if result else 0)
            
            return growth_data
        except Exception as e:
            print(f"获取广告主月增长数据出错: {str(e)}")
            return [0] * months
    
    @staticmethod
    def get_industry_distribution():
        """获取广告主行业分布数据"""
        try:
            sql = """
                SELECT industry, COUNT(*) as count 
                FROM advertisers 
                GROUP BY industry 
                ORDER BY count DESC
            """
            results = db.fetch_all(sql)
            return results
        except Exception as e:
            print(f"获取广告主行业分布数据出错: {str(e)}")
            return []
    
    @staticmethod
    def get_budget_distribution(ranges):
        """获取广告主预算范围分布"""
        try:
            result_data = []
            
            for range_item in ranges:
                min_value = range_item['min']
                max_value = range_item['max']
                
                if max_value == float('inf'):
                    sql = """
                        SELECT COUNT(*) as count FROM advertisers
                        WHERE average_budget > %s
                    """
                    result = db.fetch_one(sql, (min_value,))
                else:
                    sql = """
                        SELECT COUNT(*) as count FROM advertisers
                        WHERE average_budget > %s AND average_budget <= %s
                    """
                    result = db.fetch_one(sql, (min_value, max_value))
                
                result_data.append({
                    'name': range_item['name'],
                    'count': result['count'] if result else 0
                })
            
            return result_data
        except Exception as e:
            print(f"获取广告主预算分布数据出错: {str(e)}")
            return [{'name': r['name'], 'count': 0} for r in ranges]
    
    @staticmethod
    def get_daily_activity(days=7):
        """获取过去N天的广告主活跃度数据"""
        try:
            activity_data = []
            
            # 假设我们使用的是登录记录作为活跃度指标
            # 实际应用中，可能需要使用专门的用户活动日志表
            current_date = datetime.now()
            
            for i in range(days):
                day = (current_date - timedelta(days=i)).strftime('%Y-%m-%d')
                day_start = f"{day} 00:00:00"
                day_end = f"{day} 23:59:59"
                
                sql = """
                    SELECT COUNT(DISTINCT id) as count FROM advertisers
                    WHERE last_login BETWEEN %s AND %s
                """
                result = db.fetch_one(sql, (day_start, day_end))
                # 将结果添加到列表开头，使最早的日期在前
                activity_data.insert(0, result['count'] if result else 0)
            
            return activity_data
        except Exception as e:
            print(f"获取广告主活跃度数据出错: {str(e)}")
            return [0] * days 