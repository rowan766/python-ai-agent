# 企业级 RAG 知识管理平台

> 基于 FastAPI + Vue 3 构建的企业级知识库系统，集成文档处理、向量检索与大语言模型问答能力，支持细粒度知识空间权限管控。

---

## 功能特性

### 知识管理
- **知识空间**：多租户隔离的知识库单元，支持私有、部门、部门树、共享、全体成员五种可见性模式
- **文档处理**：支持 TXT / MD / CSV / JSON / YAML / XML / HTML / PDF / 图片（OCR）等多种格式
- **智能分块**：自动文本提取 → 语义分块 → Embedding → 向量入库全链路
- **混合检索**：向量相似度 + 关键词双引擎，支持精确匹配加权与相关度阈值过滤
- **AI 问答**：基于 RAG 的上下文问答，精准引用文档片段生成结构化答案

### 权限体系
- **平台 RBAC**：用户 → 角色 → 菜单/按钮权限，支持动态菜单与操作级按钮鉴权
- **数据范围**：全部 / 本部门 / 本部门及下属 / 仅本人，四档数据隔离
- **知识空间 ACL**：Owner / Manager / Editor / Viewer 四级空间角色，支持按部门、角色、用户精细共享
- **Token 黑名单**：退出登录即时失效，基于 Redis TTL 自动过期

### 基础设施
- **对象存储**：MinIO 管理原始文件，支持文件上传、下载、预览
- **异步任务**：文档处理独立 Worker，Redis 队列驱动，主进程零阻塞
- **向量数据库**：Qdrant 存储与检索文档 Embedding
- **图片验证码**：SVG 验证码 + Redis 短 TTL，防暴力登录

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3 · Vite · Element Plus · Pinia · Vue Router · Axios |
| **后端** | FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Python 3.11 |
| **数据库** | PostgreSQL 16 · Redis 7 |
| **存储 / 向量** | MinIO · Qdrant |
| **Embedding** | fastembed（CPU）/ Ollama（GPU 可选） |
| **LLM** | 阿里云 DashScope Qwen / Ollama 本地（可选） |
| **容器** | Docker Compose |

---

## 项目结构

```
python-ai-agent/
├── backend/
│   ├── app/
│   │   ├── api/                # 路由层
│   │   │   ├── auth.py         # 登录、验证码、登出
│   │   │   ├── users.py        # 用户 CRUD
│   │   │   ├── roles.py        # 角色管理
│   │   │   ├── menus.py        # 动态菜单与按钮权限
│   │   │   ├── departments.py  # 部门树
│   │   │   ├── dicts.py        # 数据字典
│   │   │   ├── uploads.py      # 文件上传 / 下载
│   │   │   ├── documents.py    # 文档处理与 RAG 问答
│   │   │   └── knowledge_spaces.py  # 知识空间管理
│   │   ├── core/               # 基础设施
│   │   │   ├── config.py       # 配置（从 .env 加载）
│   │   │   ├── database.py     # SQLAlchemy 连接
│   │   │   ├── security.py     # JWT & 密码哈希
│   │   │   ├── deps.py         # FastAPI 依赖注入
│   │   │   ├── redis_client.py # Redis 连接
│   │   │   └── captcha.py      # 验证码生成
│   │   ├── services/           # 业务逻辑层
│   │   │   ├── document_processor.py       # 文本提取 / OCR / 分块
│   │   │   ├── document_queue.py           # Redis 任务队列
│   │   │   ├── embedding.py                # fastembed / Ollama Embedding
│   │   │   ├── qdrant_vector_store.py      # 向量库操作
│   │   │   ├── rag_retrieval.py            # 混合检索
│   │   │   ├── rag_answer.py               # LLM 问答生成
│   │   │   ├── llm_service.py              # OpenAI 兼容客户端
│   │   │   ├── object_storage.py           # MinIO 操作
│   │   │   ├── knowledge_space_permissions.py  # 空间 ACL
│   │   │   └── document_permissions.py     # 文档权限过滤
│   │   ├── workers/
│   │   │   └── document_worker.py          # 文档处理后台进程
│   │   ├── models.py           # SQLAlchemy 数据模型
│   │   ├── schemas.py          # Pydantic 数据结构
│   │   └── main.py             # FastAPI 入口
│   ├── .env.example
│   ├── requirements.txt
│   └── start-backend.ps1
├── frontend/
│   └── src/
│       ├── api/                # 接口请求
│       ├── layout/             # 整体布局（侧边栏 / Header / Tab）
│       ├── router/             # 路由与动态菜单
│       ├── stores/             # Pinia 状态
│       └── views/              # 页面组件
├── docker-compose.yml
├── start-dev.ps1               # 一键本地开发启动脚本
└── 部署方案.md                  # Ollama 本地 GPU 部署方案
```

