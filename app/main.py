# 创建 FastAPI 应用实例，注册路由，配置跨域（CORS）。等价于 NestJS 的 main.ts + AppModule。

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api import chat, rag, auth
from app.core.database import engine, Base

# lifespan 是新的生命周期管理方式
# yield 之前是启动时执行的代码，yield 之后是关闭时执行的代码
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：自动创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭时：可以在这里做清理工作（比如关闭数据库连接池）

app = FastAPI(title="Python AI Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(rag.router, prefix="/api", tags=["RAG"])

@app.get("/")
async def root():
    return {"status": "ok", "message": "服务正常运行"}