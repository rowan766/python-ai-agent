from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Path, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.http import success_response
from app.models import Document, DocumentTask, FileRecord, KnowledgeSpace
from app.schemas import ApiResponse, FileRecordItem, UploadFileResult
from app.services.document_permissions import get_document_or_404
from app.services.document_queue import DOCUMENT_QUEUE_NAME, enqueue_document_task
from app.services.knowledge_space_permissions import (
    build_space_access_clause,
    ensure_default_knowledge_space,
    is_platform_super_admin,
)
from app.services.object_storage import (
    build_download_headers,
    get_minio_object,
    iter_minio_object,
    remove_file_from_minio,
    upload_file_to_minio,
)
from app.services.qdrant_vector_store import delete_document_vectors
from app.services.serializers import serialize_document, serialize_file_record


router = APIRouter(prefix="/upload", tags=["文件上传"])
settings = get_settings()


def _cleanup_uploaded_objects(object_names: list[str]) -> None:
    for object_name in object_names:
        remove_file_from_minio(object_name)


def _store_files(
    files: list[UploadFile],
    current_user_id: int,
    target_folder: str,
    bucket_type: str,
    db: DbSession,
) -> tuple[list[FileRecord], list[str]]:
    records: list[FileRecord] = []
    uploaded_objects: list[str] = []
    for upload in files:
        _, object_name, file_size = upload_file_to_minio(upload, target_folder)
        uploaded_objects.append(object_name)
        record = FileRecord(
            user_id=current_user_id,
            bucket_name=settings.minio_bucket_name,
            bucket_type=bucket_type,
            folder=target_folder,
            file_name=object_name,
            original_name=upload.filename or object_name.rsplit("/", 1)[-1],
            file_size=file_size,
            mime_type=upload.content_type or "application/octet-stream",
            file_url=f"{settings.minio_public_base_url}/{settings.minio_bucket_name}/{object_name}",
            status=1,
        )
        db.add(record)
        db.flush()
        records.append(record)
    return records, uploaded_objects


def _create_document_jobs(
    db: DbSession,
    *,
    current_user,
    target_space: KnowledgeSpace,
    file_records: list[FileRecord],
) -> tuple[list[Document], list[DocumentTask]]:
    documents: list[Document] = []
    tasks: list[DocumentTask] = []
    for file_record in file_records:
        document = Document(
            user_id=current_user.id,
            space_id=target_space.id,
            owner_user_id=current_user.id,
            owner_department_id=current_user.department_id,
            file_id=file_record.id,
            title=file_record.original_name,
            file_name=file_record.original_name,
            mime_type=file_record.mime_type,
            file_size=file_record.file_size,
            status="pending",
            parse_mode="auto",
        )
        document.space = target_space
        db.add(document)
        db.flush()

        task = DocumentTask(
            document_id=document.id,
            task_type="ingest",
            queue_name=DOCUMENT_QUEUE_NAME,
            status="pending",
        )
        db.add(task)
        db.flush()

        documents.append(document)
        tasks.append(task)
    return documents, tasks


def _get_file_or_404(db: DbSession, file_id: int) -> FileRecord:
    file_record = db.scalar(select(FileRecord).where(FileRecord.id == file_id))
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return file_record


