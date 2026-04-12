from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from io import BytesIO
import json
import re
from pathlib import Path

from pypdf import PdfReader
from rapidocr_onnxruntime import RapidOCR
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Document, DocumentChunk, DocumentTask, FileRecord
from app.services.document_queue import pop_document_task
from app.services.object_storage import get_minio_object
from app.services.qdrant_vector_store import QdrantUnavailableError, delete_document_vectors, upsert_document_chunks


settings = get_settings()
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".json", ".log", ".yaml", ".yml", ".xml", ".html", ".htm"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


class DocumentProcessingError(Exception):
    pass


@dataclass
class TextChunk:
    index: int
    content: str
    char_start: int
    char_end: int


@dataclass
class ExtractedDocumentText:
    text: str
    parse_mode: str


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    return normalized.strip()


def _split_sentences(block: str) -> list[str]:
    sentences = [item.strip() for item in re.split(r"(?<=[。！？!?；;])\s+|\n+", block) if item and item.strip()]
    return sentences or [block.strip()]


def _split_text_units(text: str, *, max_unit_size: int) -> list[str]:
    units: list[str] = []
    blocks = [block.strip() for block in re.split(r"\n{2,}", text) if block and block.strip()]
    for block in blocks or [text]:
        if len(block) <= max_unit_size:
            units.append(block)
            continue

        buffer = ""
        for sentence in _split_sentences(block):
            if not buffer:
                buffer = sentence
                continue
            if len(buffer) + 1 + len(sentence) <= max_unit_size:
                buffer = f"{buffer} {sentence}"
                continue
            units.append(buffer)
            buffer = sentence

        if buffer:
            if len(buffer) <= max_unit_size:
                units.append(buffer)
            else:
                for start in range(0, len(buffer), max_unit_size):
                    units.append(buffer[start : start + max_unit_size].strip())

    return [unit for unit in units if unit]


def _decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DocumentProcessingError("当前文件编码暂不支持自动识别")


