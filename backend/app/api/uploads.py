from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.http import success_response
from app.models import FileRecord
from app.services.object_storage import (
    build_download_headers,
    get_minio_object,
    iter_minio_object,
    remove_file_from_minio,
    upload_file_to_minio,
)
from app.services.serializers import serialize_file_record


router = APIRouter(prefix="/upload", tags=["文件上传"])
settings = get_settings()

def _store_files(files: list[UploadFile], current_user_id: int, target_folder: str, bucket_type: str, db: DbSession) -> list[dict]:
    records: list[dict] = []
    uploaded_objects: list[str] = []
    try:
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
            records.append(serialize_file_record(record))
        db.commit()
        return records
    except Exception:
        db.rollback()
        for object_name in uploaded_objects:
            remove_file_from_minio(object_name)
        raise


def _get_file_or_404(db: DbSession, file_id: int) -> FileRecord:
    file_record = db.scalar(select(FileRecord).where(FileRecord.id == file_id))
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return file_record


@router.post("/images", summary="上传图片")
def upload_images(
    db: DbSession,
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
) -> dict:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择要上传的图片")
    return success_response(_store_files(files, current_user.id, "images", "image", db), message="上传成功")


@router.post("/files", summary="上传文件")
def upload_files(
    db: DbSession,
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
) -> dict:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择要上传的文件")
    return success_response(_store_files(files, current_user.id, "files", "file", db), message="上传成功")


@router.get("/image/{file_id}", summary="预览图片")
def preview_image(file_id: int, db: DbSession, download: bool = Query(default=False)) -> StreamingResponse:
    file_record = _get_file_or_404(db, file_id)
    object_response = get_minio_object(file_record.file_name)
    response = StreamingResponse(
        iter_minio_object(object_response),
        media_type=file_record.mime_type,
    )
    response.headers.update(build_download_headers(file_record.original_name, inline=not download))
    return response


@router.get("/file/{file_id}/download", summary="下载文件")
def download_file(file_id: int, db: DbSession) -> StreamingResponse:
    file_record = _get_file_or_404(db, file_id)
    object_response = get_minio_object(file_record.file_name)
    response = StreamingResponse(
        iter_minio_object(object_response),
        media_type=file_record.mime_type or "application/octet-stream",
    )
    response.headers.update(build_download_headers(file_record.original_name))
    return response


@router.delete("/file/{file_id}", summary="删除上传文件")
def delete_uploaded_file(file_id: int, db: DbSession, _current_user: CurrentUser) -> dict:
    file_record = _get_file_or_404(db, file_id)
    remove_file_from_minio(file_record.file_name)
    db.delete(file_record)
    db.commit()
    return success_response(message="删除成功")
