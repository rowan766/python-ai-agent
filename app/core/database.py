# 创建异步数据库连接，相当于 NestJS 里的 TypeORM 配置

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

# 创建异步数据库引擎
engine = create_async_engine(DATABASE_URL, echo=False)

# 创建 Session 工厂（相当于 NestJS 的 Repository 注入）
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# 所有数据库模型的基类
class Base(DeclarativeBase):
    pass

# FastAPI 依赖注入用的函数，每个请求创建一个 Session，请求结束后自动关闭
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()