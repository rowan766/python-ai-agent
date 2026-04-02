#  新建用户接口 在powershell执行 New-Item -ItemType File -Path app/api/auth.py -Force 建文件然后把下面复制进去
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, ConfigDict
from app.core.database import get_db
from app.core.auth import hash_password, verify_password, create_access_token, decode_token
from app.models.user import User

router = APIRouter()
security = HTTPBearer()

# 请求/响应数据结构
class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "570436048@qq.com",
                "username": "zhanghuan_test_fix",
                "password": "zhanghuan@123456",
            }
        }
    )

class LoginRequest(BaseModel):
    email: str
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "570436048@qq.com",
                "password": "zhanghuan@123456",
            }
        }
    )

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/auth/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户"""
    # 检查邮箱是否已注册
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该邮箱已被注册")

    # 创建用户，密码哈希存储
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hash_password(request.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 注册成功后直接返回 token
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": token}

@router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": token}

@router.get("/auth/me")
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """获取当前登录用户信息"""
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {"id": user.id, "email": user.email, "username": user.username}
