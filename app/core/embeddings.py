from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)


def embed_text(text: str) -> list[float]:
    """将单段文本转为向量，拒绝空白输入。"""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("文档内容为空，无法生成向量")

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text.strip(),
    )
    return response.data[0].embedding


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量将文本转为向量，并过滤空白文本。"""
    cleaned_texts = [text.strip() for text in texts if isinstance(text, str) and text.strip()]
    if not cleaned_texts:
        raise ValueError("没有可用于向量化的文档内容")

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=cleaned_texts,
    )
    return [item.embedding for item in response.data]
