from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.captcha import generate_captcha, verify_captcha
from app.core.deps import DbSession
from app.core.http import success_response
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas import LoginRequest
from app.services.serializers import serialize_user


router = APIRouter(prefix="/auth", tags=["认证管理"])


@router.get("/captcha", summary="获取验证码")
def get_captcha() -> dict:
    captcha_id, captcha_svg = generate_captcha()
    return success_response({"captchaId": captcha_id, "captchaSvg": captcha_svg})


@router.post("/login", summary="用户登录")
def login(payload: LoginRequest, db: DbSession) -> dict:
    if not verify_captcha(payload.captchaId, payload.captchaCode):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名或密码错误")
    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号已被禁用")

    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return success_response(
        {
            "access_token": create_access_token(user.id),
            "token_type": "bearer",
            "user": serialize_user(user),
        },
        message="登录成功",
    )


@router.post("/logout", summary="退出登录")
def logout() -> dict:
    return success_response(message="退出成功")
