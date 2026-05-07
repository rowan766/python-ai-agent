import asyncio
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.core.token_blacklist import is_token_blacklisted

router = APIRouter(tags=["WebSocket"])
settings = get_settings()
logger = logging.getLogger("app.ws")


class _DocumentEventManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.debug("WS connected, total=%d", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        logger.debug("WS disconnected, total=%d", len(self._connections))

    async def broadcast(self, message: str) -> None:
        dead: set[WebSocket] = set()
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self._connections -= dead


document_event_manager = _DocumentEventManager()


async def start_redis_subscriber() -> None:
    """后台协程：订阅 Redis Pub/Sub 并将事件广播给所有 WebSocket 客户端。"""
    channel = f"{settings.redis_key_prefix}:events:document"
    while True:
        try:
            async with aioredis.from_url(settings.redis_url, decode_responses=True) as r:
                async with r.pubsub() as pubsub:
                    await pubsub.subscribe(channel)
                    logger.info("Redis Pub/Sub 已订阅频道: %s", channel)
                    async for message in pubsub.listen():
                        if message["type"] == "message":
                            await document_event_manager.broadcast(message["data"])
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Redis subscriber 异常，3 秒后重连: %s", exc)
            await asyncio.sleep(3)


@router.websocket("/ws/documents")
async def websocket_documents(
    websocket: WebSocket,
    token: str = Query(..., description="登录 access_token"),
) -> None:
    if is_token_blacklisted(token) or not decode_access_token(token):
        await websocket.close(code=4001, reason="未授权")
        return

    await document_event_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        document_event_manager.disconnect(websocket)
