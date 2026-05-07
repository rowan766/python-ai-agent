import asyncio
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from scalar_fastapi import get_scalar_api_reference

from app.api.auth import router as auth_router
from app.api.departments import router as department_router
from app.api.documents import router as document_router
from app.api.dicts import data_router as dict_data_router
from app.api.dicts import type_router as dict_type_router
from app.api.knowledge_spaces import router as knowledge_space_router
from app.api.menus import router as menu_router
from app.api.roles import router as role_router
from app.api.uploads import router as upload_router
from app.api.users import router as user_router
from app.api.ws import router as ws_router, start_redis_subscriber
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.schema_sync import ensure_runtime_schema
from app.core.redis_client import get_redis_client
from app.services.document_processor import get_ocr_engine
from app.services.object_storage import ensure_minio_bucket
from app.services.qdrant_vector_store import QdrantUnavailableError, ensure_qdrant_collection
from app.services.seed import seed_database

from app.scripts.docs_ui import (
    DOCS_CAPTCHA_PANEL_HTML,
    DOCS_CAPTCHA_PANEL_SCRIPT,
    DOCS_CAPTCHA_PANEL_STYLE,
    DOCS_DOWNLOAD_BTN_HTML,
)
from app.scripts.docs_generator import build_api_docs_md


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
    {"name": "文档处理", "description": "文档入队、任务状态、切片检索与 RAG 问答接口"},
    {"name": "知识空间", "description": "知识空间列表、创建、详情与更新接口"},
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.database_file_path:
        settings.database_file_path.parent.mkdir(parents=True, exist_ok=True)
    get_redis_client().ping()
    ensure_minio_bucket()
    qdrant_ready = False
    try:
        qdrant_ready = ensure_qdrant_collection()
    except QdrantUnavailableError as exc:
        logger.warning("Qdrant 初始化跳过: %s", exc)
        print(f"Qdrant 初始化跳过: {exc}")
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    with SessionLocal() as db:
        seed_database(db)
    docs_url = f"http://127.0.0.1:{settings.app_port}/docs"
    logger.info("后端已启动，Scalar 文档地址: %s", docs_url)
    print(f"后端已启动，Scalar 文档地址: {docs_url}")
    print(f"MinIO 控制台地址: {settings.minio_console_url}")
    if settings.document_processing_mode == "worker":
        print("文档处理模式: worker，请单独启动文档处理 Worker")
    print(f"Qdrant 地址: {settings.qdrant_url}")
    print(f"Embedding 模型: {settings.embedding_provider} / {settings.embedding_model_name}")
    if settings.llm_enabled:
        print(f"LLM 模型: {settings.llm_provider} / {settings.llm_model_name}")
    else:
        print("LLM 状态: 未配置 API Key，文档问答将回退为检索摘要模式")
    if qdrant_ready:
        print("Qdrant 状态: 已连接，可进行向量写入与检索")
    else:
        print("Qdrant 状态: 未连接，后端可正常运行，但向量检索暂不可用")

    subscriber_task = asyncio.create_task(start_redis_subscriber())
    yield
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass
    get_ocr_engine.cache_clear()


app = FastAPI(
    title=settings.app_name,
    description="""
## 接口调试说明

本项目使用 Bearer Token 鉴权，前端联调请按下面步骤操作：

1. 先调用 `GET /auth/captcha` 获取验证码。
2. 再调用 `POST /auth/login`，成功后从响应体 `data.access_token` 中复制 token。
3. 打开本文档顶部 `Introduction` 区域中的 `Authentication` 卡片，选择 `HTTPBearer`。
4. 将登录拿到的 `access_token` 填入后保存。
5. 随后再测试需要token的其他接口，文档会自动附加 `Authorization: Bearer <token>` 请求头。
6. 在文档里调 `GET /auth/captcha` 后，页面右下角会自动弹出验证码预览，可直接照着填写 `captchaCode和captchaId`。
""",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_tags=openapi_tags,
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    schema["security"] = [{"HTTPBearer": []}]
    app.openapi_schema = schema
    return app.openapi_schema


@app.get("/docs/download", include_in_schema=False)
def api_docs_download(format: str = "md"):
    md_text = build_api_docs_md(app.openapi_schema)
    if format == "md":
        return Response(
            content=md_text,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=\"api-reference.md\""},
        )
    return JSONResponse({"error": "Unsupported format"}, status_code=400)


app.openapi = custom_openapi

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


@app.get("/", summary="系统根路径", openapi_extra={"security": []})
def root() -> dict:
    return {"name": settings.app_name, "status": "ok"}


@app.get("/health", summary="健康检查", openapi_extra={"security": []})
def health() -> dict:
    return {"status": "ok"}


@app.get("/docs", include_in_schema=False)
def scalar_docs():
    response = get_scalar_api_reference(
        content=app.openapi(),
        title=f"{settings.app_name} - Scalar API Reference",
        hide_test_request_button=False,
        hide_client_button=False,
        persist_auth=True,
        default_open_all_tags=True,
        expand_all_model_sections=True,
        expand_all_responses=True,
        order_schema_properties_by="preserve",
        authentication={
            "preferredSecurityScheme": "HTTPBearer",
            "createAnySecurityScheme": True,
            "securitySchemes": {
                "HTTPBearer": {},
            },
        },
    )
    html = response.body.decode("utf-8")
    html = html.replace(
        "</body>",
        f"{DOCS_DOWNLOAD_BTN_HTML}{DOCS_CAPTCHA_PANEL_HTML}{DOCS_CAPTCHA_PANEL_STYLE}{DOCS_CAPTCHA_PANEL_SCRIPT}</body>",
    )
    return HTMLResponse(html)


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(role_router)
app.include_router(menu_router)
app.include_router(department_router)
app.include_router(dict_type_router)
app.include_router(dict_data_router)
app.include_router(knowledge_space_router)
app.include_router(upload_router)
app.include_router(document_router)
app.include_router(ws_router)
