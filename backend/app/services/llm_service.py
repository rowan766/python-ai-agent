from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from openai import OpenAI

from app.core.config import get_settings


settings = get_settings()
logger = logging.getLogger("app.llm")


class LlmUnavailableError(RuntimeError):
    """Raised when the configured LLM service is not available."""


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text).strip())
            elif item:
                parts.append(str(item).strip())
        return "\n".join(part for part in parts if part).strip()
    return str(value).strip()


@lru_cache
def get_llm_client() -> OpenAI:
    if not settings.llm_enabled:
        raise LlmUnavailableError("未配置 LLM_API_KEY、DASHSCOPE_API_KEY 或 DEEPSEEK_API_KEY")
    provider = settings.llm_provider.strip().lower()
    if provider not in {"dashscope", "deepseek"}:
        raise LlmUnavailableError(f"暂不支持的 LLM Provider: {settings.llm_provider}")
    logger.info(
        "初始化 LLM 客户端: provider=%s base_url=%s model=%s",
        settings.llm_provider,
        settings.llm_base_url,
        settings.llm_model_name,
    )
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=1,
    )


def generate_rag_answer(question: str, context_blocks: list[str], history: list[dict[str, str]] | None = None) -> str:
    """基于检索到的文档上下文生成回答"""
    if not context_blocks:
        raise LlmUnavailableError("当前没有可用的检索上下文")

    client = get_llm_client()
    context_text = "\n\n".join(context_blocks)
    logger.info("调用 LLM 生成回答: question=%s, context_blocks=%d, history=%d, model=%s", question[:80], len(context_blocks), len(history or []), settings.llm_model_name)

    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "你是企业知识库问答助手。"
                "请严格依据提供的文档切片回答问题，不要编造未在上下文中出现的事实。"
                '如果上下文不足以回答，请明确说明"当前文档上下文不足以给出确定答案"。'
                "回答请使用中文，优先给出结论，再补充要点。"
                '如引用多条上下文，可在句子中自然提到"来源1""来源2"等标记。'
            ),
        },
    ]

    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    messages.append(
        {
            "role": "user",
            "content": (
                f"用户问题：{question.strip()}\n\n"
                "以下是检索到的文档上下文，请只基于这些内容回答：\n\n"
                f"{context_text}"
            ),
        },
    )
    completion = client.chat.completions.create(
        model=settings.llm_model_name,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        messages=messages,
    )
    content = _normalize_text(completion.choices[0].message.content if completion.choices else "")
    logger.info("LLM 返回内容长度: %d 字符", len(content))
    if not content:
        raise LlmUnavailableError("LLM 未返回有效内容")
    return content


def generate_general_answer(question: str, history: list[dict[str, str]] | None = None) -> str:
    """
    LLM 直接回答问题（不依赖文档上下文）
    用于知识库中找不到相关内容时的兜底回答
    """
    client = get_llm_client()
    logger.info("调用 LLM 直接回答: question=%s, history=%d, model=%s", question[:80], len(history or []), settings.llm_model_name)

    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "你是一个友好、专业的 AI 助手。"
                "请根据你的知识直接回答用户的问题。"
                "如果问题超出你的知识范围，请诚实告知用户。"
                "回答请使用中文，简洁明了。"
            ),
        },
    ]

    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": question.strip()})

    completion = client.chat.completions.create(
        model=settings.llm_model_name,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        messages=messages,
    )
    content = _normalize_text(completion.choices[0].message.content if completion.choices else "")
    logger.info("LLM 返回内容长度: %d 字符", len(content))
    if not content:
        raise LlmUnavailableError("LLM 未返回有效内容")
    return content


def generate_follow_up_suggestions(question: str, answer: str) -> list[str]:
    """根据用户问题和助手回答，生成 3 个追问建议。"""
    client = get_llm_client()
    logger.info("调用 LLM 生成追问建议: question=%s", question[:80])

    completion = client.chat.completions.create(
        model=settings.llm_model_name,
        temperature=0.8,
        max_tokens=300,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是知识库问答助手的追问建议生成器。"
                    "根据用户的问题和助手的回答，生成 3 个用户可能想继续追问的简短问题。"
                    "要求：\n"
                    "1. 每个问题不超过 20 个字\n"
                    "2. 问题必须与当前话题相关且有实际价值\n"
                    "3. 不要重复用户已问过的问题\n"
                    "4. 只输出 3 行问题文本，每行一个问题，不要编号、不要加引号、不要其他说明"
                ),
            },
            {
                "role": "user",
                "content": f"用户问题：{question.strip()}\n\n助手回答：{answer[:500]}",
            },
        ],
    )
    raw = completion.choices[0].message.content if completion.choices else ""
    suggestions = [line.strip() for line in raw.strip().split("\n") if line.strip()]
    return suggestions[:3]
