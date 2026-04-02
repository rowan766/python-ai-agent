# 创建 FastAPI 应用实例，注册路由，配置跨域（CORS）。等价于 NestJS 的 main.ts + AppModule。

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, rag

app = FastAPI(
    title="Python AI Agent",
    description="聊天工具 + 企业级 RAG",
    version="0.1.0"
)

# 跨域配置，开发阶段允许所有来源
# 作用：让你的前端（React/Vue）能访问这个后端接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由，prefix 相当于 NestJS 的 Controller 路径前缀
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(rag.router, prefix="/api", tags=["RAG"])

@app.get("/")
async def root():
    return {"status": "ok", "message": "服务正常运行"}