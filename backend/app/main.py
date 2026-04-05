# 创建 FastAPI 应用实例，注册路由，配置跨域（CORS）。等价于 NestJS 的 main.ts + AppModule。

import logging
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from app.api import chat, rag, auth, organization, knowledge
from app import models as app_models
from app.core.database import engine, Base

logger = logging.getLogger("uvicorn.error")

TAG_AUTH = "认证 Auth"
TAG_CHAT = "聊天 Chat"
TAG_RAG = "知识库 RAG"
TAG_ORG = "组织 Organization"
TAG_KB = "知识空间 Knowledge"

OPENAPI_TAGS = [
    {
        "name": TAG_AUTH,
        "description": "用户注册、登录与当前用户信息。 User registration, login, and profile endpoints.",
    },
    {
        "name": TAG_CHAT,
        "description": "对话与流式回复接口。 Chat and streaming response endpoints.",
    },
    {
        "name": TAG_RAG,
        "description": "知识库上传、检索与格式支持。 Knowledge base upload, query, and supported formats.",
    },
    {
        "name": TAG_ORG,
        "description": "部门、成员关系与加入申请审批。 Departments, memberships, and join request approvals.",
    },
    {
        "name": TAG_KB,
        "description": "知识库空间、文档归属与企业级上传入口。 Knowledge base spaces, document ownership, and governed upload endpoints.",
    },
]

SCALAR_JS_URL = "https://cdn.jsdelivr.net/npm/@scalar/api-reference"
SCALAR_TOKEN_STORAGE_KEY = "scalar_auth_token"

# lifespan 是新的生命周期管理方式
# yield 之前是启动时执行的代码，yield 之后是关闭时执行的代码
@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = app_models
    # 启动时：自动创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("API 文档已就绪: /docs")
    logger.info("本地访问地址: http://127.0.0.1:8000/docs 或 http://localhost:8000/docs")
    yield
    # 关闭时：可以在这里做清理工作（比如关闭数据库连接池）

