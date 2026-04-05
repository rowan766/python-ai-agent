from qdrant_client import QdrantClient
from dotenv import load_dotenv
import os
import logging
from pathlib import Path
from app.core.embeddings import embed_text
from typing import Any

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env")

client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)

COLLECTION_NAME = "knowledge_base"
DEFAULT_SCORE_THRESHOLD = float(os.getenv("RAG_SCORE_THRESHOLD", 0.3))
logger = logging.getLogger("uvicorn.error")


def _format_results(points) -> list[dict[str, Any]]:
    documents = []
    for scored_point in points:
        payload = scored_point.payload or {}
        documents.append({
            "content": payload.get("page_content", ""),
            "score": scored_point.score,
            "metadata": payload.get("metadata", {}),
        })
    return documents


def _keyword_fallback(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    当向量检索因为阈值或短查询词导致无结果时，
    使用简单的关键词匹配兜底，提升文档调试体验。
    """
    query_text = query.strip().lower()
    if not query_text:
        return []

    query_terms = [term for term in query_text.split() if term]
    offset = None
    matched_documents: list[dict[str, Any]] = []

    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            with_payload=True,
            with_vectors=False,
            limit=100,
            offset=offset,
        )

        for point in points:
            payload = point.payload or {}
            content = payload.get("page_content", "")
            if not isinstance(content, str) or not content.strip():
                continue

            lowered_content = content.lower()
            phrase_hits = lowered_content.count(query_text)
            term_hits = sum(lowered_content.count(term) for term in query_terms)
            if phrase_hits == 0 and term_hits == 0:
                continue

            score = phrase_hits * 10 + term_hits
            matched_documents.append({
                "content": content,
                "score": float(score),
                "metadata": {
                    **payload.get("metadata", {}),
                    "retrieval_mode": "keyword_fallback",
                },
            })

        if offset is None:
            break

    matched_documents.sort(key=lambda item: item["score"], reverse=True)
    return matched_documents[:limit]


def retrieve_documents(query: str, limit: int = 5, score_threshold: float | None = None):
    """
    根据用户查询进行向量检索，返回最相关的文档片段
    """
    try:
        # 把查询文本转为向量
        query_vector = embed_text(query)

        # 执行相似度搜索
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=max(limit, 10),
            with_payload=True,
        )

        threshold = DEFAULT_SCORE_THRESHOLD if score_threshold is None else score_threshold
        filtered_points = [
            point for point in response.points
            if threshold is None or point.score >= threshold
        ]
        if filtered_points:
            return _format_results(filtered_points[:limit])
    except Exception as exc:
        logger.warning("向量检索失败，已降级为关键词检索: %s", exc)

    return _keyword_fallback(query=query, limit=limit)