---

## 快速启动

### 环境要求

- Python **3.11**（fastembed / onnxruntime 稳定性要求）
- Node.js **20+**
- Docker Desktop

### 推荐开发模式（基础设施容器 + 本地前后端）

**步骤 1：启动基础服务**

```powershell
docker compose up -d postgres redis minio qdrant document-worker
```

**步骤 2：初始化后端依赖（仅首次）**

```powershell
cd backend
uv venv --python 3.11 .venv-fastapi311
uv pip install --python .venv-fastapi311\Scripts\python.exe -r requirements.txt
```

**步骤 3：配置环境变量**

```powershell
cp backend/.env.example backend/.env
# 编辑 backend/.env，填写 SECRET_KEY 和其他配置
```

**步骤 4：启动后端**

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\start-backend.ps1
```

后端启动时会自动完成：建表、初始化种子数据、检查 Redis、创建 MinIO Bucket。

**步骤 5：启动前端**

```powershell
cd frontend
pnpm install   # 仅首次
pnpm dev
```

### 一键启动脚本

```powershell
# 推荐：基础设施容器 + 本地前后端
powershell -ExecutionPolicy Bypass -File .\start-dev.ps1 -Mode local

# 全容器模式
powershell -ExecutionPolicy Bypass -File .\start-dev.ps1 -Mode compose

# 预览将执行的命令（不实际启动）
powershell -ExecutionPolicy Bypass -File .\start-dev.ps1 -Mode local -DryRun
```

---

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端管理界面 | http://127.0.0.1:5173 |
| 后端 API 文档 | http://127.0.0.1:3101/docs |
| MinIO 控制台 | http://127.0.0.1:9001 |
| Qdrant Dashboard | http://127.0.0.1:6333/dashboard |

**默认账号**

| 系统 | 账号 | 密码 |
|------|------|------|
| 管理后台 | `admin` | `123456` |
| MinIO | `minioadmin` | `minioadmin` |

---

## 配置说明

配置文件位于 `backend/.env`，参考 `backend/.env.example`。

### 核心配置

```env
# 应用
APP_NAME=企业知识库RAG系统
SECRET_KEY=请替换为至少32位随机字符串

# 数据库（本地开发端口 5433，容器内 5432）
DATABASE_URL=postgresql+psycopg://admin:password123@localhost:5433/admin_system

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=admin-system

# Qdrant
QDRANT_URL=http://127.0.0.1:6333

# 跨域
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### LLM 配置

**方案 A：阿里云 DashScope（默认，无需 GPU）**

```env
LLM_PROVIDER=dashscope
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
LLM_MODEL_NAME=qwen-plus
```

> 不配置 `LLM_API_KEY` 时，系统自动降级为"检索摘要"模式，问答功能仍可使用，但无 LLM 生成。

**方案 B：Ollama 本地 GPU（数据不出内网）**

```env
LLM_PROVIDER=ollama
LLM_MODEL_NAME=qwen2.5:14b
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL_NAME=mxbai-embed-large
EMBEDDING_VECTOR_SIZE=1024
```

详细的 Ollama 部署步骤见 [部署方案.md](./部署方案.md)。

### Embedding 配置

