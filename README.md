# Python AI Agent

当前仓库是一套正在演进中的“后台管理系统 + 企业级 RAG 底座”项目。

现阶段我们已经优先把管理后台跑通：

- `frontend/`
  Vue 3 + Vite + Element Plus 管理前端
- `backend/`
  FastAPI + SQLAlchemy 后端
- `docker-compose.yml`
  本地基础服务编排

项目当前的推进策略是：

1. 先打通后台管理、登录鉴权、动态菜单、按钮权限、文件上传和数据库基础设施
2. 再补企业级 RAG 所需的对象存储、异步任务和缓存能力
3. 最后接入向量库、chunk、embedding 和检索问答链路

## 当前状态

当前已经完成：

- FastAPI 后端基础工程
- PostgreSQL 持久化配置
- 登录、验证码、个人中心
- 用户、角色、菜单、部门、数据字典 CRUD
- 动态菜单和按钮权限联调
- 文件上传、下载、图片预览
- Scalar API 文档
- 前后端本地联调可运行

当前还没有切到 MinIO，上传文件暂时存放在本地目录：

- `backend/app/storage/uploads/`

这是为了先把前后端和权限主链路跑通。后续如果按企业级 RAG 路线推进，文件存储建议切换到 MinIO。

## 技术栈

前端：

- Vue 3
- Vite
- Element Plus
- Pinia
- Vue Router
- Axios

后端：

- FastAPI
- SQLAlchemy
- PostgreSQL
- Scalar FastAPI

基础服务：

- PostgreSQL
- Redis
- Qdrant

## 当前目录

```text
python-ai-agent/
├── backend/                 # FastAPI 后端
├── frontend/                # Vue 管理前端
├── docker-compose.yml       # PostgreSQL / Redis / Qdrant
├── README.md
└── sample-upload-test.md
```

## 环境要求

- Python 3.11+
- Node.js 20+
- Docker Desktop

## Docker 服务

当前 `docker-compose.yml` 已包含：

- `postgres`
  当前后台管理系统默认使用
- `redis`
  已准备好，后续用于验证码、缓存、任务状态、异步任务队列
- `qdrant`
  已准备好，后续用于 RAG 向量检索

启动全部基础服务：

```powershell
cd D:\study_python_20260404\python-ai-agent
docker compose up -d
```

如果你当前只想先跑后台管理系统，至少启动 PostgreSQL：

```powershell
docker compose up -d postgres
```

## PostgreSQL 配置

当前后端默认连接：

- 地址：`127.0.0.1`
- 端口：`5433`
- 数据库：`admin_system`
- 用户名：`admin`
- 密码：`password123`

对应环境文件：

- [backend/.env](D:/study_python_20260404/python-ai-agent/backend/.env)
- [backend/.env.example](D:/study_python_20260404/python-ai-agent/backend/.env.example)

## 后端启动

第一次安装依赖：

```powershell
cd D:\study_python_20260404\python-ai-agent\backend
uv venv .venv-fastapi
uv pip install --python .venv-fastapi\Scripts\python.exe bcrypt fastapi itsdangerous pydantic-settings psycopg[binary] python-multipart scalar-fastapi sqlalchemy "uvicorn[standard]"
```

启动后端：

```powershell
cd D:\study_python_20260404\python-ai-agent\backend
.venv-fastapi\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 3101 --reload
```

后端启动后：

- 自动建表
- 自动初始化基础数据
- 默认管理员账号：`admin / 123456`
- 控制台会打印 Scalar 文档地址

文档地址：

- Scalar 文档：`http://127.0.0.1:3101/docs`
- OpenAPI JSON：`http://127.0.0.1:3101/openapi.json`

## 前端启动

第一次安装依赖：

```powershell
cd D:\study_python_20260404\python-ai-agent\frontend
npm install
```

启动前端：

```powershell
cd D:\study_python_20260404\python-ai-agent\frontend
npm run dev
```

默认访问地址：

- `http://127.0.0.1:5173`
- 或 `http://localhost:5173`

前端开发代理默认把 `/api` 转发到：

- `http://localhost:3101`

## 快速启动顺序

建议按这个顺序：

1. 启动数据库

```powershell
cd D:\study_python_20260404\python-ai-agent
docker compose up -d postgres
```

2. 启动后端

```powershell
cd D:\study_python_20260404\python-ai-agent\backend
.venv-fastapi\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 3101 --reload
```

3. 启动前端

```powershell
cd D:\study_python_20260404\python-ai-agent\frontend
npm run dev
```

4. 浏览器访问

- 前端：`http://127.0.0.1:5173`
- 文档：`http://127.0.0.1:3101/docs`

## 当前上传方案

当前上传功能已经可用，但实现方式是本地文件存储，不是 MinIO。

当前行为：

- 文件内容保存在 `backend/app/storage/uploads/`
- 文件记录保存在 PostgreSQL `sys_file`
- 前端上传、预览、下载、删除链路已打通

这样做的原因是：

- 先确保权限、上传、元数据、页面联调闭环
- 降低最初接入复杂度

## 推荐演进路线

基于你当前项目和我们的执行计划，建议下一阶段按下面顺序推进：

### 第一阶段：企业级底座

- PostgreSQL
  用户、角色、菜单、部门、知识库、文档元数据
- Redis
  验证码、缓存、任务状态、异步任务队列
- MinIO
  原始文件、附件、预处理产物、导出文件

这一阶段的目标是：

- 把上传链路从本地文件切换到 MinIO
- 把验证码和后续异步任务基础设施切到 Redis
- 保持前端接口尽量稳定

### 第二阶段：文档处理链路

- 文档上传后异步入队
- 文本提取 / OCR
- 文档切 chunk
- chunk 元数据入库

### 第三阶段：RAG 检索链路

- 向量库写入 embedding
- 检索召回
- 权限过滤
- 重排与问答接口

## 当前建议

如果你的目标是企业级 RAG，我建议：

1. 先保留当前已跑通的管理后台能力
2. 下一步优先接入 `MinIO + Redis`
3. 等文件和权限模型稳定后，再正式接 `Qdrant + chunk + embedding + 检索`

这个顺序会比“一开始先堆向量库”更稳，因为企业级 RAG 的难点通常先出现在：

- 文件存储
- 权限继承
- 知识库边界
- 任务编排
- 失败重试和状态追踪

## 备注

如果你后面准备继续推进下一阶段，我建议直接在当前代码基础上做这两件事：

- 把上传服务切到 MinIO
- 把验证码和任务状态切到 Redis

这样项目就会从“能跑的后台管理系统”升级成“RAG-ready 的后台底座”。
