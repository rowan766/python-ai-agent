"""审计日志模块"""
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.core.config import get_settings
from app.core.redis_client import get_redis_client


settings = get_settings()
logger = logging.getLogger("app.audit")


class AuditAction(str, Enum):
    """审计操作类型"""

    # 认证相关
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"

    # 文档相关
    DOCUMENT_CREATE = "document_create"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_UPDATE = "document_update"
    DOCUMENT_DOWNLOAD = "document_download"

    # 用户相关
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_PASSWORD_CHANGE = "user_password_change"

    # 角色权限相关
    ROLE_CREATE = "role_create"
    ROLE_UPDATE = "role_update"
    ROLE_DELETE = "role_delete"
    ROLE_ASSIGN = "role_assign"


def log_audit(
    action: AuditAction,
    user_id: int | None = None,
    username: str | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    success: bool = True,
) -> None:
    """
    记录审计日志

    Args:
        action: 操作类型
        user_id: 用户 ID
        username: 用户名
        resource_type: 资源类型（如 document, user, role）
        resource_id: 资源 ID
        details: 详细信息
        ip_address: IP 地址
        success: 操作是否成功
    """
    try:
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action.value,
            "user_id": user_id,
            "username": username,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "success": success,
        }

        # 记录到日志文件
        logger.info(
            "审计日志: action=%s, user_id=%s, username=%s, resource=%s:%s, success=%s",
            action.value,
            user_id,
            username,
            resource_type,
            resource_id,
            success,
            extra={"audit": audit_entry},
        )

        # 可选：将审计日志存储到 Redis 或数据库
        # 这里使用 Redis List 存储最近的审计日志
        try:
            redis_client = get_redis_client()
            key = f"{settings.redis_key_prefix}:audit:logs"
            redis_client.lpush(key, json.dumps(audit_entry, ensure_ascii=False))
            # 只保留最近 10000 条审计日志
            redis_client.ltrim(key, 0, 9999)
        except Exception as e:
            logger.warning("存储审计日志到 Redis 失败: %s", e)

    except Exception as e:
        logger.error("记录审计日志失败: %s", e, exc_info=True)


def get_recent_audit_logs(limit: int = 100) -> list[dict[str, Any]]:
    """
    获取最近的审计日志

    Args:
        limit: 返回的日志条数

    Returns:
        审计日志列表
    """
    try:
        redis_client = get_redis_client()
        key = f"{settings.redis_key_prefix}:audit:logs"
        logs = redis_client.lrange(key, 0, limit - 1)
        return [json.loads(log) for log in logs]
    except Exception as e:
        logger.error("获取审计日志失败: %s", e, exc_info=True)
        return []
