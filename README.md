# Python AI Agent

企业级 RAG 单仓项目，当前采用前后端同仓结构：

```text
python-ai-agent/
├── backend/                 # FastAPI + SQLAlchemy + Qdrant 后端
├── frontend/                # Vue 3 + Vite + Element Plus 前端
├── docker-compose.yml       # PostgreSQL / Redis / Qdrant
├── enterprise-rag-*.md      # 方案与设计文档
└── studyDev.md              # 学习笔记
```

## 启动方式

### 1. 启动基础服务

```bash
docker compose up -d
```

### 2. 启动后端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

接口文档：

- `http://127.0.0.1:8000/docs`
- `http://localhost:8000/docs`

### 3. 启动前端

```bash
cd frontend
corepack pnpm install
corepack pnpm dev
```

默认前端会请求：

- `http://127.0.0.1:8000`

## 目录说明

- `backend/app/main.py`
  FastAPI 应用入口、路由注册和 Scalar 文档页
- `backend/app/api`
  认证、组织、知识库、文档、RAG 等接口
- `backend/app/core`
  数据库、认证、模型客户端、权限与路径配置
- `frontend/src`
  前端页面、路由、状态管理与接口封装

## 环境文件

后端环境文件位于：

- `backend/.env`
- 模板：`backend/.env.example`

前端环境示例位于：

- `frontend/.env.example`

## 当前能力

- 用户注册、登录、当前用户
- 部门树、自举首个部门、加入部门申请与审批
- 部门治理：创建部门、调整层级、指定负责人、影响评估
- 知识库空间、归属型文档上传、文档列表
- 知识库共享申请与审批
- 按可访问知识库范围过滤的检索
- Scalar 风格接口文档
