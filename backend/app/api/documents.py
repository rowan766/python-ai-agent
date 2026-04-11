from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.core.http import paginated_response, success_response
from app.models import Document, DocumentChunk, DocumentTask
from app.schemas import DocumentReprocessRequest
from app.services.document_queue import DOCUMENT_QUEUE_NAME, enqueue_document_task, get_document_queue_length
from app.services.serializers import serialize_document, serialize_document_chunk, serialize_document_task


router = APIRouter(prefix="/document", tags=["文档处理"])


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


@router.get("", summary="获取文档列表")
def get_document_list(
    db: DbSession,
    _current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=1000),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = None,
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


@router.get("/tasks", summary="获取文档任务列表")
def get_document_task_list(
    db: DbSession,
    _current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=1000),
    status_filter: str | None = Query(default=None, alias="status"),
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


@router.get("/queue/status", summary="获取文档队列状态")
def get_document_queue_status(_current_user: CurrentUser) -> dict:
    return success_response(
        {
            "queueName": DOCUMENT_QUEUE_NAME,
            "processingMode": "worker",
            "pendingCount": get_document_queue_length(DOCUMENT_QUEUE_NAME),
        }
    )


@router.get("/{document_id}", summary="获取文档详情")
def get_document_detail(document_id: int, db: DbSession, _current_user: CurrentUser) -> dict:
    return success_response(serialize_document(_get_document_or_404(db, document_id), include_tasks=True))


@router.get("/{document_id}/chunks", summary="获取文档切片列表")
def get_document_chunks(
    document_id: int,
    db: DbSession,
    _current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=1000),
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


@router.post("/{document_id}/reprocess", summary="重新处理文档")
def reprocess_document(
    document_id: int,
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
        message="文档已重新入队，等待 Worker 处理",
    )
