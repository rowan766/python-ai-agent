from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import get_settings
from app.services.llm_service import LlmUnavailableError, generate_rag_answer


logger = logging.getLogger("app.rag_answer")


settings = get_settings()
_sentence_split_pattern = re.compile(r"(?<=[。！？!?；;\n])")


def _split_sentences(text: str) -> list[str]:
    parts = [segment.strip() for segment in _sentence_split_pattern.split(text) if segment and segment.strip()]
    return parts or [text.strip()]


def _build_extractive_answer(question: str, hits: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    if not hits:
        return "当前没有检索到可用于回答的问题上下文。", []

    remaining_chars = settings.rag_answer_max_context_chars
    selected_sources: list[dict[str, Any]] = []
    answer_segments: list[str] = []

    for hit in hits[: settings.rag_answer_max_chunks]:
        content = str(hit.get("content") or "").strip()
        if not content or remaining_chars <= 0:
            continue

        snippet_parts = []
        consumed = 0
        for sentence in _split_sentences(content):
            sentence = sentence.strip()
            if not sentence:
                continue
            if consumed + len(sentence) > min(remaining_chars, 280):
                break
            snippet_parts.append(sentence)
            consumed += len(sentence)
            if len(snippet_parts) >= 2:
                break

        snippet = " ".join(snippet_parts).strip() or content[: min(remaining_chars, 180)].strip()
        remaining_chars -= len(snippet)
        if not snippet:
            continue

        document = hit.get("document") or {}
        document_title = document.get("title") or f"文档#{hit.get('documentId', '-')}"
        answer_segments.append(f"【{document_title}】{snippet}")
        selected_sources.append(
            {
                "documentId": hit.get("documentId"),
                "documentTitle": document.get("title"),
                "chunkId": hit.get("chunkId"),
                "chunkIndex": hit.get("chunkIndex"),
                "score": hit.get("score"),
                "content": hit.get("content"),
            }
        )

    if not answer_segments:
        return "当前没有检索到可用于回答的问题上下文。", []

    answer = f"根据当前命中的文档切片，和“{question.strip()}”最相关的信息如下：\n\n" + "\n\n".join(answer_segments)
    return answer, selected_sources


def _build_llm_context_blocks(sources: list[dict[str, Any]]) -> list[str]:
    context_blocks: list[str] = []
    for index, source in enumerate(sources, start=1):
        content = str(source.get("content") or "").strip()
        if not content:
            continue
        document_title = source.get("documentTitle") or f"文档#{source.get('documentId', '-')}"
        chunk_index = source.get("chunkIndex")
        context_blocks.append(
            f"来源{index}\n文档标题：{document_title}\n切片序号：{chunk_index}\n内容：{content}"
        )
    return context_blocks


def answer_question_from_hits(question: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    answer, sources = _build_extractive_answer(question, hits)
    answer_mode = "extractive-preview"

    if sources:
        try:
            answer = generate_rag_answer(question, _build_llm_context_blocks(sources))
            answer_mode = "llm-rag"
        except LlmUnavailableError as exc:
            logger.warning("LLM 不可用，回退到检索摘要: %s", exc)
            answer_mode = "extractive-preview"
        except Exception as exc:
            logger.error("LLM 调用异常，回退到检索摘要: %s", exc, exc_info=True)
            answer_mode = "extractive-preview"

    return {
        "question": question,
        "answer": answer,
        "answerMode": answer_mode,
        "answerModel": settings.llm_model_name if answer_mode == "llm-rag" else None,
        "sources": sources,
        "retrievalCount": len(sources),
    }
