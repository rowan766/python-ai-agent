from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import get_settings
from app.services.llm_service import LlmUnavailableError, generate_follow_up_suggestions, generate_rag_answer, generate_general_answer


logger = logging.getLogger("app.rag_answer")


settings = get_settings()
_sentence_split_pattern = re.compile(r"(?<=[。！？!?；;\n])")

# 相关性阈值：低于此分数认为检索结果不相关
RELEVANCE_THRESHOLD = 0.3


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
        space = document.get("space") or {}
        answer_segments.append(f"【{document_title}】{snippet}")
        selected_sources.append(
            {
                "documentId": hit.get("documentId"),
                "documentTitle": document.get("title"),
                "spaceId": document.get("spaceId"),
                "spaceName": space.get("name"),
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
        space_name = source.get("spaceName")
        space_line = f"\n所属空间：{space_name}" if space_name else ""
        context_blocks.append(
            f"来源{index}\n文档标题：{document_title}{space_line}\n切片序号：{chunk_index}\n内容：{content}"
        )
    return context_blocks


def answer_question_from_hits(question: str, hits: list[dict[str, Any]], history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """
    基于检索结果回答问题

    策略：
    1. 如果检索结果相关性高 → 基于文档回答（RAG）
    2. 如果检索结果相关性低或为空 → LLM 直接回答（兜底）
    """
    # 判断检索结果的相关性
    max_score = max([hit.get("score", 0.0) for hit in hits], default=0.0)
    is_relevant = max_score >= RELEVANCE_THRESHOLD and len(hits) > 0

    logger.info(
        "检索结果分析: hits=%d, max_score=%.3f, is_relevant=%s",
        len(hits),
        max_score,
        is_relevant,
    )

    # 如果检索结果不相关，直接用 LLM 回答
    if not is_relevant:
        logger.info("检索结果不相关，使用 LLM 直接回答")
        try:
            answer = generate_general_answer(question, history=history)
            answer_mode = "llm-general"

            # 生成追问建议
            suggestions = []
            try:
                suggestions = generate_follow_up_suggestions(question, answer)
            except Exception:
                pass

            return {
                "question": question,
                "answer": answer,
                "answerMode": answer_mode,
                "answerModel": settings.llm_model_name,
                "sources": [],
                "retrievalCount": 0,
                "suggestions": suggestions,
            }
        except LlmUnavailableError as exc:
            logger.warning("LLM 不可用，返回友好提示: %s", exc)
            return {
                "question": question,
                "answer": "抱歉，当前知识库中没有找到相关内容，且 AI 助手暂时不可用。请尝试换个问题或联系管理员。",
                "answerMode": "fallback",
                "answerModel": None,
                "sources": [],
                "retrievalCount": 0,
                "suggestions": [],
            }
        except Exception as exc:
            logger.error("LLM 调用异常: %s", exc, exc_info=True)
            return {
                "question": question,
                "answer": "抱歉，AI 助手遇到了一些问题，请稍后再试。",
                "answerMode": "error",
                "answerModel": None,
                "sources": [],
                "retrievalCount": 0,
                "suggestions": [],
            }

    # 检索结果相关，基于文档回答
    answer, sources = _build_extractive_answer(question, hits)
    answer_mode = "extractive-preview"

    if sources:
        try:
            answer = generate_rag_answer(question, _build_llm_context_blocks(sources), history=history)
            answer_mode = "llm-rag"
        except LlmUnavailableError as exc:
            logger.warning("LLM 不可用，回退到检索摘要: %s", exc)
            answer_mode = "extractive-preview"
        except Exception as exc:
            logger.error("LLM 调用异常，回退到检索摘要: %s", exc, exc_info=True)
            answer_mode = "extractive-preview"

    # Generate follow-up suggestions
    suggestions = []
    if answer_mode in ("llm-rag", "llm-general"):
        try:
            suggestions = generate_follow_up_suggestions(question, answer)
        except Exception:
            pass

    return {
        "question": question,
        "answer": answer,
        "answerMode": answer_mode,
        "answerModel": settings.llm_model_name if answer_mode in ("llm-rag", "llm-general") else None,
        "sources": sources,
        "retrievalCount": len(sources),
        "suggestions": suggestions,
    }
