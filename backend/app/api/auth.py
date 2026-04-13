from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.audit import AuditAction, log_audit
from app.core.captcha import generate_captcha, verify_captcha
from app.core.deps import CurrentUser, DbSession
from app.core.http import success_response
from app.core.security import create_access_token, verify_password
from app.core.token_blacklist import add_token_to_blacklist
from app.models import User
from app.schemas import ApiResponse, CaptchaData, LoginData, LoginRequest
from app.services.serializers import serialize_user


router = APIRouter(prefix="/auth", tags=["认证管理"])
bearer_scheme = HTTPBearer(auto_error=False)


@router.get(
    "/captcha",
    summary="获取验证码",
    response_model=ApiResponse[CaptchaData],
    openapi_extra={"security": []},
)
def get_captcha() -> dict:
    captcha_id, captcha_svg = generate_captcha()
    return success_response(
        {
            "captchaId": captcha_id,
            "captchaSvg": captcha_svg,
        }
    )


@router.post(
    "/login",
    summary="用户登录",
    response_model=ApiResponse[LoginData],
    openapi_extra={"security": []},
)
def login(payload: LoginRequest, db: DbSession, request: Request) -> dict:
    if not verify_captcha(payload.captchaId, payload.captchaCode):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    user = db.scalar(select(User).where(User.username == payload.username))

    # 获取客户端 IP
    client_ip = request.client.host if request.client else None

    if not user or not verify_password(payload.password, user.password):
        # 记录登录失败
        log_audit(
            action=AuditAction.LOGIN_FAILED,
            username=payload.username,
            ip_address=client_ip,
            success=False,
            details={"reason": "用户名或密码错误"},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名或密码错误")

    if user.status != 1:
        # 记录登录失败
        log_audit(
            action=AuditAction.LOGIN_FAILED,
            user_id=user.id,
            username=user.username,
            ip_address=client_ip,
            success=False,
            details={"reason": "账号已被禁用"},
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号已被禁用")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    # 记录登录成功
    log_audit(
        action=AuditAction.LOGIN,
        user_id=user.id,
        username=user.username,
        ip_address=client_ip,
        success=True,
    )

    return success_response(
        {
            "access_token": create_access_token(user.id),
            "token_type": "bearer",
            "user": serialize_user(user),
        },
        message="登录成功",
    )


@router.post(
    "/logout",
    summary="退出登录",
    response_model=ApiResponse[None],
)
def logout(
    current_user: CurrentUser,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = None,
) -> dict:
    # 获取客户端 IP
    client_ip = request.client.host if request.client else None

    # 尝试将 token 加入黑名单
    if credentials and credentials.credentials:
        token = credentials.credentials.strip()
        add_token_to_blacklist(token)

    # 记录登出
    log_audit(
        action=AuditAction.LOGOUT,
        user_id=current_user.id,
        username=current_user.username,
        ip_address=client_ip,
        success=True,
    )

    return success_response(message="退出成功")
