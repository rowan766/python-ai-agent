from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv
import os
from pathlib import Path
from uuid import uuid4
from app.core.embeddings import embed_texts

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env")

client = QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"), 
                     port=int(os.getenv("QDRANT_PORT", 6333)))

COLLECTION_NAME = "knowledge_base"

def ensure_collection():
    """确保向量集合存在"""
    collections = client.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
        )

def index_documents(docs, collection_name: str = COLLECTION_NAME):
    """将文档向量化并存入 Qdrant"""
    valid_docs = [doc for doc in docs if isinstance(doc.page_content, str) and doc.page_content.strip()]
    if not valid_docs:
        raise ValueError("文档解析后没有可用文本内容，请检查文件是否为空，或文件编码是否正确")

    ensure_collection()
    vectors = embed_texts([doc.page_content for doc in valid_docs])

    points = []
    for doc, vector in zip(valid_docs, vectors):
        points.append(PointStruct(
            id=uuid4().hex,
            vector=vector,
            payload={
                "page_content": doc.page_content,
                "metadata": doc.metadata
            }
        ))

    client.upsert(collection_name=collection_name, points=points)
    return len(points)
