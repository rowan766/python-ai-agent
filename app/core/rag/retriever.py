from qdrant_client import QdrantClient
from dotenv import load_dotenv
import os
from pathlib import Path
from app.core.embeddings import embed_text

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env")

client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)

COLLECTION_NAME = "knowledge_base"

def retrieve_documents(query: str, limit: int = 5):
    """
    根据用户查询进行向量检索，返回最相关的文档片段
    """
    # 把查询文本转为向量
    query_vector = embed_text(query)
    
    # 执行相似度搜索
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        with_payload=True,
        score_threshold=0.6   # 只返回相似度足够高的结果
    )
    
    # 提取内容
    documents = []
    for scored_point in response.points:
        documents.append({
            "content": scored_point.payload["page_content"],
            "score": scored_point.score,
            "metadata": scored_point.payload.get("metadata", {})
        })
    
    return documents
