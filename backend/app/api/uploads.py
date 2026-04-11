from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.http import success_response
from app.models import FileRecord
from app.services.serializers import serialize_file_record


router = APIRouter(prefix="/upload", tags=["文件上传"])
settings = get_settings()


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _store_files(files: list[UploadFile], current_user_id: int, target_folder: str, bucket_type: str, base_route: str, db: DbSession) -> list[dict]:
    destination = settings.upload_root / target_folder
    _ensure_directory(destination)

    records: list[dict] = []
    for upload in files:
        extension = Path(upload.filename or "").suffix
        generated_name = f"{uuid.uuid4().hex}{extension}"
        stored_path = destination / generated_name
        with stored_path.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

        record = FileRecord(
            user_id=current_user_id,
            bucket_name="local-storage",
            bucket_type=bucket_type,
            folder=target_folder,
            file_name=f"{target_folder}/{generated_name}",
            original_name=upload.filename or generated_name,
            file_size=stored_path.stat().st_size,
            mime_type=upload.content_type or "application/octet-stream",
            file_url=f"/upload/{base_route}/{generated_name}",
            status=1,
        )
        db.add(record)
        db.flush()
        records.append(serialize_file_record(record))

    db.commit()
    return records


def _get_file_or_404(db: DbSession, file_id: int) -> FileRecord:
    file_record = db.scalar(select(FileRecord).where(FileRecord.id == file_id))
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return file_record


def _build_physical_path(file_record: FileRecord) -> Path:
    return settings.upload_root / file_record.file_name


@router.post("/images", summary="上传图片")
def upload_images(
    db: DbSession,
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
) -> dict:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择要上传的图片")
    return success_response(_store_files(files, current_user.id, "images", "image", "image", db), message="上传成功")


@router.post("/files", summary="上传文件")
def upload_files(
    db: DbSession,
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
) -> dict:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择要上传的文件")
    return success_response(_store_files(files, current_user.id, "files", "file", "file", db), message="上传成功")


@router.get("/image/{file_id}", summary="预览图片")
def preview_image(file_id: int, db: DbSession, download: bool = Query(default=False)) -> FileResponse:
    file_record = _get_file_or_404(db, file_id)
    file_path = _build_physical_path(file_record)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件内容不存在")
    return FileResponse(
        file_path,
        media_type=file_record.mime_type,
        filename=file_record.original_name,
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("/file/{file_id}/download", summary="下载文件")
def download_file(file_id: int, db: DbSession) -> FileResponse:
    file_record = _get_file_or_404(db, file_id)
    file_path = _build_physical_path(file_record)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件内容不存在")
    return FileResponse(
        file_path,
        media_type=file_record.mime_type or "application/octet-stream",
        filename=file_record.original_name,
        content_disposition_type="attachment",
    )


@router.delete("/file/{file_id}", summary="删除上传文件")
def delete_uploaded_file(file_id: int, db: DbSession, _current_user: CurrentUser) -> dict:
    file_record = _get_file_or_404(db, file_id)
    file_path = _build_physical_path(file_record)
    if file_path.exists():
        file_path.unlink()
    db.delete(file_record)
    db.commit()
    return success_response(message="删除成功")
