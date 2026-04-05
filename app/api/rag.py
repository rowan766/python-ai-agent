# RAG 功能的路由入口

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from app.core.rag.loader import load_documents, get_supported_formats
from app.core.rag.indexer import index_documents
from app.core.rag.retriever import retrieve_documents
from app.core.embeddings import embed_text, EMBEDDING_MODEL, client as embedding_client
from app.core.llm import client as llm_client, DEFAULT_MODEL
import shutil
from pathlib import Path
import os

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post(
    "/rag/upload",
    summary="上传文档 Upload",
    description="上传文件并完成解析、切分、向量化与入库。 Upload a file, then parse, chunk, embed, and index it.",
)
async def upload_and_index(file: UploadFile = File(...)):
    """
    上传文档 → 自动解析 → 切分 → 向量化 → 存入知识库
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="没有文件")
    
    # 保存临时文件
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # 1. 加载并切分文档
        docs = load_documents(str(file_path))
        if not docs:
            raise HTTPException(
                status_code=400,
                detail="文档解析后没有可用文本内容，请检查文件是否为空，或文件编码是否正确"
            )
        
        # 2. 存入向量数据库
        count = index_documents(docs)
        
        return JSONResponse(content={
            "status": "success",
            "filename": file.filename,
            "chunks": count,
            "message": f"成功索引 {count} 个文档片段"
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理临时文件
        if file_path.exists():
            file_path.unlink()

@router.post(
    "/rag/query",
    summary="知识库检索 Query",
    description="输入问题后返回知识库中最相关的结果片段。 Query the knowledge base and return the most relevant chunks.",
)
async def rag_query(query: str, limit: int = 5):
    """
    直接输入问题，返回知识库中最相关的答案片段
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="查询不能为空")

    docs = retrieve_documents(query, limit)

    return {
        "query": query,
        "results": docs,
        "count": len(docs)
    }

@router.get(
    "/rag/supported-formats",
    summary="支持格式 Supported Formats",
    description="返回当前支持上传和解析的文件格式。 Return the file formats currently supported for upload and parsing.",
)
async def supported_formats():
    """返回当前支持的文件格式列表"""
    return {"supported_formats": get_supported_formats()}


@router.get(
    "/rag/debug/embedding",
    summary="Embedding 健康检查 Embedding Health Check",
    description="检查当前 embedding 模型是否可用，并返回模型名、Base URL、向量维度和调用状态。 Check embedding availability and return model, base URL, vector dimensions, and status.",
)
async def embedding_health_check(
    text: str = Query(
        default="embedding health check",
        description="用于生成测试向量的文本。 Sample text used to generate a test embedding.",
    ),
):
    """检查 embedding 服务连通性与当前模型配置。"""
    sample_text = text.strip() if isinstance(text, str) else ""
    if not sample_text:
        raise HTTPException(status_code=400, detail="测试文本不能为空")

    base_url = str(getattr(embedding_client, "base_url", "")).rstrip("/")

    try:
        vector = embed_text(sample_text)
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "embedding_model": EMBEDDING_MODEL,
                "base_url": base_url,
                "sample_text": sample_text,
                "error": str(exc),
            },
        )

    return {
        "status": "ok",
        "embedding_model": EMBEDDING_MODEL,
        "base_url": base_url,
        "sample_text": sample_text,
        "dimensions": len(vector),
        "vector_preview": vector[:5],
    }


@router.get(
    "/rag/debug/chat",
    summary="聊天模型健康检查 Chat Model Health Check",
    description="检查当前聊天模型是否可用，并返回模型名、Base URL、首段回复和调用状态。 Check chat model availability and return model, base URL, first response text, and status.",
)
async def chat_health_check(
    prompt: str = Query(
        default="请回复: chat health ok",
        description="用于测试聊天模型的提示词。 Prompt used to test the chat model.",
    ),
    model: str = Query(
        default=DEFAULT_MODEL,
        description="要测试的聊天模型名称。 Chat model name to test.",
    ),
):
    """检查聊天模型服务连通性与当前模型配置。"""
    sample_prompt = prompt.strip() if isinstance(prompt, str) else "请回复: chat health ok"
    sample_model = model.strip() if isinstance(model, str) else DEFAULT_MODEL

    if not sample_prompt:
        raise HTTPException(status_code=400, detail="测试提示词不能为空")
    if not sample_model:
        raise HTTPException(status_code=400, detail="模型名称不能为空")

    base_url = str(getattr(llm_client, "base_url", "")).rstrip("/")

    try:
        response = await llm_client.chat.completions.create(
            model=sample_model,
            messages=[{"role": "user", "content": sample_prompt}],
            stream=False,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "chat_model": sample_model,
                "base_url": base_url,
                "prompt": sample_prompt,
                "error": str(exc),
            },
        )

    message = ""
    if response.choices and response.choices[0].message:
        message = response.choices[0].message.content or ""

    return {
        "status": "ok",
        "chat_model": sample_model,
        "base_url": base_url,
        "prompt": sample_prompt,
        "response_preview": message,
    }
