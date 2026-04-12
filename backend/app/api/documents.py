from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.core.http import paginated_response, success_response
from app.models import Document, DocumentChunk, DocumentTask
from app.schemas import (
    ApiResponse,
    DocumentChunkItem,
    DocumentItem,
    DocumentQueueStatusData,
    DocumentReprocessRequest,
    DocumentSearchHit,
    DocumentTaskItem,
    PageData,
    ReprocessDocumentData,
)
from app.services.document_queue import DOCUMENT_QUEUE_NAME, enqueue_document_task, get_document_queue_length
from app.services.qdrant_vector_store import QdrantUnavailableError, search_document_chunks
from app.services.serializers import serialize_document, serialize_document_chunk, serialize_document_task
from app.core.config import get_settings


router = APIRouter(prefix="/document", tags=["文档处理"])
settings = get_settings()


def _document_query():
    return (
        select(Document)
        .options(selectinload(Document.file_record))
        .options(selectinload(Document.tasks))
        .options(selectinload(Document.chunks))
    )


def _get_document_or_404(db: DbSession, document_id: int) -> Document:
    document = db.scalar(_document_query().where(Document.id == document_id))
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    return document


@router.get(
    "",
    summary="获取文档列表",
    response_model=ApiResponse[PageData[DocumentItem]],
)
def get_document_list(
    db: DbSession,
    _current_user: CurrentUser,
    page: int = Query(default=1, ge=1, title="页码", description="分页页码，从 1 开始"),
    pageSize: int = Query(default=10, ge=1, le=1000, title="每页条数", description="每页返回的文档数量"),
    status_filter: str | None = Query(default=None, alias="status", title="文档状态", description="按文档处理状态筛选"),
    keyword: str | None = Query(default=None, title="关键词", description="按文档标题模糊搜索"),
) -> dict:
    filters = []
    if status_filter:
        filters.append(Document.status == status_filter)
    if keyword:
        keyword_value = f"%{keyword.strip()}%"
        filters.append(Document.title.ilike(keyword_value))

    total = db.scalar(select(func.count()).select_from(Document).where(*filters)) or 0
    documents = db.scalars(
        _document_query()
        .where(*filters)
        .order_by(Document.id.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()
    return paginated_response([serialize_document(item) for item in documents], total, page, pageSize)


@router.get(
    "/tasks",
    summary="获取文档任务列表",
    response_model=ApiResponse[PageData[DocumentTaskItem]],
)
def get_document_task_list(
    db: DbSession,
    _current_user: CurrentUser,
    page: int = Query(default=1, ge=1, title="页码", description="分页页码，从 1 开始"),
    pageSize: int = Query(default=10, ge=1, le=1000, title="每页条数", description="每页返回的任务数量"),
    status_filter: str | None = Query(default=None, alias="status", title="任务状态", description="按任务处理状态筛选"),
) -> dict:
    filters = []
    if status_filter:
        filters.append(DocumentTask.status == status_filter)

    total = db.scalar(select(func.count()).select_from(DocumentTask).where(*filters)) or 0
    tasks = db.scalars(
        select(DocumentTask)
        .where(*filters)
        .order_by(DocumentTask.id.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()
    return paginated_response([serialize_document_task(item) for item in tasks], total, page, pageSize)


@router.get(
    "/queue/status",
    summary="获取文档队列状态",
    response_model=ApiResponse[DocumentQueueStatusData],
)
def get_document_queue_status(db: DbSession, _current_user: CurrentUser) -> dict:
    processing_count = (
        db.scalar(select(func.count()).select_from(DocumentTask).where(DocumentTask.status == "processing"))
        or 0
    )
    return success_response(
        {
            "queueName": DOCUMENT_QUEUE_NAME,
            "processingMode": settings.document_processing_mode,
            "pendingCount": get_document_queue_length(DOCUMENT_QUEUE_NAME),
            "processingCount": processing_count,
        }
    )


@router.get(
    "/search",
    summary="搜索文档切片",
    response_model=ApiResponse[list[DocumentSearchHit]],
)
def search_documents(
    query: Annotated[str, Query(title="检索关键词", description="用于向量检索文档切片的查询关键词")],
    db: DbSession,
    _current_user: CurrentUser,
    limit: int = Query(default=5, ge=1, le=20, title="返回条数", description="最多返回的检索结果数量"),
) -> dict:
    keyword = query.strip()
    if not keyword:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="检索关键词不能为空")

    try:
        hits = search_document_chunks(keyword, limit=limit)
    except QdrantUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not hits:
        return success_response([])

    chunk_ids = [int(item["chunkId"]) for item in hits if item.get("chunkId") is not None]
    chunks = db.scalars(
        select(DocumentChunk)
        .options(selectinload(DocumentChunk.document))
        .where(DocumentChunk.id.in_(chunk_ids))
    ).all()
    chunk_map = {chunk.id: chunk for chunk in chunks}

    results: list[dict] = []
    for hit in hits:
        chunk_id = int(hit["chunkId"])
        chunk = chunk_map.get(chunk_id)
        results.append(
            {
                "score": hit["score"],
                "chunkId": chunk_id,
                "documentId": hit["documentId"],
                "chunkIndex": hit["chunkIndex"],
                "content": hit["content"],
                "document": serialize_document(chunk.document, include_file=False) if chunk and chunk.document else None,
            }
        )
    return success_response(results)


@router.get(
    "/{document_id}",
    summary="获取文档详情",
    response_model=ApiResponse[DocumentItem],
)
def get_document_detail(
    document_id: Annotated[int, Path(title="文档 ID", description="要查询的文档主键 ID")],
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    return success_response(serialize_document(_get_document_or_404(db, document_id), include_tasks=True))


@router.get(
    "/{document_id}/chunks",
    summary="获取文档切片列表",
    response_model=ApiResponse[PageData[DocumentChunkItem]],
)
def get_document_chunks(
    document_id: Annotated[int, Path(title="文档 ID", description="要查询切片列表的文档主键 ID")],
    db: DbSession,
    _current_user: CurrentUser,
    page: int = Query(default=1, ge=1, title="页码", description="分页页码，从 1 开始"),
    pageSize: int = Query(default=10, ge=1, le=1000, title="每页条数", description="每页返回的切片数量"),
) -> dict:
    _get_document_or_404(db, document_id)
    total = db.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document_id)) or 0
    chunks = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()
    return paginated_response([serialize_document_chunk(item) for item in chunks], total, page, pageSize)


@router.post(
    "/{document_id}/reprocess",
    summary="重新处理文档",
    response_model=ApiResponse[ReprocessDocumentData],
)
def reprocess_document(
    document_id: Annotated[int, Path(title="文档 ID", description="要重新处理的文档主键 ID")],
    payload: DocumentReprocessRequest,
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    document = _get_document_or_404(db, document_id)
    latest_task = db.scalar(
        select(DocumentTask)
        .where(DocumentTask.document_id == document_id)
        .order_by(DocumentTask.id.desc())
        .limit(1)
    )
    if latest_task and latest_task.status in {"pending", "processing"} and not payload.force:
        return success_response(
            {
                "document": serialize_document(document, include_tasks=True),
                "task": serialize_document_task(latest_task),
            },
            message="当前文档已有处理中任务",
        )

    task = DocumentTask(
        document_id=document.id,
        task_type="reprocess",
        queue_name=DOCUMENT_QUEUE_NAME,
        status="pending",
    )
    document.status = "pending"
    document.error_message = None
    db.add(task)
    db.commit()
    db.refresh(task)
    enqueue_document_task(task.id, task.queue_name)

    refreshed = _get_document_or_404(db, document.id)
    return success_response(
        {
            "document": serialize_document(refreshed, include_tasks=True),
            "task": serialize_document_task(task),
        },
        message="文档已重新入队，系统会自动继续处理",
    )
