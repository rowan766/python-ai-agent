from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference

from app.api.auth import router as auth_router
from app.api.departments import router as department_router
from app.api.dicts import data_router as dict_data_router
from app.api.dicts import type_router as dict_type_router
from app.api.menus import router as menu_router
from app.api.roles import router as role_router
from app.api.uploads import router as upload_router
from app.api.users import router as user_router
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.redis_client import get_redis_client
from app.services.object_storage import ensure_minio_bucket
from app.services.seed import seed_database


settings = get_settings()
logger = logging.getLogger("app.startup")
openapi_tags = [
    {"name": "认证管理", "description": "登录、退出与验证码接口"},
    {"name": "用户管理", "description": "用户列表、个人中心、角色分配等接口"},
    {"name": "角色管理", "description": "角色维护、菜单授权与数据权限接口"},
    {"name": "菜单管理", "description": "动态路由菜单与按钮权限接口"},
    {"name": "部门管理", "description": "部门树维护接口"},
    {"name": "数据字典", "description": "字典类型与字典数据接口"},
    {"name": "文件上传", "description": "图片、文件上传与下载接口"},
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.database_file_path:
        settings.database_file_path.parent.mkdir(parents=True, exist_ok=True)
    get_redis_client().ping()
    ensure_minio_bucket()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    docs_url = f"http://127.0.0.1:{settings.app_port}/docs"
    logger.info("后端已启动，Scalar 文档地址: %s", docs_url)
    print(f"后端已启动，Scalar 文档地址: {docs_url}")
    print(f"MinIO 控制台地址: {settings.minio_console_url}")
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": str(exc) or "服务器内部错误", "data": None},
    )


@app.get("/", summary="系统根路径")
def root() -> dict:
    return {"name": settings.app_name, "status": "ok"}


@app.get("/health", summary="健康检查")
def health() -> dict:
    return {"status": "ok"}


@app.get("/docs", include_in_schema=False)
def scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=f"{settings.app_name} - Scalar API Reference",
    )


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(role_router)
app.include_router(menu_router)
app.include_router(department_router)
app.include_router(dict_type_router)
app.include_router(dict_data_router)
app.include_router(upload_router)
