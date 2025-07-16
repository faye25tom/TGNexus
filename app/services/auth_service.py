from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import os
import secrets
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8小时

# HTTP Bearer 认证
security = HTTPBearer()

class AuthService:
    """认证服务"""
    
    def __init__(self):
        # 从环境变量读取管理员账户配置
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        
        self.admin_users = {
            admin_username: {
                "username": admin_username,
                "hashed_password": self.get_password_hash(admin_password),
                "is_active": True,
                "failed_attempts": 0,
                "locked_until": None
            }
        }
        
        # 安全配置
        self.max_failed_attempts = 5  # 最大失败尝试次数
        self.lockout_duration = 15  # 锁定时间（分钟）
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希"""
        return pwd_context.hash(password)
    
    def is_account_locked(self, username: str) -> bool:
        """检查账户是否被锁定"""
        user = self.admin_users.get(username)
        if not user or not user.get("locked_until"):
            return False
        
        if datetime.now() < user["locked_until"]:
            return True
        else:
            # 锁定时间已过，重置状态
            user["locked_until"] = None
            user["failed_attempts"] = 0
            return False
    
    def lock_account(self, username: str):
        """锁定账户"""
        user = self.admin_users.get(username)
        if user:
            user["locked_until"] = datetime.now() + timedelta(minutes=self.lockout_duration)
            logger.warning(f"账户 {username} 已被锁定 {self.lockout_duration} 分钟")
    
    def record_failed_attempt(self, username: str):
        """记录失败尝试"""
        user = self.admin_users.get(username)
        if user:
            user["failed_attempts"] = user.get("failed_attempts", 0) + 1
            if user["failed_attempts"] >= self.max_failed_attempts:
                self.lock_account(username)
    
    def reset_failed_attempts(self, username: str):
        """重置失败尝试次数"""
        user = self.admin_users.get(username)
        if user:
            user["failed_attempts"] = 0
            user["locked_until"] = None
    
    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """验证用户"""
        user = self.admin_users.get(username)
        if not user:
            return None
        
        # 检查账户是否被锁定
        if self.is_account_locked(username):
            locked_until = user["locked_until"]
            remaining_time = int((locked_until - datetime.now()).total_seconds() / 60)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"账户已被锁定，请 {remaining_time} 分钟后再试"
            )
        
        # 验证密码
        if not self.verify_password(password, user["hashed_password"]):
            self.record_failed_attempt(username)
            return None
        
        # 登录成功，重置失败次数
        self.reset_failed_attempts(username)
        return user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return {"username": username}
        except JWTError:
            return None
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
        """获取当前用户"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        token = credentials.credentials
        token_data = self.verify_token(token)
        if token_data is None:
            raise credentials_exception
        
        user = self.admin_users.get(token_data["username"])
        if user is None:
            raise credentials_exception
        
        return user
    
    def check_session(self, request: Request) -> bool:
        """检查会话状态"""
        token = request.cookies.get("access_token")
        if not token:
            return False
        
        token_data = self.verify_token(token)
        return token_data is not None
    
    def update_password(self, username: str, new_password: str) -> bool:
        """更新用户密码"""
        try:
            if username in self.admin_users:
                self.admin_users[username]["hashed_password"] = self.get_password_hash(new_password)
                logger.info(f"用户 {username} 密码已更新")
                return True
            return False
        except Exception as e:
            logger.error(f"更新密码失败: {e}")
            return False

# 全局认证服务实例
auth_service = AuthService()