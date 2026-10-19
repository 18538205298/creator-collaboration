import hashlib
from app.dao.user_dao import user_dao

class AuthService:
    def verify_login(self, username, password, role=None):
        """验证用户登录"""
        # 根据角色查询用户
        user = user_dao.get_user_by_username(username, role)
        if not user:
            return None
        
        # 验证密码
        if not self._verify_password(password, user.get('password')):
            return None
        
        # 更新最后登录时间
        user_dao.update_last_login(user['id'], user['role'])
            
        return user
    
    def register_user(self, username, email, password, role='collaborator'):
        """注册新用户"""
        # 检查用户名是否已存在
        if user_dao.get_user_by_username(username):
            return False, "用户名已存在"
            
        # 检查邮箱是否已存在
        if user_dao.get_user_by_email(email):
            return False, "邮箱已注册"
        
        # 创建用户
        result = user_dao.create_user(username, email, password, role)
        if result:
            return True, "注册成功"
        else:
            return False, "注册失败，请稍后重试"
    
    def _verify_password(self, input_password, stored_password):
        """验证密码是否匹配"""
        # 在这个简单实现中，我们假设存储的密码是明文的
        # 实际生产环境应该使用安全的密码哈希算法
        return input_password == stored_password
    
    def _hash_password(self, password):
        """密码哈希处理"""
        # 注意：在真实环境中应使用更安全的方法，如bcrypt
        # 但在当前系统中似乎使用的是明文存储
        return password

# 创建全局认证服务实例
auth_service = AuthService() 