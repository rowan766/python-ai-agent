from qdrant_client import QdrantClient
from qdrant_client.http import models
import os
import logging
from app.core.embeddings import embed_text
from typing import Any
from app.core.paths import ensure_env_loaded

ensure_env_loaded()

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


def _payload_matches(
    payload: dict[str, Any],
    accessible_department_ids: list[int] | None = None,
    knowledge_base_ids: list[int] | None = None,
) -> bool:
    if accessible_department_ids is not None:
        department_id = payload.get("department_id")
        if department_id not in accessible_department_ids:
            return False

    if knowledge_base_ids is not None:
        knowledge_base_id = payload.get("knowledge_base_id")
        if knowledge_base_id not in knowledge_base_ids:
            return False

    if payload.get("status") not in {None, "active"}:
        return False

    return True


def _build_query_filter(
    accessible_department_ids: list[int] | None = None,
    knowledge_base_ids: list[int] | None = None,
):
    must_conditions: list[models.FieldCondition] = [
        models.FieldCondition(key="status", match=models.MatchValue(value="active"))
    ]

    if accessible_department_ids is not None:
        must_conditions.append(
            models.FieldCondition(
                key="department_id",
                match=models.MatchAny(any=accessible_department_ids),
            )
        )

    if knowledge_base_ids is not None:
        must_conditions.append(
            models.FieldCondition(
                key="knowledge_base_id",
                match=models.MatchAny(any=knowledge_base_ids),
            )
        )

    return models.Filter(must=must_conditions)


def _keyword_fallback(
    query: str,
    limit: int = 5,
    accessible_department_ids: list[int] | None = None,
    knowledge_base_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
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
            if not _payload_matches(
                payload=payload,
                accessible_department_ids=accessible_department_ids,
                knowledge_base_ids=knowledge_base_ids,
            ):
                continue
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


def retrieve_documents(
    query: str,
    limit: int = 5,
    score_threshold: float | None = None,
    accessible_department_ids: list[int] | None = None,
    knowledge_base_ids: list[int] | None = None,
):
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
            query_filter=_build_query_filter(
                accessible_department_ids=accessible_department_ids,
                knowledge_base_ids=knowledge_base_ids,
            ),
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

    return _keyword_fallback(
        query=query,
        limit=limit,
        accessible_department_ids=accessible_department_ids,
        knowledge_base_ids=knowledge_base_ids,
    )
