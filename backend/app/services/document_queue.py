from app.core.config import get_settings
from app.core.redis_client import get_redis_client


settings = get_settings()
redis_client = get_redis_client()
DOCUMENT_QUEUE_NAME = "document-processing"


def get_document_queue_key(queue_name: str = DOCUMENT_QUEUE_NAME) -> str:
    return f"{settings.redis_key_prefix}:queue:{queue_name}"


def enqueue_document_task(task_id: int, queue_name: str = DOCUMENT_QUEUE_NAME) -> None:
    redis_client.rpush(get_document_queue_key(queue_name), task_id)


def get_document_queue_length(queue_name: str = DOCUMENT_QUEUE_NAME) -> int:
    return int(redis_client.llen(get_document_queue_key(queue_name)))


def pop_document_task(*, queue_name: str = DOCUMENT_QUEUE_NAME, block: bool = False, timeout: int = 3) -> int | None:
    queue_key = get_document_queue_key(queue_name)
    if block:
        item = redis_client.blpop(queue_key, timeout=timeout)
        if not item:
            return None
        _, value = item
    else:
        value = redis_client.lpop(queue_key)

    if value is None:
        return None
    return int(value)
