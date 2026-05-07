import json
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Request, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.audit import AuditAction, log_audit
from app.core.deps import CurrentUser, DbSession
from app.core.http import paginated_response, success_response
from app.models import Document, DocumentChunk, DocumentQaMessage, DocumentQaSession, DocumentTask
from app.schemas import (
    ApiResponse,
    DocumentChunkItem,
    DocumentItem,
    DocumentQaData,
    DocumentQaSessionCreateRequest,
    DocumentQaSessionItem,
    DocumentQaSessionSyncRequest,
    DocumentQaSessionUpdateRequest,
    DocumentQaRequest,
    DocumentQueueStatusData,
    DocumentReprocessRequest,
    DocumentSearchHit,
    DocumentTaskItem,
    PageData,
    ReprocessDocumentData,
)
from app.services.document_permissions import build_document_permission_clause
from app.services.document_queue import DOCUMENT_QUEUE_NAME, enqueue_document_task
from app.services.object_storage import remove_file_from_minio
from app.services.rag_answer import answer_question_from_hits
from app.services.rag_retrieval import retrieve_document_chunks
from app.services.serializers import (
    serialize_document,
    serialize_document_chunk,
    serialize_document_qa_session,
    serialize_document_task,
)
from app.core.config import get_settings
from app.services.qdrant_vector_store import delete_document_vectors


router = APIRouter(prefix="/document", tags=["文档处理"])
settings = get_settings()
logger = logging.getLogger("app.api.documents")


def _document_query():
    return (
        select(Document)
        .options(selectinload(Document.file_record))
        .options(selectinload(Document.space))
        .options(selectinload(Document.tasks))
        .options(selectinload(Document.chunks))
    )


def _document_qa_session_query():
    return select(DocumentQaSession).options(selectinload(DocumentQaSession.messages))


def _get_document_detail_or_404(db: DbSession, document_id: int, current_user, *, action: str = "read") -> Document:
    statement = _document_query().where(Document.id == document_id)
    permission_clause = build_document_permission_clause(db, current_user, action=action)
    if permission_clause is not None:
        statement = statement.where(permission_clause)
    document = db.scalar(statement)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    return document


