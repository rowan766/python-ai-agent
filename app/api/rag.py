# RAG 功能的路由入口，现在先放健康检查，后面再填充实际逻辑。

from fastapi import APIRouter

router = APIRouter()

@router.get("/rag/health")
async def rag_health():
    return {"status": "ok", "message": "RAG 接口待实现"}