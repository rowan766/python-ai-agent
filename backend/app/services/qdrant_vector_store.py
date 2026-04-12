from functools import lru_cache
import logging

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from app.core.config import get_settings
from app.models import DocumentChunk
from app.services.embedding import embed_passages, embed_query


settings = get_settings()
logger = logging.getLogger("app.qdrant")


class QdrantUnavailableError(RuntimeError):
    pass


def _build_qdrant_error(exc: Exception) -> QdrantUnavailableError:
    return QdrantUnavailableError(f"Qdrant 服务不可用，请确认 {settings.qdrant_url} 已正常启动")


@lru_cache
def get_qdrant_client() -> QdrantClient:
    if settings.qdrant_url == ":memory:":
        return QdrantClient(location=":memory:")
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def ensure_qdrant_collection() -> bool:
    try:
        client = get_qdrant_client()
        collections = client.get_collections().collections
        existing_names = {collection.name for collection in collections}
        if settings.qdrant_collection_name in existing_names:
            return True
        client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=rest.VectorParams(
                size=settings.embedding_vector_size,
                distance=rest.Distance.COSINE,
            ),
        )
        return True
    except Exception as exc:
        raise _build_qdrant_error(exc) from exc


def delete_document_vectors(document_id: int) -> None:
    try:
        get_qdrant_client().delete(
            collection_name=settings.qdrant_collection_name,
            points_selector=rest.FilterSelector(
                filter=rest.Filter(
                    must=[
                        rest.FieldCondition(
                            key="documentId",
                            match=rest.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )
    except Exception as exc:
        logger.warning("删除文档向量失败，已跳过。document_id=%s, error=%s", document_id, exc)


def upsert_document_chunks(document_id: int, chunks: list[DocumentChunk]) -> int:
    if not chunks:
        delete_document_vectors(document_id)
        return 0

    vectors = embed_passages([chunk.content for chunk in chunks])
    points = []
    for chunk, vector in zip(chunks, vectors, strict=False):
        points.append(
            rest.PointStruct(
                id=chunk.id,
                vector=vector,
                payload={
                    "documentId": chunk.document_id,
                    "chunkId": chunk.id,
                    "chunkIndex": chunk.chunk_index,
                    "content": chunk.content,
                    "contentLength": chunk.content_length,
                    "charStart": chunk.char_start,
                    "charEnd": chunk.char_end,
                },
            )
        )

    try:
        client = get_qdrant_client()
        client.upsert(
            collection_name=settings.qdrant_collection_name,
            points=points,
            wait=True,
        )
        return len(points)
    except Exception as exc:
        raise _build_qdrant_error(exc) from exc


def search_document_chunks(query: str, limit: int = 5, document_ids: list[int] | None = None) -> list[dict]:
    try:
        query_vector = embed_query(query)
        query_filter = None
        if document_ids:
            query_filter = rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="documentId",
                        match=rest.MatchAny(any=document_ids),
                    )
                ]
            )
        response = get_qdrant_client().query_points(
            collection_name=settings.qdrant_collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        payloads: list[dict] = []
        for item in response.points:
            payload = dict(item.payload or {})
            payload["score"] = float(item.score)
            payloads.append(payload)
        return payloads
    except Exception as exc:
        raise _build_qdrant_error(exc) from exc
