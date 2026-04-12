import hashlib
import math
import re

from app.core.config import get_settings


settings = get_settings()
_token_pattern = re.compile(r"[\u4e00-\u9fff]|[a-zA-Z0-9_]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    tokens = _token_pattern.findall(text.lower())
    if not tokens:
        compact = re.sub(r"\s+", "", text.lower())
        return [compact[index : index + 2] for index in range(max(len(compact) - 1, 1)) if compact]
    return tokens


def _hash_index(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % settings.embedding_vector_size


def embed_text(text: str) -> list[float]:
    vector = [0.0] * settings.embedding_vector_size
    tokens = _tokenize(text)
    if not tokens:
        return vector

    for token in tokens:
        index = _hash_index(token)
        sign = 1.0 if (ord(token[0]) % 2 == 0) else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def embed_texts(texts: list[str]) -> list[list[float]]:
    return [embed_text(text) for text in texts]
