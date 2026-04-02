# RAG 功能的路由入口

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from app.core.rag.loader import load_documents, get_supported_formats
from app.core.rag.indexer import index_documents
from app.core.rag.retriever import retrieve_documents
import shutil
from pathlib import Path
import os

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/rag/upload")
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

@router.post("/rag/query")
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

@router.get("/rag/supported-formats")
async def supported_formats():
    """返回当前支持的文件格式列表"""
    return {"supported_formats": get_supported_formats()}
