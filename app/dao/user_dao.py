from app.dao.database import db

class UserDAO:
    def get_user_by_id(self, user_id, role):
        """通过ID获取用户信息"""
        table = self._get_table_by_role(role)
        query = f"SELECT * FROM {table} WHERE id = %s"
        return db.execute_one(query, (user_id,))
    
    def get_user_by_username(self, username, role=None):
        """通过用户名获取用户信息"""
        if role:
            table = self._get_table_by_role(role)
            query = f"SELECT *, '{role}' as role FROM {table} WHERE username = %s"
            return db.execute_one(query, (username,))
        else:
            # 如果未指定角色，则尝试在所有表中查找
            for r in ['admin', 'advertiser', 'collaborator']:
                table = self._get_table_by_role(r)
                query = f"SELECT *, '{r}' as role FROM {table} WHERE username = %s"
                user = db.execute_one(query, (username,))
                if user:
                    return user
            return None
    
    def get_user_by_email(self, email, role=None):
        """通过邮箱获取用户信息"""
        if role:
            table = self._get_table_by_role(role)
            query = f"SELECT * FROM {table} WHERE email = %s"
            return db.execute_one(query, (email,))
        else:
            # 如果未指定角色，则尝试在所有表中查找
            for r in ['admin', 'advertiser', 'collaborator']:
                table = self._get_table_by_role(r)
                query = f"SELECT * FROM {table} WHERE email = %s"
                user = db.execute_one(query, (email,))
                if user:
                    return user
            return None
    
    def create_user(self, username, email, password, role):
        """创建新用户"""
        table = self._get_table_by_role(role)
        if role == 'admin':
            query = f"""
            INSERT INTO {table} (username, email, password, created_at) 
            VALUES (%s, %s, %s, NOW())
            """
            return db.execute(query, (username, email, password))
        elif role == 'advertiser':
            query = f"""
            INSERT INTO {table} (username, email, password, company_name, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            """
            return db.execute(query, (username, email, password, '未设置'))
        else:  # collaborator
            query = f"""
            INSERT INTO {table} (username, email, password, created_at)
            VALUES (%s, %s, %s, NOW())
            """
            return db.execute(query, (username, email, password))
    
    def update_user(self, user_id, data):
        """更新用户信息"""
        set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
        values = list(data.values())
        values.append(user_id)
        
        query = f"UPDATE users SET {set_clause} WHERE id = %s"
        return db.execute(query, values)
    
    def delete_user(self, user_id):
        """删除用户"""
        query = "DELETE FROM users WHERE id = %s"
        return db.execute(query, (user_id,))
    
    def get_users_by_role(self, role, page=1, per_page=10):
        """获取指定角色的用户列表"""
        offset = (page - 1) * per_page
        query = "SELECT * FROM users WHERE role = %s LIMIT %s, %s"
        return db.execute_query(query, (role, offset, per_page))
    
    def count_users_by_role(self, role):
        """统计指定角色的用户数量"""
        query = "SELECT COUNT(*) AS count FROM users WHERE role = %s"
        result = db.execute_one(query, (role,))
        return result['count'] if result else 0
    
    def update_last_login(self, user_id, role):
        """更新用户最后登录时间"""
        table = self._get_table_by_role(role)
        query = f"UPDATE {table} SET last_login = NOW() WHERE id = %s"
        return db.execute(query, (user_id,))
    
    def update_collaborator(self, user_id, data):
        """更新合作者信息"""
        set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
        values = list(data.values())
        values.append(user_id)
        
        query = f"UPDATE collaborators SET {set_clause} WHERE id = %s"
        return db.execute(query, values)
    
    def get_all_collaborators(self, limit=None):
        """获取所有合作者信息，可选择限制数量"""
        if limit:
            query = "SELECT * FROM collaborators ORDER BY followers_count DESC LIMIT %s"
            return db.execute_query(query, (limit,))
        else:
            query = "SELECT * FROM collaborators ORDER BY followers_count DESC"
            return db.execute_query(query)
    
    def get_advertiser_by_id(self, advertiser_id):
        """通过ID获取广告主信息"""
        query = "SELECT * FROM advertisers WHERE id = %s"
        return db.execute_one(query, (advertiser_id,))
    
    def get_collaborator_by_id(self, collaborator_id):
        """通过ID获取合作者信息"""
        query = "SELECT * FROM collaborators WHERE id = %s"
        return db.execute_one(query, (collaborator_id,))
    
    def _get_table_by_role(self, role):
        """根据角色获取对应的表名"""
        if role == 'admin':
            return 'admins'
        elif role == 'advertiser':
            return 'advertisers'
        elif role == 'collaborator':
            return 'collaborators'
        else:
            raise ValueError(f"未知的用户角色: {role}")
    
    def update_user_balance(self, user_id, role, amount, is_add=True):
        """更新用户余额"""
        table = self._get_table_by_role(role)
        if is_add:
            query = f"UPDATE {table} SET balance = balance + %s WHERE id = %s"
        else:
            query = f"UPDATE {table} SET balance = balance - %s WHERE id = %s"
        return db.execute(query, (amount, user_id))

# 创建全局用户DAO实例
user_dao = UserDAO() 