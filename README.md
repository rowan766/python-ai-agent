# Python AI Agent

> 基于 FastAPI + LangChain + Qdrant 构建的企业级 AI 聊天与 RAG 知识库系统

## 技术栈

| 层级 | 技术 | 说明 |
|---|---|---|
| Web 框架 | FastAPI + Uvicorn | 高性能异步 API，对标 NestJS |
| LLM | OpenAI SDK（兼容千问） | 通义千问 / OpenAI 均可接入 |
| RAG 框架 | LangChain + LangChain-Community | 文档加载、切分、检索 |
| 向量数据库 | Qdrant | 语义向量存储与相似度检索 |
| 关系数据库 | PostgreSQL + SQLAlchemy (async) | 用户系统与元数据存储 |
| 缓存 / 会话 | Redis | 多轮对话记忆、JWT 黑名单 |
| 认证 | JWT（python-jose）+ bcrypt | 无状态登录鉴权 |
| 数据校验 | Pydantic v2 | 请求 / 响应结构定义 |
| 包管理 | uv | 比 pip 快 10x，虚拟环境隔离 |

---

## 项目结构

```
python-ai-agent/
├── app/
│   ├── main.py                  # FastAPI 入口，路由注册，lifespan 管理
│   ├── api/
│   │   ├── chat.py              # 聊天接口（流式 SSE + 非流式）
│   │   ├── rag.py               # RAG 接口（文档上传、检索）
│   │   └── auth.py              # 用户认证接口（注册、登录、用户信息）
│   ├── core/
│   │   ├── llm.py               # OpenAI 客户端封装（全局单例）
│   │   ├── database.py          # 异步数据库引擎与 Session 管理
│   │   ├── auth.py              # JWT 生成/验证、密码哈希工具
│   │   └── rag/
│   │       ├── loader.py        # 多格式文档加载与切分
│   │       ├── indexer.py       # 文档向量化并存入 Qdrant
│   │       └── retriever.py     # 向量相似度检索
│   └── models/
│       ├── schemas.py           # 聊天相关 Pydantic 数据模型
│       └── user.py              # 用户数据库模型（SQLAlchemy ORM）
├── .env                         # 环境变量（不提交 Git）
├── .env.example                 # 环境变量模板
├── docker-compose.yml           # Qdrant + Redis + PostgreSQL
├── pyproject.toml               # 项目依赖（uv 管理）
└── uv.lock                      # 锁文件（精确版本）
```

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/你的用户名/python-ai-agent.git
cd python-ai-agent
```

### 2. 安装 uv（包管理工具）

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，填入真实配置：

```bash
cp .env.example .env
```

### 4. 安装依赖

```bash
uv python install 3.11
uv python pin 3.11
uv sync
```

### 5. 启动基础服务（数据库）

```bash
docker compose up -d
```

### 6. 启动应用

```bash
uv run uvicorn app.main:app --reload --port 8000
```

访问 `http://localhost:8000/docs` 查看 API 文档。

---

## 环境变量说明（.env.example）

```env
# LLM 配置（支持千问 / OpenAI，接口兼容）
OPENAI_API_KEY=sk-你的APIKey
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DEFAULT_MODEL=qwen-plus

# 向量数据库 Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Redis（对话记忆、会话管理）
REDIS_URL=redis://localhost:6379

# PostgreSQL（用户系统、知识库元数据）
DATABASE_URL=postgresql+asyncpg://admin:password123@localhost:5432/ai_agent

# JWT 认证
JWT_SECRET=替换为随机字符串
JWT_EXPIRE_MINUTES=1440

# 应用配置
APP_ENV=development
APP_PORT=8000
```

> 使用 OpenAI 只需将 `OPENAI_BASE_URL` 改为 `https://api.openai.com/v1`，其余代码不变。

---

## API 接口

### 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/register` | 注册新用户，返回 JWT |
| POST | `/api/auth/login` | 用户登录，返回 JWT |
| GET | `/api/auth/me` | 获取当前用户信息（需 Bearer Token） |

### 聊天

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat` | 发送消息，支持流式（SSE）和非流式响应 |

**请求示例：**

```json
{
  "messages": [
    { "role": "user", "content": "你好！" }
  ],
  "model": "qwen-plus",
  "stream": true
}
```

**流式响应格式（SSE）：**

```
data: {"content": "你"}
data: {"content": "好"}
data: [DONE]
```

### RAG 知识库

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/rag/upload` | 上传文档，自动解析、切分、向量化存储 |
| POST | `/api/rag/query` | 检索知识库，返回最相关文档片段 |
| GET | `/api/rag/supported-formats` | 查询当前支持的文件格式 |

**支持的文件格式：**

`.pdf` / `.docx` / `.doc` / `.xlsx` / `.xls` / `.pptx` / `.ppt` / `.html` / `.md` / `.txt`

---

## RAG 核心流程

```
用户上传文档
    ↓
文档解析（loader.py）
按格式自动选择解析器 → 读取文本内容
    ↓
文本切分（RecursiveCharacterTextSplitter）
chunk_size=500 / chunk_overlap=50
    ↓
向量化（OpenAI Embeddings / 千问兼容）
每个文本块 → 1024 维向量
    ↓
存入 Qdrant（indexer.py）
余弦相似度索引
    ↓
用户提问 → 向量检索（retriever.py）
返回 Top-K 最相关片段（score_threshold=0.6）
```

---

## 基础服务

通过 Docker Compose 管理三个基础服务：

```yaml
# 启动
docker compose up -d

# 查看状态
docker compose ps

# 停止
docker compose down
```

| 服务 | 端口 | 用途 |
|---|---|---|
| Qdrant | 6333 | 向量数据库（RAG 检索） |
| Redis | 6379 | 对话记忆缓存 |
| PostgreSQL | 5432 | 用户数据与元数据 |

---

## 开发工具推荐（VSCode 插件）

- **Python**（微软官方）
- **Pylance**（类型提示与智能补全）
- **Ruff**（Python Linter，比 flake8 快很多）
- **REST Client**（直接在 VSCode 里测试接口）

---

## 后续规划

- [ ] 对话历史持久化（Redis + PostgreSQL）
- [ ] Hybrid Search（BM25 关键词 + 向量语义融合）
- [ ] Reranker 重排序（BGE-reranker）
- [ ] LangGraph 多步推理 Agent
- [ ] 多知识库管理（按用户隔离）
- [ ] 前端页面（React / Vue）

---

## 学习参考

本项目参考以下开源项目的架构设计：

- [Dify](https://github.com/langgenius/dify) — 生产级 AI Agent 平台，重点参考 `api/core/` 的 Agent、RAG、Tool 实现
- [LangGraph Examples](https://github.com/langchain-ai/langgraph/tree/main/examples) — 多智能体编排模式参考
- [RAGFlow](https://github.com/infiniflow/ragflow) — 企业级 RAG 优化策略参考