def _read_object_bytes(object_name: str) -> bytes:
    response = get_minio_object(object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


@lru_cache
def get_ocr_engine() -> RapidOCR:
    return RapidOCR()


def _normalize_ocr_text(lines: list[str]) -> str:
    return _normalize_text("\n".join(line.strip() for line in lines if line and line.strip()))


def _extract_text_from_ocr_bytes(data: bytes) -> str:
    result, _ = get_ocr_engine()(data)
    if not result:
        return ""
    lines = [str(item[1]).strip() for item in result if len(item) >= 2 and item[1]]
    return _normalize_ocr_text(lines)


def _extract_text_from_pdf_ocr(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    page_texts: list[str] = []
    for page in reader.pages:
        image_texts: list[str] = []
        for image in page.images:
            image_text = _extract_text_from_ocr_bytes(image.data)
            if image_text:
                image_texts.append(image_text)
        if image_texts:
            page_texts.append("\n".join(image_texts))
    return _normalize_text("\n\n".join(page_texts))


def _extract_text_from_pdf(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    page_texts: list[str] = []
    for page in reader.pages:
        page_texts.append(page.extract_text() or "")
    return _normalize_text("\n\n".join(page_texts))


def extract_document_text(file_record: FileRecord) -> ExtractedDocumentText:
    extension = Path(file_record.original_name or file_record.file_name).suffix.lower()
    data = _read_object_bytes(file_record.file_name)

    if extension in TEXT_EXTENSIONS or file_record.mime_type.startswith("text/"):
        return ExtractedDocumentText(
            text=_normalize_text(_decode_bytes(data)),
            parse_mode="text_direct",
        )

    if extension == ".pdf" or file_record.mime_type == "application/pdf":
        extracted_text = _extract_text_from_pdf(data)
        if extracted_text:
            return ExtractedDocumentText(
                text=extracted_text,
                parse_mode="pdf_text",
            )

        ocr_text = _extract_text_from_pdf_ocr(data)
        if ocr_text:
            return ExtractedDocumentText(
                text=ocr_text,
                parse_mode="pdf_ocr_fallback",
            )
        raise DocumentProcessingError("PDF 未提取到可用文本，且 OCR 结果为空")

    if extension in IMAGE_EXTENSIONS or file_record.mime_type.startswith("image/"):
        extracted_text = _extract_text_from_ocr_bytes(data)
        if extracted_text:
            return ExtractedDocumentText(
                text=extracted_text,
                parse_mode="image_ocr",
            )
        raise DocumentProcessingError("图片类文档 OCR 结果为空")

    raise DocumentProcessingError(f"暂不支持解析该文件类型：{extension or file_record.mime_type}")


def build_text_chunks(text: str, *, chunk_size: int, chunk_overlap: int) -> list[TextChunk]:
    normalized = _normalize_text(text)
    if not normalized:
        raise DocumentProcessingError("文档解析后没有可用文本内容")

    safe_overlap = max(0, min(chunk_overlap, chunk_size - 1))
    chunks: list[TextChunk] = []
    index = 0
    cursor = 0
    units = _split_text_units(normalized, max_unit_size=max(chunk_size // 2, 180))
    current_chunk = ""
    chunk_start = 0

    for unit in units:
        unit_start = normalized.find(unit, cursor)
        if unit_start == -1:
            unit_start = cursor
        unit_end = unit_start + len(unit)
        cursor = unit_end

        if not current_chunk:
            current_chunk = unit
            chunk_start = unit_start
            continue

        proposed = f"{current_chunk}\n\n{unit}"
        if len(proposed) <= chunk_size:
            current_chunk = proposed
            continue

        chunk_end = chunk_start + len(current_chunk)
        chunks.append(
            TextChunk(
                index=index,
                content=current_chunk.strip(),
                char_start=chunk_start,
                char_end=chunk_end,
            )
        )
        index += 1

        overlap_text = current_chunk[-safe_overlap:].strip() if safe_overlap else ""
        if overlap_text:
            overlap_start = max(chunk_end - len(overlap_text), chunk_start)
            current_chunk = f"{overlap_text}\n\n{unit}".strip()
            chunk_start = overlap_start
        else:
            current_chunk = unit
            chunk_start = unit_start

    if current_chunk:
        chunks.append(
            TextChunk(
                index=index,
                content=current_chunk.strip(),
                char_start=chunk_start,
                char_end=chunk_start + len(current_chunk),
            )
        )

    return chunks


def process_document_task(task_id: int) -> bool:
    with SessionLocal() as db:
        task = db.scalar(
            select(DocumentTask)
            .options(
                selectinload(DocumentTask.document)
                .selectinload(Document.file_record),
            )
            .where(DocumentTask.id == task_id)
        )
        if not task or not task.document:
            return False

        document = task.document
        now = datetime.utcnow()
        task.status = "processing"
        task.attempts += 1
        task.started_at = now
        task.finished_at = None
        task.error_message = None
        document.status = "processing"
        document.error_message = None
        db.commit()

        try:
            extraction_result = extract_document_text(document.file_record)
            chunks = build_text_chunks(
                extraction_result.text,
                chunk_size=settings.document_chunk_size,
                chunk_overlap=settings.document_chunk_overlap,
            )

            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
            delete_document_vectors(document.id)
            for chunk in chunks:
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        task_id=task.id,
                        chunk_index=chunk.index,
                        content=chunk.content,
                        content_length=len(chunk.content),
                        char_start=chunk.char_start,
                        char_end=chunk.char_end,
                        status="ready",
                        metadata_json=json.dumps(
                            {
                                "sourceFileId": document.file_id,
                                "sourceFileName": document.file_name,
                                "mimeType": document.mime_type,
                                "parseMode": extraction_result.parse_mode,
                            },
                            ensure_ascii=False,
                        ),
                    )
                )
            db.commit()

            stored_chunks = db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document.id)
                .order_by(DocumentChunk.chunk_index.asc())
            ).all()
            try:
                upsert_document_chunks(document.id, stored_chunks)
            except QdrantUnavailableError as exc:
                print(f"文档 {document.id} 切片已入库，但向量写入跳过: {exc}")

            finished_at = datetime.utcnow()
            task.status = "success"
            task.finished_at = finished_at
            task.error_message = None
            document.status = "success"
            document.parse_mode = extraction_result.parse_mode
            document.text_length = len(extraction_result.text)
            document.chunk_count = len(chunks)
            document.error_message = None
            document.processed_at = finished_at
            db.commit()
            return True
        except Exception as exc:
            error_message = str(exc) or "文档处理失败"
            finished_at = datetime.utcnow()
            delete_document_vectors(document.id)
            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
            task.status = "failed"
            task.finished_at = finished_at
            task.error_message = error_message
            document.status = "failed"
            document.text_length = 0
            document.chunk_count = 0
            document.error_message = error_message
            document.processed_at = finished_at
            db.commit()
            return False


def drain_document_queue(*, max_tasks: int = 5) -> int:
    processed_count = 0
    for _ in range(max_tasks):
        task_id = pop_document_task()
        if task_id is None:
            break
        process_document_task(task_id)
        processed_count += 1
    return processed_count
