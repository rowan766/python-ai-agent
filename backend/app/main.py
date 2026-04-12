from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from scalar_fastapi import get_scalar_api_reference

from app.api.auth import router as auth_router
from app.api.departments import router as department_router
from app.api.documents import router as document_router
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
from app.services.qdrant_vector_store import QdrantUnavailableError, ensure_qdrant_collection
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
    {"name": "文档处理", "description": "文档入队、任务状态与切片结果接口"},
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
    with SessionLocal() as db:
        seed_database(db)
    docs_url = f"http://127.0.0.1:{settings.app_port}/docs"
    logger.info("后端已启动，Scalar 文档地址: %s", docs_url)
    print(f"后端已启动，Scalar 文档地址: {docs_url}")
    print(f"MinIO 控制台地址: {settings.minio_console_url}")
    if settings.document_processing_mode == "worker":
        print("文档处理模式: worker，请单独启动文档处理 Worker")
    print(f"Qdrant 地址: {settings.qdrant_url}")
    if qdrant_ready:
        print("Qdrant 状态: 已连接，可进行向量写入与检索")
    else:
        print("Qdrant 状态: 未连接，后端可正常运行，但向量检索暂不可用")
    yield


app = FastAPI(
    title=settings.app_name,
    description="""
## 接口调试说明

本项目使用 Bearer Token 鉴权，前端联调请按下面步骤操作：

1. 先调用 `GET /auth/captcha` 获取验证码。
2. 再调用 `POST /auth/login`，成功后从响应体 `data.access_token` 中复制 token。
3. 打开本文档顶部 `Introduction` 区域中的 `Authentication` 卡片，选择 `HTTPBearer`。
4. 将登录拿到的 `access_token` 填入后保存。
5. 随后再测试需要登录的接口，文档会自动附加 `Authorization: Bearer <token>` 请求头。
6. 在文档里调 `GET /auth/captcha` 后，页面右下角会自动弹出验证码预览，可直接照着填写 `captchaCode`。

说明：

- 文档里的 `username`、`password`、`captchaId` 这类字段名是接口真实参数名，不会改成中文。
- 中文内容体现在参数标题、参数说明、响应模型说明中。
""",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_tags=openapi_tags,
)

DOCS_CAPTCHA_PANEL_HTML = """
<div id="scalar-captcha-panel" aria-live="polite" hidden>
  <div class="scalar-captcha-panel__header">
    <div>
      <div class="scalar-captcha-panel__title">验证码预览</div>
      <div class="scalar-captcha-panel__desc">调用 <code>GET /auth/captcha</code> 后，最新验证码会显示在这里，方便继续调登录接口。</div>
    </div>
    <button id="scalar-captcha-close" type="button" aria-label="关闭验证码预览">×</button>
  </div>
  <div class="scalar-captcha-panel__image-wrap">
    <img id="scalar-captcha-image" alt="验证码预览" />
  </div>
  <div id="scalar-captcha-id" class="scalar-captcha-panel__meta"></div>
  <div class="scalar-captcha-panel__hint">登录时把上面图片里的字符填到 <code>captchaCode</code>，把返回的 <code>captchaId</code> 填到登录参数中。</div>
</div>
"""