app = FastAPI(
    title="Python AI Agent",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api", tags=[TAG_AUTH])
app.include_router(chat.router, prefix="/api", tags=[TAG_CHAT])
app.include_router(rag.router, prefix="/api", tags=[TAG_RAG])
app.include_router(organization.router, prefix="/api", tags=[TAG_ORG])
app.include_router(knowledge.router, prefix="/api", tags=[TAG_KB])

@app.get("/")
async def root():
    return {"status": "ok", "message": "服务正常运行"}


@app.get("/docs", include_in_schema=False)
async def scalar_docs() -> HTMLResponse:
    scalar_config = {
        "url": app.openapi_url,
        "theme": "default",
        "layout": "modern",
        "showSidebar": True,
        "hideDownloadButton": False,
        "hideTestRequestButton": False,
        "defaultOpenAllTags": False,
        "persistAuth": True,
        "operationTitleSource": "summary",
        "authentication": {
            "preferredSecurityScheme": "HTTPBearer",
            "securitySchemes": {
                "HTTPBearer": {
                    "token": "",
                }
            },
        },
        "agent": {"disabled": True},
    }
    config_json = json.dumps(scalar_config, ensure_ascii=False)
    html = f"""<!doctype html>
<html>
  <head>
    <title>{app.title} - API Reference</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      body {{
        margin: 0;
      }}

      .docs-auth-toolbar {{
        display: flex;
        justify-content: flex-end;
        width: 100%;
        margin: 16px 0 20px;
        z-index: 20;
        position: relative;
      }}

      .docs-auth-toolbar[data-mounted="false"] {{
        display: none;
      }}

      .docs-auth-card {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 10px;
        min-width: 220px;
        max-width: 260px;
        border: 1px solid #d9d3c7;
        border-radius: 10px;
        background: rgba(255, 252, 245, 0.96);
        box-shadow: 0 8px 22px rgba(62, 39, 14, 0.08);
        backdrop-filter: blur(10px);
        font: 12px/1.35 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}

      .docs-auth-status {{
        color: #5f574d;
        white-space: nowrap;
        flex: 1;
      }}

      .docs-auth-button {{
        border: 0;
        border-radius: 999px;
        background: #1f6f54;
        color: #fff;
        padding: 6px 10px;
        font: inherit;
        cursor: pointer;
      }}

      .docs-auth-button:disabled {{
        background: #b8b1a5;
        cursor: not-allowed;
      }}
    </style>
  </head>
  <body>
    <div id="app"></div>
    <div id="docs-auth-toolbar" class="docs-auth-toolbar" data-mounted="false">
      <div class="docs-auth-card">
        <span id="docs-auth-status" class="docs-auth-status">Token 未登录</span>
        <button id="docs-auth-button" type="button" class="docs-auth-button">清空 Token</button>
      </div>
    </div>
    <script>
      (function() {{
        const TOKEN_STORAGE_KEY = {json.dumps(SCALAR_TOKEN_STORAGE_KEY)};
        const LOGIN_PATHS = new Set(['/api/auth/login', '/api/auth/register']);
        const originalFetch = window.fetch.bind(window);
        const toolbar = document.getElementById('docs-auth-toolbar');
        const authStatus = document.getElementById('docs-auth-status');
        const authButton = document.getElementById('docs-auth-button');

        function getToken() {{
          return window.localStorage.getItem(TOKEN_STORAGE_KEY);
        }}

        function updateAuthToolbar() {{
          const hasToken = Boolean(getToken());
          authStatus.textContent = hasToken ? 'Token 已保存' : 'Token 未登录';
          authButton.textContent = hasToken ? '退出授权' : '清空 Token';
          authButton.disabled = !hasToken;
        }}

        function saveToken(token) {{
          if (token) {{
            window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
            updateAuthToolbar();
          }}
        }}

        function clearToken() {{
          window.localStorage.removeItem(TOKEN_STORAGE_KEY);
          updateAuthToolbar();
        }}

        function mountToolbar() {{
          if (!toolbar) {{
            return;
          }}

          const main = document.querySelector('#app main');
          if (!main) {{
            return;
          }}

          const introSection = main.querySelector('section');
          const mountTarget = introSection || main.firstElementChild || main;
          if (!mountTarget) {{
            return;
          }}

          if (toolbar.parentElement !== mountTarget) {{
            mountTarget.prepend(toolbar);
          }}
          toolbar.dataset.mounted = 'true';
        }}

        function resolvePath(input) {{
          try {{
            if (typeof input === 'string') {{
              return new URL(input, window.location.origin).pathname;
            }}
            if (input instanceof URL) {{
              return input.pathname;
            }}
            if (input && typeof input.url === 'string') {{
              return new URL(input.url, window.location.origin).pathname;
            }}
          }} catch (_error) {{
            return '';
          }}
          return '';
        }}

        window.fetch = async function(input, init) {{
          const path = resolvePath(input);
          const token = getToken();
          const request = new Request(input, init);

          if (token && path.startsWith('/api/')) {{
            request.headers.set('Authorization', `Bearer ${{token}}`);
          }}

          const response = await originalFetch(request);

          if (LOGIN_PATHS.has(path)) {{
            try {{
              const data = await response.clone().json();
              if (data && typeof data.access_token === 'string') {{
                saveToken(data.access_token);
              }}
            }} catch (_error) {{
            }}
          }}

          return response;
        }};

        authButton.addEventListener('click', function() {{
          clearToken();
          window.location.reload();
        }});

        updateAuthToolbar();
        mountToolbar();
        new MutationObserver(function() {{
          mountToolbar();
        }}).observe(document.body, {{ childList: true, subtree: true }});
      }})();
    </script>
    <script src="{SCALAR_JS_URL}"></script>
    <script>
      const rawConfig = {config_json};
      const tokenStorageKey = {json.dumps(SCALAR_TOKEN_STORAGE_KEY)};
      const savedToken = window.localStorage.getItem(tokenStorageKey);

      if (
        savedToken &&
        rawConfig.authentication &&
        rawConfig.authentication.securitySchemes &&
        rawConfig.authentication.securitySchemes.HTTPBearer &&
        rawConfig.authentication.securitySchemes.HTTPBearer.token
      ) {{
        rawConfig.authentication.securitySchemes.HTTPBearer.token = savedToken;
      }}

      Scalar.createApiReference('#app', rawConfig);
    </script>
  </body>
</html>"""
    return HTMLResponse(html)
