import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, is_platform_admin
from app.core.auth import create_access_token
from app.core.captcha import (
    CAPTCHA_EXPIRE_MINUTES,
    build_captcha_data_url,
    build_captcha_svg,
    create_captcha_token,
    generate_captcha_code,
    verify_captcha_token,
)
from app.core.database import get_db
from app.core.mail import send_password_reset_email, should_expose_reset_code
from app.models.department import Department, DepartmentMembership
from app.models.password_reset import PasswordResetCode
from app.models.user import User
from app.core.auth import hash_password, verify_password

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

PASSWORD_RESET_CODE_EXPIRE_MINUTES = int(os.getenv("PASSWORD_RESET_CODE_EXPIRE_MINUTES", "10"))


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str = Field(min_length=6)

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
    account: str | None = None
    email: str | None = None
    password: str
    captcha_code: str = Field(min_length=4, max_length=8)
    captcha_token: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account": "zhanghuan_test_fix",
                "password": "zhanghuan@123456",
                "captcha_code": "ABCDX",
                "captcha_token": "captcha-jwt-token",
            }
        }
    )


class LoginCaptchaResponse(BaseModel):
    captcha_token: str
    image_data: str
    expires_in_minutes: int


class PasswordResetCodeRequest(BaseModel):
    email: str


class PasswordResetCodeResponse(BaseModel):
    message: str
    expires_in_minutes: int
    debug_code: str | None = None


class PasswordResetConfirmRequest(BaseModel):
    email: str
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def generate_reset_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


@router.get(
    "/auth/login-captcha",
    response_model=LoginCaptchaResponse,
    summary="获取登录验证码",
    description="生成用于登录表单的字母图形验证码。 Generate a letter-based captcha for the login form.",
)
async def get_login_captcha():
    code = generate_captcha_code()
    token = create_captcha_token(code)
    svg = build_captcha_svg(code)
    return {
        "captcha_token": token,
        "image_data": build_captcha_data_url(svg),
        "expires_in_minutes": CAPTCHA_EXPIRE_MINUTES,
    }


async def build_user_profile(current_user: User, db: AsyncSession) -> dict:
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
        "is_active": current_user.is_active,
        "is_platform_admin": is_platform_admin(current_user),
        "organization_status": "ready" if memberships else "pending_assignment",
        "memberships": memberships,
    }


@router.post(
    "/auth/register",
    response_model=TokenResponse,
    summary="用户注册",
    description="注册新用户并返回访问令牌。 Register a new user and return an access token.",
)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    normalized_email = request.email.strip().lower()
    normalized_username = request.username.strip()

    existing_user_result = await db.execute(
        select(User).where(or_(User.email == normalized_email, User.username == normalized_username))
    )
    if existing_user_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该邮箱或用户名已被使用")

    user = User(
        email=normalized_email,
        username=normalized_username,
        hashed_password=hash_password(request.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="用户登录",
    description="使用账户或邮箱和密码登录并返回访问令牌。 Log in with username/email and password and return an access token.",
)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    identifier = (request.account or request.email or "").strip()
    if not identifier:
        raise HTTPException(status_code=422, detail="请输入账号或邮箱")
    if not verify_captcha_token(request.captcha_token, request.captcha_code):
        raise HTTPException(status_code=400, detail="图形验证码错误或已过期")

    result = await db.execute(
        select(User).where(or_(User.email == identifier.lower(), User.username == identifier))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="账号或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.post(
    "/auth/password-reset/code",
    response_model=PasswordResetCodeResponse,
    summary="发送重置验证码",
    description="向用户邮箱发送 6 位密码重置验证码。 Send a password reset code to the user's email.",
)
async def send_password_reset_code(
    request: PasswordResetCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    normalized_email = request.email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    debug_code: str | None = None

    if user:
        existing_codes_result = await db.execute(
            select(PasswordResetCode).where(
                and_(
                    PasswordResetCode.user_id == user.id,
                    PasswordResetCode.consumed_at.is_(None),
                )
            )
        )
        now = datetime.now(timezone.utc)
        for existing_code in existing_codes_result.scalars():
            existing_code.consumed_at = now

        code = generate_reset_code()
        expires_at = now + timedelta(minutes=PASSWORD_RESET_CODE_EXPIRE_MINUTES)
        reset_code = PasswordResetCode(
            user_id=user.id,
            email=user.email,
            code=code,
            expires_at=expires_at,
        )
        db.add(reset_code)
        await db.commit()

        if should_expose_reset_code():
            debug_code = code

        try:
            delivered = send_password_reset_email(
                recipient_email=user.email,
                code=code,
                expires_minutes=PASSWORD_RESET_CODE_EXPIRE_MINUTES,
            )
            if not delivered:
                logger.info("密码重置验证码未真正发送，当前为开发兜底模式。 email=%s", user.email)
        except Exception:
            logger.exception("发送密码重置邮件失败，email=%s", user.email)

    return {
        "message": "如果该邮箱已注册，验证码已发送，请前往邮箱查收。",
        "expires_in_minutes": PASSWORD_RESET_CODE_EXPIRE_MINUTES,
        "debug_code": debug_code,
    }


@router.post(
    "/auth/password-reset/confirm",
    summary="重置密码",
    description="使用邮箱验证码重置密码。 Reset password with email verification code.",
)
async def confirm_password_reset(
    request: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    normalized_email = request.email.strip().lower()
    user_result = await db.execute(select(User).where(User.email == normalized_email))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="验证码无效或已过期")

    code_result = await db.execute(
        select(PasswordResetCode)
        .where(
            and_(
                PasswordResetCode.user_id == user.id,
                PasswordResetCode.email == normalized_email,
                PasswordResetCode.code == request.code.strip(),
                PasswordResetCode.consumed_at.is_(None),
            )
        )
        .order_by(PasswordResetCode.created_at.desc())
    )
    reset_code = code_result.scalars().first()
    now = datetime.now(timezone.utc)

    if not reset_code or reset_code.expires_at < now:
        raise HTTPException(status_code=400, detail="验证码无效或已过期")

    user.hashed_password = hash_password(request.new_password)
    reset_code.consumed_at = now

    active_codes_result = await db.execute(
        select(PasswordResetCode).where(
            and_(
                PasswordResetCode.user_id == user.id,
                PasswordResetCode.consumed_at.is_(None),
            )
        )
    )
    for active_code in active_codes_result.scalars():
        active_code.consumed_at = now

    await db.commit()
    return {"message": "密码已重置，请使用新密码登录。"}


@router.get(
    "/auth/me",
    summary="当前用户",
    description="获取当前登录用户的信息。 Get the currently authenticated user's profile.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await build_user_profile(current_user, db)


@router.get(
    "/auth/session",
    summary="校验 JWT 会话",
    description="校验当前 JWT 是否有效，并返回当前用户信息。 Validate the active JWT session and return the current user profile.",
)
async def verify_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await build_user_profile(current_user, db)
    return {"token_valid": True, "user": profile}