```env
# 默认：fastembed 本地 CPU（无需 GPU）
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_VECTOR_SIZE=384
EMBEDDING_FALLBACK_TO_HASH=true
```

> 切换 Embedding 模型后，旧向量与新模型不兼容，需清空 Qdrant collection 并重新处理所有文档。

### RAG 调优参数

```env
RAG_ANSWER_MAX_CHUNKS=4           # 传入 LLM 的最大 chunk 数
RAG_ANSWER_MAX_CONTEXT_CHARS=2400 # 上下文最大字符数
RETRIEVAL_RELEVANCE_THRESHOLD=0.3 # 相关度阈值（0~1）
LLM_MAX_TOKENS=900
LLM_TEMPERATURE=0.2
LLM_TIMEOUT_SECONDS=120
```

---

## 文档处理流程

```
用户上传文件
     │
     ▼
MinIO 存储原始文件 ──► PostgreSQL 创建文档记录
     │
     ▼
Redis 任务队列（document-worker 消费）
     │
     ▼
文本提取 / OCR（PDF / 图片 / 扫描版 PDF 自动回退）
     │
     ▼
语义分块（chunk_size=800, overlap=120）
     │
     ▼
Embedding 向量化（fastembed CPU / Ollama GPU）
     │
     ▼
Qdrant 向量写入 + PostgreSQL chunk 元数据写入
```

**支持格式**

| 类型 | 格式 |
|------|------|
| 文本 | txt · md · csv · json · yaml · xml · html |
| 文档 | pdf（原生文本 + 扫描 OCR 回退） |
| 图片 | png · jpg · jpeg · bmp · gif · webp · tif · tiff |

---

## 知识空间权限模型

### 可见性模式

| 模式 | 说明 |
|------|------|
| `private` | 仅知识空间成员可见 |
| `department` | 仅归属部门成员可见 |
| `department_tree` | 归属部门及所有下属部门成员可见 |
| `shared` | 按共享配置（部门 / 角色 / 用户）可见 |
| `all` | 全体成员可见 |

### 空间角色权限

| 角色 | read | write | manage | share |
|------|:----:|:-----:|:------:|:-----:|
| owner | ✓ | ✓ | ✓ | ✓ |
| manager | ✓ | ✓ | ✓ | ✓ |
| editor | ✓ | ✓ | | |
| viewer | ✓ | | | |

---

## Docker 服务说明

```yaml
# docker-compose.yml 包含以下服务
postgres:        # PostgreSQL 16，端口 5433
redis:           # Redis 7，端口 6379
minio:           # MinIO，API 9000 / Console 9001
qdrant:          # Qdrant，HTTP 6333 / gRPC 6334
backend:         # FastAPI 后端，端口 3101
document-worker: # 文档处理 Worker（独立进程）
```

**仅启动基础依赖（本地开发推荐）：**

```powershell
docker compose up -d postgres redis minio qdrant document-worker
```

**启动全部服务：**

```powershell
docker compose up -d
```

---

## 生产部署 Checklist

- [ ] `SECRET_KEY` 替换为随机字符串（`openssl rand -hex 32`）
- [ ] PostgreSQL / MinIO 密码修改为强密码
- [ ] `ALLOWED_ORIGINS` 只保留生产域名
- [ ] Qdrant / MinIO 控制台端口不对外暴露（防火墙封掉 6333、9001）
- [ ] 开启 HTTPS（Nginx + Let's Encrypt）
- [ ] `EMBEDDING_FALLBACK_TO_HASH=false`（生产环境禁止降级到哈希向量）
- [ ] `LLM_TIMEOUT_SECONDS` 根据网络环境适当调大

---

## 开发常用命令

```powershell
# 查看 Worker 日志
docker compose logs -f document-worker

# 查看后端容器日志
docker compose logs -f backend

# 重启 Worker
docker compose restart document-worker

# 构建前端产物
cd frontend && pnpm build

# 手动运行 Worker（非 Docker）
cd backend
.venv-fastapi311\Scripts\python.exe -m app.workers.document_worker
```