def _get_document_qa_session_or_404(db: DbSession, session_id: int, current_user) -> DocumentQaSession:
    session = db.scalar(
        _document_qa_session_query().where(
            DocumentQaSession.id == session_id,
            DocumentQaSession.user_id == current_user.id,
        )
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return session


def _parse_message_timestamp(value: str | int | None) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _sanitize_doc_ids(doc_ids: list[int] | None) -> list[int]:
    if not doc_ids:
        return []
    values: list[int] = []
    for item in doc_ids:
        if isinstance(item, bool):
            continue
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if value > 0 and value not in values:
            values.append(value)
    return values


def _sanitize_space_id(space_id: int | None) -> int | None:
    if space_id in (None, ""):
        return None
    try:
        value = int(space_id)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _resolve_qa_document_scope(doc_ids: list[int] | None) -> tuple[int | None, list[int] | None]:
    scoped_doc_ids = _sanitize_doc_ids(doc_ids)
    if not scoped_doc_ids:
        return None, None
    if len(scoped_doc_ids) == 1:
        return scoped_doc_ids[0], None
    return None, scoped_doc_ids


def _build_session_title(messages: list[DocumentQaMessage], fallback: str | None = None) -> str:
    for message in messages:
        if message.role == "user" and message.content:
            content = message.content.strip()
            if content:
                return f"{content[:30]}..." if len(content) > 30 else content
    return (fallback or "").strip()


def _replace_session_messages(session: DocumentQaSession, payload_messages) -> None:
    session.messages.clear()
    for item in payload_messages:
        session.messages.append(
            DocumentQaMessage(
                role=item.role,
                content=item.content,
                answer_mode=item.answerMode,
                answer_model=item.answerModel,
                sources_json=json.dumps(jsonable_encoder(item.sources), ensure_ascii=False),
                suggestions_json=json.dumps(jsonable_encoder(item.suggestions), ensure_ascii=False),
                message_ts=_parse_message_timestamp(item.timestamp),
            )
        )


@router.get(
    "",
    summary="获取文档列表",
    response_model=ApiResponse[PageData[DocumentItem]],
)
def get_document_list(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1, title="页码", description="分页页码，从 1 开始"),
    pageSize: int = Query(default=10, ge=1, le=1000, title="每页条数", description="每页返回的文档数量"),
    status_filter: str | None = Query(default=None, alias="status", title="文档状态", description="按文档处理状态筛选"),
    keyword: str | None = Query(default=None, title="关键词", description="按文档标题模糊搜索"),
    spaceId: int | None = Query(default=None, title="知识空间 ID", description="按所属知识空间筛选"),
) -> dict:
    filters = []
    permission_clause = build_document_permission_clause(db, current_user, action="read")
    if permission_clause is not None:
        filters.append(permission_clause)
    if status_filter:
        filters.append(Document.status == status_filter)
    if keyword:
        keyword_value = f"%{keyword.strip()}%"
        filters.append(Document.title.ilike(keyword_value))
    if spaceId is not None:
        filters.append(Document.space_id == spaceId)

    total = db.scalar(select(func.count()).select_from(Document).where(*filters)) or 0

    # 列表查询只加载必要的关联，不加载 tasks 和 chunks
    documents = db.scalars(
        select(Document)
        .options(selectinload(Document.file_record))
        .options(selectinload(Document.space))
        .where(*filters)
        .order_by(Document.id.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()

    return paginated_response(
        [serialize_document(item, include_tasks=False, include_space=True) for item in documents],
        total,
        page,
        pageSize,
    )


@router.get(
    "/tasks",
    summary="获取文档任务列表",
    response_model=ApiResponse[PageData[DocumentTaskItem]],
)
def get_document_task_list(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1, title="页码", description="分页页码，从 1 开始"),
    pageSize: int = Query(default=10, ge=1, le=1000, title="每页条数", description="每页返回的任务数量"),
    status_filter: str | None = Query(default=None, alias="status", title="任务状态", description="按任务处理状态筛选"),
) -> dict:
    filters = []
    permission_clause = build_document_permission_clause(db, current_user, action="read")
    if permission_clause is not None:
        filters.append(DocumentTask.document_id.in_(select(Document.id).where(permission_clause)))
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
    pending_count = (
        db.scalar(select(func.count()).select_from(Document).where(Document.status == "pending"))
        or 0
    )
    processing_count = (
        db.scalar(select(func.count()).select_from(Document).where(Document.status == "processing"))
        or 0
    )
    return success_response(
        {
            "queueName": DOCUMENT_QUEUE_NAME,
            "processingMode": settings.document_processing_mode,
            "pendingCount": pending_count,
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
    current_user: CurrentUser,
    limit: int = Query(default=5, ge=1, le=20, title="返回条数", description="最多返回的检索结果数量"),
    documentId: int | None = Query(default=None, title="文档 ID", description="限定在某份文档范围内检索"),
    spaceId: int | None = Query(default=None, title="知识空间 ID", description="限定在某个知识空间内检索"),
) -> dict:
    keyword = query.strip()
    if not keyword:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="检索关键词不能为空")

    hits = retrieve_document_chunks(
        db,
        current_user,
        query=keyword,
        limit=limit,
        document_id=documentId,
        space_id=spaceId,
    )
    return success_response(hits)


@router.get(
    "/qa/sessions",
    summary="获取问答会话列表",
    response_model=ApiResponse[list[DocumentQaSessionItem]],
)
def get_document_qa_sessions(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    sessions = db.scalars(
        _document_qa_session_query()
        .where(DocumentQaSession.user_id == current_user.id)
        .order_by(DocumentQaSession.updated_at.desc(), DocumentQaSession.id.desc())
    ).all()
    return success_response([serialize_document_qa_session(session) for session in sessions])


@router.post(
    "/qa/sessions",
    summary="创建问答会话",
    response_model=ApiResponse[DocumentQaSessionItem],
)
def create_document_qa_session(
    payload: DocumentQaSessionCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    session = DocumentQaSession(
        user_id=current_user.id,
        space_id=_sanitize_space_id(payload.spaceId),
        document_ids_json=json.dumps(_sanitize_doc_ids(payload.docIds), ensure_ascii=False),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    session = _get_document_qa_session_or_404(db, session.id, current_user)
    return success_response(serialize_document_qa_session(session))


@router.put(
    "/qa/sessions/{session_id}",
    summary="更新问答会话",
    response_model=ApiResponse[DocumentQaSessionItem],
)
def update_document_qa_session(
    session_id: Annotated[int, Path(title="会话 ID", description="要更新的聊天会话 ID")],
    payload: DocumentQaSessionUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    session = _get_document_qa_session_or_404(db, session_id, current_user)
    session.title = (payload.title or "").strip() or None
    session.space_id = _sanitize_space_id(payload.spaceId)
    session.document_ids_json = json.dumps(_sanitize_doc_ids(payload.docIds), ensure_ascii=False)
    db.commit()
    db.refresh(session)
    session = _get_document_qa_session_or_404(db, session.id, current_user)
    return success_response(serialize_document_qa_session(session))


@router.put(
    "/qa/sessions/{session_id}/sync",
    summary="同步问答会话消息",
    response_model=ApiResponse[DocumentQaSessionItem],
)
def sync_document_qa_session(
    session_id: Annotated[int, Path(title="会话 ID", description="要同步的聊天会话 ID")],
    payload: DocumentQaSessionSyncRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    session = _get_document_qa_session_or_404(db, session_id, current_user)
    session.space_id = _sanitize_space_id(payload.spaceId)
    session.document_ids_json = json.dumps(_sanitize_doc_ids(payload.docIds), ensure_ascii=False)
    _replace_session_messages(session, payload.messages)
    session.title = _build_session_title(session.messages, fallback=payload.title) or None
    db.commit()
    db.refresh(session)
    session = _get_document_qa_session_or_404(db, session.id, current_user)
    return success_response(serialize_document_qa_session(session))


@router.delete(
    "/qa/sessions/{session_id}",
    summary="删除问答会话",
    response_model=ApiResponse[None],
)
def delete_document_qa_session(
    session_id: Annotated[int, Path(title="会话 ID", description="要删除的聊天会话 ID")],
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    session = _get_document_qa_session_or_404(db, session_id, current_user)
    db.delete(session)
    db.commit()
    return success_response(message="对话已删除")


@router.delete(
    "/qa/sessions/{session_id}/messages/{message_id}",
    summary="删除问答消息",
    response_model=ApiResponse[DocumentQaSessionItem],
)
def delete_document_qa_message(
    session_id: Annotated[int, Path(title="会话 ID", description="所属聊天会话 ID")],
    message_id: Annotated[int, Path(title="消息 ID", description="要删除的消息 ID")],
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    session = _get_document_qa_session_or_404(db, session_id, current_user)
    messages = list(session.messages)
    target_index = next((idx for idx, item in enumerate(messages) if item.id == message_id), -1)
    if target_index < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")

    target = messages[target_index]
    delete_items = [target]
    if target.role == "user":
        next_index = target_index + 1
        if next_index < len(messages) and messages[next_index].role == "assistant":
            delete_items.append(messages[next_index])

    for item in delete_items:
        db.delete(item)

    db.flush()
    refreshed_messages = db.scalars(
        select(DocumentQaMessage)
        .where(DocumentQaMessage.session_id == session.id)
        .order_by(DocumentQaMessage.id.asc())
    ).all()
    session.title = _build_session_title(refreshed_messages) or None
    db.commit()
    session = _get_document_qa_session_or_404(db, session.id, current_user)
    return success_response(serialize_document_qa_session(session), message="消息已删除")


@router.get(
    "/{document_id}",
    summary="获取文档详情",
    response_model=ApiResponse[DocumentItem],
)
def get_document_detail(
    document_id: Annotated[int, Path(title="文档 ID", description="要查询的文档主键 ID")],
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    return success_response(
        serialize_document(
            _get_document_detail_or_404(db, document_id, current_user, action="read"),
            include_tasks=True,
            include_space=True,
        )
    )


@router.get(
    "/{document_id}/chunks",
    summary="获取文档切片列表",
    response_model=ApiResponse[PageData[DocumentChunkItem]],
)
def get_document_chunks(
    document_id: Annotated[int, Path(title="文档 ID", description="要查询切片列表的文档主键 ID")],
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1, title="页码", description="分页页码，从 1 开始"),
    pageSize: int = Query(default=10, ge=1, le=1000, title="每页条数", description="每页返回的切片数量"),
) -> dict:
    _get_document_detail_or_404(db, document_id, current_user, action="read")
    total = db.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document_id)) or 0
    chunks = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()
    return paginated_response([serialize_document_chunk(item) for item in chunks], total, page, pageSize)


@router.delete(
    "/{document_id}",
    summary="删除文档",
    response_model=ApiResponse[None],
)
def delete_document(
    document_id: Annotated[int, Path(title="文档 ID", description="要删除的文档主键 ID")],
    db: DbSession,
    current_user: CurrentUser,
    request: Request,
) -> dict:
    document = _get_document_detail_or_404(db, document_id, current_user, action="manage")
    if document.status == "processing":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="文档正在处理中，请稍后再删除")

    file_record = document.file_record
    client_ip = request.client.host if request.client else None

    # 先删除外部资源（向量和 MinIO 文件）
    try:
        logger.info(
            "开始删除文档外部资源: document_id=%d, user_id=%d, title=%s",
            document_id,
            current_user.id,
            document.title,
        )

        # 删除向量数据
        delete_document_vectors(document.id)
        logger.info("文档向量已删除: document_id=%d", document_id)

        # 删除 MinIO 文件
        if file_record:
            remove_file_from_minio(file_record.file_name)
            logger.info("MinIO 文件已删除: document_id=%d, file_name=%s", document_id, file_record.file_name)

    except Exception as e:
        logger.error(
            "删除文档外部资源失败: document_id=%d, error=%s",
            document_id,
            str(e),
            exc_info=True,
        )
        # 记录审计日志
        log_audit(
            action=AuditAction.DOCUMENT_DELETE,
            user_id=current_user.id,
            username=current_user.username,
            resource_type="document",
            resource_id=document_id,
            ip_address=client_ip,
            success=False,
            details={"title": document.title, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文件失败: {str(e)}，请稍后重试",
        )

    # 外部资源删除成功后，再删除数据库记录
    try:
        db.delete(document)
        if file_record:
            db.delete(file_record)
        db.commit()

        logger.info(
            "文档删除成功: document_id=%d, user_id=%d, title=%s",
            document_id,
            current_user.id,
            document.title,
        )

        # 记录审计日志
        log_audit(
            action=AuditAction.DOCUMENT_DELETE,
            user_id=current_user.id,
            username=current_user.username,
            resource_type="document",
            resource_id=document_id,
            ip_address=client_ip,
            success=True,
            details={"title": document.title, "file_name": file_record.file_name if file_record else None},
        )

    except Exception as e:
        db.rollback()
        logger.error(
            "删除文档数据库记录失败: document_id=%d, error=%s",
            document_id,
            str(e),
            exc_info=True,
        )
        # 记录审计日志
        log_audit(
            action=AuditAction.DOCUMENT_DELETE,
            user_id=current_user.id,
            username=current_user.username,
            resource_type="document",
            resource_id=document_id,
            ip_address=client_ip,
            success=False,
            details={"title": document.title, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除文档记录失败，请稍后重试",
        )

    return success_response(message="文档已删除，相关切片、向量和文件记录已同步清理")


@router.post(
    "/{document_id}/reprocess",
    summary="重新处理文档",
    response_model=ApiResponse[ReprocessDocumentData],
)
def reprocess_document(
    document_id: Annotated[int, Path(title="文档 ID", description="要重新处理的文档主键 ID")],
    payload: DocumentReprocessRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    document = _get_document_detail_or_404(db, document_id, current_user, action="manage")
    latest_task = db.scalar(
        select(DocumentTask)
        .where(DocumentTask.document_id == document_id)
        .order_by(DocumentTask.id.desc())
        .limit(1)
    )
    if latest_task and latest_task.status in {"pending", "processing"} and not payload.force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前文档已有处理中任务，如需强制重处理请传入 force=true",
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

    refreshed = _get_document_detail_or_404(db, document.id, current_user, action="manage")
    return success_response(
        {
            "document": serialize_document(refreshed, include_tasks=True),
            "task": serialize_document_task(task),
        },
        message="文档已重新入队，系统会自动继续处理",
    )


@router.post(
    "/qa",
    summary="文档问答",
    response_model=ApiResponse[DocumentQaData],
)
def document_qa(
    payload: DocumentQaRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="问题不能为空")

    history = None
    if payload.history:
        history = [{"role": m.role, "content": m.content} for m in payload.history if m.role in ("user", "assistant")]

    document_id, document_ids = _resolve_qa_document_scope(payload.documentIds)
    hits = retrieve_document_chunks(
        db,
        current_user,
        query=question,
        limit=payload.limit,
        document_id=document_id,
        document_ids=document_ids,
        space_id=payload.spaceId,
    )
    return success_response(answer_question_from_hits(question, hits, history=history))