def _assert_file_access(db: DbSession, current_user, file_record: FileRecord, *, action: str = "read") -> Document | None:
    document = db.scalar(select(Document).where(Document.file_id == file_record.id))
    if document:
        get_document_or_404(db, current_user, document.id, action=action)
        return document

    if file_record.user_id != current_user.id and not is_platform_super_admin(db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该文件")
    return None


def _get_upload_target_space(db: DbSession, current_user, space_id: int | None) -> KnowledgeSpace:
    if space_id is None:
        return ensure_default_knowledge_space(db, current_user)

    statement = select(KnowledgeSpace).where(KnowledgeSpace.id == space_id)
    access_clause = build_space_access_clause(db, current_user, action="write")
    if access_clause is not None:
        statement = statement.where(access_clause)
    space = db.scalar(statement)
    if not space:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识空间不存在或无写入权限")
    return space


@router.post(
    "/images",
    summary="上传图片",
    response_model=ApiResponse[list[FileRecordItem]],
)
def upload_images(
    db: DbSession,
    current_user: CurrentUser,
    files: list[UploadFile] = File(..., description="要上传的图片文件列表，支持一次上传多个文件"),
) -> dict:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择要上传的图片")

    uploaded_objects: list[str] = []
    try:
        file_records, uploaded_objects = _store_files(files, current_user.id, "images", "image", db)
        db.commit()
        for record in file_records:
            db.refresh(record)
        return success_response([serialize_file_record(record) for record in file_records], message="上传成功")
    except Exception:
        db.rollback()
        _cleanup_uploaded_objects(uploaded_objects)
        raise


@router.post(
    "/files",
    summary="上传文件",
    response_model=ApiResponse[list[UploadFileResult]],
)
def upload_files(
    db: DbSession,
    current_user: CurrentUser,
    spaceId: int | None = Form(default=None, description="上传目标知识空间 ID，不传则自动写入默认知识空间"),
    files: list[UploadFile] = File(..., description="要上传的文件列表，上传后会自动创建文档并加入处理队列"),
) -> dict:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择要上传的文件")

    uploaded_objects: list[str] = []
    try:
        target_space = _get_upload_target_space(db, current_user, spaceId)
        file_records, uploaded_objects = _store_files(files, current_user.id, "files", "file", db)
        documents, tasks = _create_document_jobs(
            db,
            current_user=current_user,
            target_space=target_space,
            file_records=file_records,
        )
        db.commit()

        for task in tasks:
            enqueue_document_task(task.id, task.queue_name)

        document_map = {document.file_id: document for document in documents}
        response_items = []
        for record in file_records:
            payload = serialize_file_record(record)
            document = document_map.get(record.id)
            if document:
                payload["document"] = serialize_document(document, include_file=False, include_space=True)
                payload["documentId"] = document.id
                payload["documentStatus"] = document.status
            response_items.append(payload)
        return success_response(response_items, message="上传成功，文档已入队，系统会自动处理")
    except Exception:
        db.rollback()
        _cleanup_uploaded_objects(uploaded_objects)
        raise


@router.get("/image/{file_id}", summary="预览图片")
def preview_image(
    file_id: Annotated[int, Path(title="文件 ID", description="要预览的图片文件主键 ID")],
    db: DbSession,
    current_user: CurrentUser,
    download: bool = Query(default=False, title="是否下载", description="是否以附件下载方式返回图片"),
) -> StreamingResponse:
    file_record = _get_file_or_404(db, file_id)
    _assert_file_access(db, current_user, file_record, action="read")
    object_response = get_minio_object(file_record.file_name)
    response = StreamingResponse(
        iter_minio_object(object_response),
        media_type=file_record.mime_type,
    )
    response.headers.update(build_download_headers(file_record.original_name, inline=not download))
    return response


@router.get("/file/{file_id}/download", summary="下载文件")
def download_file(
    file_id: Annotated[int, Path(title="文件 ID", description="要下载的文件主键 ID")],
    db: DbSession,
    current_user: CurrentUser,
) -> StreamingResponse:
    file_record = _get_file_or_404(db, file_id)
    _assert_file_access(db, current_user, file_record, action="read")
    object_response = get_minio_object(file_record.file_name)
    response = StreamingResponse(
        iter_minio_object(object_response),
        media_type=file_record.mime_type or "application/octet-stream",
    )
    response.headers.update(build_download_headers(file_record.original_name))
    return response


@router.delete(
    "/file/{file_id}",
    summary="删除上传文件",
    response_model=ApiResponse[None],
)
def delete_uploaded_file(
    file_id: Annotated[int, Path(title="文件 ID", description="要删除的文件主键 ID")],
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    file_record = _get_file_or_404(db, file_id)
    document = _assert_file_access(db, _current_user, file_record, action="manage")
    if document:
        delete_document_vectors(document.id)
    remove_file_from_minio(file_record.file_name)
    db.delete(file_record)
    db.commit()
    return success_response(message="删除成功")
