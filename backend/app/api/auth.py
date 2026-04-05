#  新建用户接口 在powershell执行 New-Item -ItemType File -Path app/api/auth.py -Force 建文件然后把下面复制进去
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
from pydantic import BaseModel, ConfigDict
from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.auth import hash_password, verify_password, create_access_token
from app.models.department import Department, DepartmentMembership
from app.models.user import User

router = APIRouter()

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

@router.post(
    "/auth/register",
    response_model=TokenResponse,
    summary="用户注册",
    description="注册新用户并返回访问令牌。 Register a new user and return an access token.",
)
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
    return {"access_token": token, "token_type": "bearer"}

@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="用户登录",
    description="使用邮箱和密码登录并返回访问令牌。 Log in with email and password and return an access token.",
)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": token, "token_type": "bearer"}

@router.get(
    "/auth/me",
    summary="当前用户",
    description="获取当前登录用户的信息。 Get the currently authenticated user's profile.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前登录用户信息"""
    membership_result = await db.execute(
        select(DepartmentMembership, Department)
        .join(Department, Department.id == DepartmentMembership.department_id)
        .where(
            and_(
                DepartmentMembership.user_id == current_user.id,
                DepartmentMembership.status == "active",
            )
        )
        .order_by(DepartmentMembership.is_primary.desc(), Department.id.asc())
    )
    memberships = []
    for membership, department in membership_result.all():
        memberships.append(
            {
                "id": membership.id,
                "department_id": department.id,
                "department_name": department.name,
                "department_code": department.code,
                "membership_type": membership.membership_type,
                "is_primary": membership.is_primary,
                "status": membership.status,
            }
        )

    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "organization_status": "ready" if memberships else "pending_assignment",
        "memberships": memberships,
    }
