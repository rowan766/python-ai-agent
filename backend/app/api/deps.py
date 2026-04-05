import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import decode_token
from app.core.database import get_db
from app.core.paths import ensure_env_loaded
from app.models.user import User

ensure_env_loaded()

security = HTTPBearer()


def get_platform_admin_emails() -> set[str]:
    raw_value = os.getenv("PLATFORM_ADMIN_EMAILS", "")
    return {item.strip().lower() for item in raw_value.split(",") if item.strip()}


def is_platform_admin(user: User) -> bool:
    return user.email.lower() in get_platform_admin_emails()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")

    return user
