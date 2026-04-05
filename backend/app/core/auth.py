# 密码哈希、JWT 生成和验证，相当于 NestJS 的 AuthService。

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from app.core.paths import ensure_env_loaded

ensure_env_loaded()

JWT_SECRET = os.getenv("JWT_SECRET", "fallback-secret-change-me")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 1440))
ALGORITHM = "HS256"

# 密码哈希工具
# 这里使用 pbkdf2_sha256，避免 passlib 1.7.4 与 bcrypt 5.x 的兼容问题，
# 否则注册/登录时会在密码哈希阶段直接抛 500。
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    """把明文密码哈希加密"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码和哈希密码是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """生成 JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """解码并验证 JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
