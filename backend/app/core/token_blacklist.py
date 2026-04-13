"""Token 黑名单管理模块"""
import logging
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.redis_client import get_redis_client
from app.core.security import decode_access_token


settings = get_settings()
logger = logging.getLogger("app.token_blacklist")


def _get_blacklist_key(token: str) -> str:
    """获取 token 黑名单的 Redis key"""
    return f"{settings.redis_key_prefix}:blacklist:token:{token}"


def add_token_to_blacklist(token: str) -> bool:
    """
    将 token 添加到黑名单

    Args:
        token: JWT token

    Returns:
        是否添加成功
    """
    try:
        redis_client = get_redis_client()
        payload = decode_access_token(token)

        if not payload:
            logger.warning("无法解析 token，跳过加入黑名单")
            return False

        # 计算 token 剩余有效期
        exp = payload.get("exp")
        if not exp:
            logger.warning("token 没有过期时间，使用默认 TTL")
            ttl = settings.access_token_ttl_seconds
        else:
            now = datetime.now(timezone.utc).timestamp()
            ttl = max(int(exp - now), 60)  # 至少保留 60 秒

        # 将 token 加入黑名单，设置过期时间
        key = _get_blacklist_key(token)
        redis_client.setex(key, ttl, "1")
        logger.info("token 已加入黑名单，TTL=%d 秒", ttl)
        return True

    except Exception as e:
        logger.error("添加 token 到黑名单失败: %s", e, exc_info=True)
        return False


def is_token_blacklisted(token: str) -> bool:
    """
    检查 token 是否在黑名单中

    Args:
        token: JWT token

    Returns:
        是否在黑名单中
    """
    try:
        redis_client = get_redis_client()
        key = _get_blacklist_key(token)
        return redis_client.exists(key) > 0
    except Exception as e:
        logger.error("检查 token 黑名单失败: %s", e, exc_info=True)
        # 出错时保守处理，不阻止用户访问
        return False


def remove_token_from_blacklist(token: str) -> bool:
    """
    从黑名单中移除 token（用于测试或特殊场景）

    Args:
        token: JWT token

    Returns:
        是否移除成功
    """
    try:
        redis_client = get_redis_client()
        key = _get_blacklist_key(token)
        result = redis_client.delete(key)
        return result > 0
    except Exception as e:
        logger.error("从黑名单移除 token 失败: %s", e, exc_info=True)
        return False
