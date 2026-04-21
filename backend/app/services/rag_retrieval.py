from __future__ import annotations

import re
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models import DocumentChunk
from app.services.document_permissions import get_accessible_document_ids
from app.services.qdrant_vector_store import QdrantUnavailableError, search_document_chunks
from app.services.serializers import serialize_document


settings = get_settings()
_keyword_pattern = re.compile(r"[\u4e00-\u9fff]{1,2}|[a-zA-Z0-9_]+", re.UNICODE)


def _extract_keywords(text: str) -> list[str]:
    return [token.lower() for token in _keyword_pattern.findall(text.lower()) if token.strip()]


def _keyword_score(query: str, content: str) -> float:
    query_keywords = set(_extract_keywords(query))
    if not query_keywords:
        return 0.0

    content_lower = content.lower()
    matched = sum(1 for token in query_keywords if token in content_lower)
    score = matched / max(len(query_keywords), 1)
    if query.strip().lower() in content_lower:
        score += settings.retrieval_exact_match_bonus
    return min(score, 1.0)


def _build_lexical_candidates(db, accessible_document_ids: list[int], query: str, limit: int) -> list[DocumentChunk]:
    keywords = _extract_keywords(query)[:6]
    if not keywords or not accessible_document_ids:
        return []

    clauses = [DocumentChunk.content.ilike(f"%{keyword}%") for keyword in keywords]
    if not clauses:
        return []

    return (
        db.scalars(
            select(DocumentChunk)
            .options(selectinload(DocumentChunk.document))
            .where(DocumentChunk.document_id.in_(accessible_document_ids))
            .where(or_(*clauses))
            .order_by(DocumentChunk.updated_at.desc(), DocumentChunk.id.desc())
            .limit(limit)
        )
        .unique()
        .all()
    )


def retrieve_document_chunks(
    db,
    current_user,
    *,
    query: str,
    limit: int,
    document_id: int | None = None,
    document_ids: list[int] | None = None,
    space_id: int | None = None,
    space_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    accessible_document_ids = get_accessible_document_ids(
        db,
        current_user,
        document_id=document_id,
        document_ids=document_ids,
        space_id=space_id,
        space_ids=space_ids,
    )
    if not accessible_document_ids:
        return []

    candidate_limit = max(limit, settings.retrieval_candidate_limit)
    chunk_payload_map: dict[int, dict[str, Any]] = {}
    qdrant_hits: list[dict[str, Any]] = []

    try:
        qdrant_hits = search_document_chunks(
            query,
            limit=candidate_limit,
            document_ids=accessible_document_ids,
        )
    except QdrantUnavailableError:
        qdrant_hits = []

    chunk_ids = [int(item["chunkId"]) for item in qdrant_hits if item.get("chunkId") is not None]
    chunks = []
    if chunk_ids:
        chunks = (
            db.scalars(
                select(DocumentChunk)
                .options(selectinload(DocumentChunk.document))
                .where(DocumentChunk.id.in_(chunk_ids))
            )
            .unique()
            .all()
        )

    chunk_map = {chunk.id: chunk for chunk in chunks}

    for hit in qdrant_hits:
        chunk_id = int(hit["chunkId"])
        chunk = chunk_map.get(chunk_id)
        content = chunk.content if chunk else str(hit.get("content") or "")
        vector_score = float(hit.get("score") or 0.0)
        keyword_score = _keyword_score(query, content)
        final_score = max(
            0.0,
            min(1.0, vector_score * (1 - settings.retrieval_keyword_weight) + keyword_score * settings.retrieval_keyword_weight),
        )
        chunk_payload_map[chunk_id] = {
            "score": final_score,
            "vectorScore": vector_score,
            "keywordScore": keyword_score,
            "chunkId": chunk_id,
            "documentId": int(hit["documentId"]),
            "chunkIndex": int(hit["chunkIndex"]),
            "content": content,
            "document": serialize_document(chunk.document, include_file=False, include_space=True) if chunk and chunk.document else None,
        }

    for chunk in _build_lexical_candidates(db, accessible_document_ids, query, candidate_limit):
        keyword_score = _keyword_score(query, chunk.content)
        existing = chunk_payload_map.get(chunk.id)
        if existing:
            existing["keywordScore"] = max(existing["keywordScore"], keyword_score)
            existing["score"] = max(
                existing["score"],
                min(
                    1.0,
                    existing["vectorScore"] * (1 - settings.retrieval_keyword_weight)
                    + max(existing["keywordScore"], keyword_score) * settings.retrieval_keyword_weight,
                ),
            )
            continue

        chunk_payload_map[chunk.id] = {
            "score": min(0.95, 0.45 + keyword_score / 2),
            "vectorScore": 0.0,
            "keywordScore": keyword_score,
            "chunkId": chunk.id,
            "documentId": chunk.document_id,
            "chunkIndex": chunk.chunk_index,
            "content": chunk.content,
            "document": serialize_document(chunk.document, include_file=False, include_space=True) if chunk.document else None,
        }

    results = list(chunk_payload_map.values())
    results.sort(
        key=lambda item: (
            -item["score"],
            -item["keywordScore"],
            -item["vectorScore"],
            item["chunkIndex"],
        )
    )
    return results[:limit]
