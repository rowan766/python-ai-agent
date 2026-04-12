from __future__ import annotations

import hashlib
import logging
import math
import re
import warnings
from functools import lru_cache
from typing import Iterable

from app.core.config import get_settings


settings = get_settings()
logger = logging.getLogger("app.embedding")
_token_pattern = re.compile(r"[\u4e00-\u9fff]|[a-zA-Z0-9_]+", re.UNICODE)
_dimension_warning_emitted = False
_fallback_warning_emitted = False


def _tokenize(text: str) -> list[str]:
    tokens = _token_pattern.findall(text.lower())
    if not tokens:
        compact = re.sub(r"\s+", "", text.lower())
        return [compact[index : index + 2] for index in range(max(len(compact) - 1, 1)) if compact]
    return tokens


def _hash_index(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % settings.embedding_vector_size


def _normalize_vector(vector: Iterable[float]) -> list[float]:
    values = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [value / norm for value in values]


def _embed_with_hash(text: str) -> list[float]:
    vector = [0.0] * settings.embedding_vector_size
    tokens = _tokenize(text)
    if not tokens:
        return vector

    for token in tokens:
        index = _hash_index(token)
        sign = 1.0 if (ord(token[0]) % 2 == 0) else -1.0
        vector[index] += sign
    return _normalize_vector(vector)


def _prepare_text(text: str, *, is_query: bool) -> str:
    normalized = text.strip()
    model_name = settings.embedding_model_name.lower()
    if model_name.startswith("intfloat/multilingual-e5"):
        prefix = "query: " if is_query else "passage: "
        if not normalized.lower().startswith(prefix):
            return f"{prefix}{normalized}"
    return normalized


@lru_cache
def _get_fastembed_model():
    from fastembed import TextEmbedding

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=".*now uses mean pooling instead of CLS embedding.*",
            category=UserWarning,
        )
        return TextEmbedding(model_name=settings.embedding_model_name)


def _warn_fallback(exc: Exception) -> None:
    global _fallback_warning_emitted
    if _fallback_warning_emitted:
        return
    logger.warning("真实 embedding 模型加载失败，已回退到 hash 向量: %s", exc)
    _fallback_warning_emitted = True


def _embed_with_model(texts: list[str], *, is_query: bool) -> list[list[float]]:
    global _dimension_warning_emitted

    model = _get_fastembed_model()
    prepared_texts = [_prepare_text(text, is_query=is_query) for text in texts]

    if is_query and hasattr(model, "query_embed"):
        raw_vectors = list(model.query_embed(prepared_texts))
    elif not is_query and hasattr(model, "passage_embed"):
        raw_vectors = list(model.passage_embed(prepared_texts))
    else:
        raw_vectors = list(model.embed(prepared_texts, batch_size=settings.embedding_batch_size))

    vectors: list[list[float]] = []
    for raw_vector in raw_vectors:
        vector = raw_vector.tolist() if hasattr(raw_vector, "tolist") else list(raw_vector)
        if len(vector) != settings.embedding_vector_size and not _dimension_warning_emitted:
            logger.warning(
                "Embedding 模型维度与配置不一致: model=%s, actual=%s, expected=%s",
                settings.embedding_model_name,
                len(vector),
                settings.embedding_vector_size,
            )
            _dimension_warning_emitted = True
        vectors.append(_normalize_vector(vector))
    return vectors


def _embed_texts(texts: list[str], *, is_query: bool) -> list[list[float]]:
    provider = settings.embedding_provider.strip().lower()
    if provider == "fastembed":
        try:
            return _embed_with_model(texts, is_query=is_query)
        except Exception as exc:
            if not settings.embedding_fallback_to_hash:
                raise
            _warn_fallback(exc)

    return [_embed_with_hash(text) for text in texts]


def embed_query(text: str) -> list[float]:
    return _embed_texts([text], is_query=True)[0]


def embed_passages(texts: list[str]) -> list[list[float]]:
    return _embed_texts(texts, is_query=False)


def embed_text(text: str) -> list[float]:
    return embed_query(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    return embed_passages(texts)
