from pathlib import Path
from typing import Iterator
from urllib.parse import quote
import uuid

from fastapi import HTTPException, UploadFile, status
from minio import Minio
from minio.error import S3Error
from minio.helpers import ObjectWriteResult
from minio.datatypes import Object

from app.core.config import get_settings


settings = get_settings()


def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        region=settings.minio_region,
    )


def ensure_minio_bucket() -> None:
    client = get_minio_client()
    if not client.bucket_exists(settings.minio_bucket_name):
        client.make_bucket(settings.minio_bucket_name)


def upload_file_to_minio(upload: UploadFile, folder: str) -> tuple[ObjectWriteResult, str, int]:
    extension = Path(upload.filename or "").suffix
    object_name = f"{folder}/{uuid.uuid4().hex}{extension}"
    upload.file.seek(0, 2)
    file_size = upload.file.tell()
    upload.file.seek(0)
    result = get_minio_client().put_object(
        settings.minio_bucket_name,
        object_name,
        upload.file,
        length=file_size,
        content_type=upload.content_type or "application/octet-stream",
    )
    return result, object_name, file_size


def remove_file_from_minio(object_name: str) -> None:
    try:
        get_minio_client().remove_object(settings.minio_bucket_name, object_name)
    except S3Error as exc:
        if exc.code not in {"NoSuchKey", "NoSuchObject"}:
            raise


def get_minio_object(object_name: str) -> Object:
    try:
        return get_minio_client().get_object(settings.minio_bucket_name, object_name)
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件内容不存在") from exc
        raise


def iter_minio_object(response: Object, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
    try:
        yield from response.stream(chunk_size)
    finally:
        response.close()
        response.release_conn()


def build_download_headers(filename: str, inline: bool = False) -> dict[str, str]:
    disposition_type = "inline" if inline else "attachment"
    encoded_name = quote(filename)
    return {
        "Content-Disposition": f"{disposition_type}; filename*=UTF-8''{encoded_name}",
    }
