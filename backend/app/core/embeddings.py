from openai import OpenAI
import os
from typing import Iterable
from app.core.paths import ensure_env_loaded

ensure_env_loaded()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", 10))

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)


def _chunked(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index:index + size]


def embed_text(text: str) -> list[float]:
    """将单段文本转为向量，拒绝空白输入。"""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("文档内容为空，无法生成向量")

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text.strip(),
    )
    return response.data[0].embedding


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量将文本转为向量，并过滤空白文本。"""
    cleaned_texts = [text.strip() for text in texts if isinstance(text, str) and text.strip()]
    if not cleaned_texts:
        raise ValueError("没有可用于向量化的文档内容")

    if EMBEDDING_BATCH_SIZE <= 0:
        raise ValueError("EMBEDDING_BATCH_SIZE 必须大于 0")

    embeddings: list[list[float]] = []
    for batch in _chunked(cleaned_texts, EMBEDDING_BATCH_SIZE):
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        embeddings.extend(item.embedding for item in response.data)

    return embeddings