DOCS_CAPTCHA_PANEL_SCRIPT = """
<script>
(() => {
  const CAPTCHA_PANEL_ID = 'scalar-captcha-panel';
  const CAPTCHA_IMAGE_ID = 'scalar-captcha-image';
  const CAPTCHA_META_ID = 'scalar-captcha-id';

  const isCaptchaRequest = (rawUrl) => {
    try {
      const url = new URL(rawUrl, window.location.origin);
      return url.origin === window.location.origin && url.pathname === '/auth/captcha';
    } catch {
      return false;
    }
  };

  const showCaptchaPanel = (payload) => {
    const panel = document.getElementById(CAPTCHA_PANEL_ID);
    const image = document.getElementById(CAPTCHA_IMAGE_ID);
    const meta = document.getElementById(CAPTCHA_META_ID);
    if (!panel || !image || !meta) return;

    const data = payload?.data ?? {};
    const captchaId = data.captchaId || '';
    const svg = data.captchaSvg || '';
    if (!captchaId || !svg) return;

    image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
    meta.textContent = `captchaId: ${captchaId}`;
    panel.hidden = false;
  };

  const tryHandleCaptchaResponse = async (rawUrl, response) => {
    if (!isCaptchaRequest(rawUrl)) return;
    try {
      const cloned = response.clone();
      const contentType = cloned.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) return;
      const payload = await cloned.json();
      showCaptchaPanel(payload);
    } catch {}
  };

  const mountPanelEvents = () => {
    const closeButton = document.getElementById('scalar-captcha-close');
    const panel = document.getElementById(CAPTCHA_PANEL_ID);
    if (!closeButton || !panel) return;
    closeButton.addEventListener('click', () => {
      panel.hidden = true;
    });
  };

  const patchFetch = () => {
    if (window.__scalarCaptchaFetchPatched) return;
    window.__scalarCaptchaFetchPatched = true;
    const originalFetch = window.fetch.bind(window);

    window.fetch = async (input, init) => {
      const requestUrl = typeof input === 'string' ? input : input instanceof Request ? input.url : String(input);
      const response = await originalFetch(input, init);
      await tryHandleCaptchaResponse(requestUrl, response);
      return response;
    };
  };

  const patchXHR = () => {
    if (window.__scalarCaptchaXHRPatched) return;
    window.__scalarCaptchaXHRPatched = true;

    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
      this.__scalarDocsUrl = url;
      return originalOpen.call(this, method, url, ...rest);
    };

    XMLHttpRequest.prototype.send = function(body) {
      this.addEventListener('load', () => {
        if (!isCaptchaRequest(this.__scalarDocsUrl || '')) return;
        try {
          const contentType = this.getResponseHeader('content-type') || '';
          if (!contentType.includes('application/json')) return;
          showCaptchaPanel(JSON.parse(this.responseText));
        } catch {}
      }, { once: true });
      return originalSend.call(this, body);
    };
  };

  const init = () => {
    mountPanelEvents();
    patchFetch();
    patchXHR();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
</script>
"""

DOCS_CAPTCHA_PANEL_STYLE = """
<style>
#scalar-captcha-panel {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 9999;
  width: min(420px, calc(100vw - 32px));
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 12px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(10px);
  padding: 14px;
  color: #0f172a;
  font-family: Inter, system-ui, sans-serif;
}

#scalar-captcha-panel code {
  font-family: "JetBrains Mono", Consolas, monospace;
}

.scalar-captcha-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.scalar-captcha-panel__title {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 4px;
}

.scalar-captcha-panel__desc {
  font-size: 13px;
  line-height: 1.5;
  color: #475569;
}

#scalar-captcha-close {
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}

.scalar-captcha-panel__image-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 72px;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
}

.scalar-captcha-panel__image-wrap img {
  max-width: 100%;
  height: auto;
  display: block;
}

.scalar-captcha-panel__meta {
  font-size: 12px;
  color: #0f172a;
  font-family: "JetBrains Mono", Consolas, monospace;
  margin-bottom: 8px;
}

.scalar-captcha-panel__hint {
  font-size: 12px;
  line-height: 1.5;
  color: #334155;
}
</style>
"""


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
        f"{DOCS_CAPTCHA_PANEL_HTML}{DOCS_CAPTCHA_PANEL_STYLE}{DOCS_CAPTCHA_PANEL_SCRIPT}</body>",
    )
    return HTMLResponse(html)


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(role_router)
app.include_router(menu_router)
app.include_router(department_router)
app.include_router(dict_type_router)
app.include_router(dict_data_router)
app.include_router(upload_router)
app.include_router(document_router)
