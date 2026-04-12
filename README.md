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
- Redis 验证码存储
- MinIO 对象存储上传
- 文档上传后自动入队
- 文本文档 / PDF 基础解析
- 文档切 chunk 并写入数据库
- 登录、验证码、个人中心
- 用户、角色、菜单、部门、数据字典 CRUD
- 动态菜单和按钮权限联调
- 文件上传、下载、图片预览
- Scalar API 文档
- 前后端本地联调可运行

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
- MinIO
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

- Python 3.11
- Node.js 20+
- Docker Desktop

## Docker 服务

当前 `docker-compose.yml` 已包含：

- `backend`
  FastAPI 后端服务
- `document-worker`
  常驻文档处理 Worker，负责自动消费队列
- `postgres`
  当前后台管理系统默认使用
- `redis`
  当前已用于验证码存储，后续继续承接缓存、任务状态、异步任务队列
- `minio`
  当前已用于图片、文件上传和对象存储管理
- `qdrant`
  已准备好，后续用于 RAG 向量检索

启动全部服务：

```powershell
cd D:\study_python_20260404\python-ai-agent
docker compose up -d
```

如果你当前只想先跑基础依赖，也可以只启动这四个：

```powershell
docker compose up -d postgres redis minio qdrant
```

## 一键脚本

项目根目录现在提供了一个 Windows PowerShell 启动脚本：

- [start-dev.ps1](D:/study_python_20260404/python-ai-agent/start-dev.ps1)

推荐命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-dev.ps1 -Mode local
```

这条命令的作用：

- 启动 `postgres`
- 启动 `redis`
- 启动 `minio`
- 启动 `qdrant`
- 启动 `document-worker`
- 另外打开一个本地后端窗口执行 `uvicorn`
- 另外打开一个前端开发窗口执行 `pnpm dev`

如果你要把后端也放进容器里，使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-dev.ps1 -Mode compose
```

这条命令的作用：

- 启动 `postgres / redis / minio / qdrant / backend / document-worker`
- 另外打开一个窗口运行前端 `pnpm dev`

如果你只想看脚本会执行什么命令，不真正启动，可以加：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-dev.ps1 -Mode compose -DryRun
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

## Redis 与 MinIO 配置

当前后端默认连接：

- Redis：`redis://127.0.0.1:6379/0`
- MinIO API：`http://127.0.0.1:9000`
- MinIO Console：`http://127.0.0.1:9001`
- Qdrant：`http://127.0.0.1:6333`
- MinIO 用户名：`minioadmin`
- MinIO 密码：`minioadmin`
- MinIO Bucket：`admin-system`
- 文档处理模式：`worker`

## 千问 LLM 配置

文档问答接口现在已经支持接入阿里云百炼千问模型，默认走 OpenAI 兼容接法：

- Provider：`dashscope`
- Base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 默认模型：`qwen-plus`

你只需要在 [backend/.env](D:/study_python_20260404/python-ai-agent/backend/.env) 里填入：

```env
LLM_API_KEY=你的阿里云百炼 API Key
```

可选配置：

```env
LLM_MODEL_NAME=qwen-plus
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=900
```

说明：

- 配置了 `LLM_API_KEY` 后，`/document/qa` 会走“检索 + 千问生成式回答”
- 如果没有配置 Key，系统会自动回退成当前的检索摘要模式，不会影响页面使用

## 后端启动

第一次安装依赖：

```powershell
cd D:\study_python_20260404\python-ai-agent\backend
uv venv --python 3.11 .venv-fastapi311
uv pip install --python .venv-fastapi311\Scripts\python.exe -r requirements.txt
```

说明：

- 本地后端现在推荐固定使用 `Python 3.11`
- 原因是 `fastembed / onnxruntime` 在这套环境里更稳定，能真正启用正式 embedding，而不是退回 hash 向量

启动后端：

```powershell
cd D:\study_python_20260404\python-ai-agent\backend
.venv-fastapi311\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 3101 --reload
```

后端启动后：

- 自动建表
- 自动初始化基础数据
- 自动检查 Redis 连接
- 自动创建 MinIO Bucket
- 默认管理员账号：`admin / 123456`
- 控制台会打印 Scalar 文档地址
- 控制台会打印 MinIO 控制台地址

文档地址：

- Scalar 文档：`http://127.0.0.1:3101/docs`
- OpenAPI JSON：`http://127.0.0.1:3101/openapi.json`

后端控制台启动后还会打印：

- Scalar 文档地址
- MinIO 控制台地址：`http://127.0.0.1:9001`

## 前端启动

第一次安装依赖：

```powershell
cd D:\study_python_20260404\python-ai-agent\frontend
pnpm install
```

启动前端：

```powershell
cd D:\study_python_20260404\python-ai-agent\frontend
pnpm dev
```

默认访问地址：

- `http://127.0.0.1:5173`
- 或 `http://localhost:5173`

前端开发代理默认把 `/api` 转发到：

- `http://localhost:3101`

## 一次看懂怎么启动

你当前推荐的开发方式是：

- `frontend` 本地跑
- `Python backend` 本地跑
- `postgres / redis / minio / qdrant / document-worker` 跑在容器里

这样既方便你改前后端代码，又能保持文档处理链路和基础依赖运行形态稳定。

### 方式一：推荐的本地开发模式

#### 终端 1：启动基础依赖与独立 Worker

```powershell
cd D:\study_python_20260404\python-ai-agent
docker compose up -d postgres redis minio qdrant document-worker
```

这条命令的作用：

- 启动 Docker 里的 `postgres`
- 启动 Docker 里的 `redis`
- 启动 Docker 里的 `minio`
- 启动 Docker 里的 `qdrant`
- 启动 Docker 里的 `document-worker`

#### 终端 2：启动本地后端

```powershell
cd D:\study_python_20260404\python-ai-agent\backend
.venv-fastapi311\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 3101 --reload
```

这条命令的作用：

- 启动本地 FastAPI API 服务
- 方便直接调试 Python 后端代码

#### 终端 3：启动前端

```powershell
cd D:\study_python_20260404\python-ai-agent\frontend
pnpm dev
```

这条命令的作用：

- 启动前端开发服务器
- 本地访问地址通常是 `http://127.0.0.1:5173`

启动完成后访问：

- 前端：`http://127.0.0.1:5173`
- 后端文档：`http://127.0.0.1:3101/docs`
- MinIO Console：`http://127.0.0.1:9001`

默认账号：

- 后台管理员：`admin / 123456`
- MinIO：`minioadmin / minioadmin`

### 方式二：整套容器模式

如果你后面准备把前后端也一起容器化，可以直接使用：

#### 终端 1：启动后端与基础服务

```powershell
cd D:\study_python_20260404\python-ai-agent
docker compose up -d
```

这条命令的作用：

- 启动 Docker 里的 `backend`
- 启动 Docker 里的 `document-worker`
- 启动 Docker 里的 `postgres / redis / minio / qdrant`

#### 终端 2：启动前端

```powershell
cd D:\study_python_20260404\python-ai-agent\frontend
pnpm dev
```

这条命令的作用：

- 启动前端开发服务器
- 代理 `/api` 到本地后端 `3101`

## 快速启动顺序

建议按这个顺序：

1. 启动基础服务

```powershell
cd D:\study_python_20260404\python-ai-agent
docker compose up -d postgres redis minio qdrant document-worker
```

作用：

- 提供 PostgreSQL、Redis、MinIO、Qdrant、独立文档 Worker

2. 启动后端

```powershell
cd D:\study_python_20260404\python-ai-agent\backend
.venv-fastapi311\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 3101 --reload
```

作用：

- 提供登录、菜单、上传、文档处理接口

3. 启动前端

```powershell
cd D:\study_python_20260404\python-ai-agent\frontend
pnpm dev
```

作用：

- 提供管理后台页面

默认情况下，不再推荐本地手动启动 `python -m app.workers.document_worker`。
当前更推荐让 `document-worker` 跟数据库、Redis、MinIO、Qdrant 一样跑在 Docker 里。

5. 浏览器访问

- 前端：`http://127.0.0.1:5173`
- 文档：`http://127.0.0.1:3101/docs`
- MinIO Console：`http://127.0.0.1:9001`

## 当前上传方案

当前上传功能已经切到 MinIO 对象存储。

当前行为：

- 文件内容保存在 MinIO Bucket `admin-system`
- 文件记录保存在 PostgreSQL `sys_file`
- 前端上传、预览、下载、删除链路已打通

当前验证码也已经切到 Redis，不再依赖单进程内存存储。

## 当前文档处理能力

第二阶段已经开始落地，当前后端已支持：

- 文件上传后自动创建文档记录
- 自动创建文档处理任务并入 Redis 队列
- 文本文档和 PDF 的基础文本提取
- 图片类文档 OCR
- 扫描版 PDF OCR 回退处理
- 自动切 chunk
- chunk 元数据写入 PostgreSQL
- chunk 自动写入 Qdrant
- 已提供基础文档检索接口
- 已提供基于千问的文档问答接口

当前已提供的接口分组：

- `文档处理`
  - 文档列表
  - 文档详情
  - 文档任务列表
  - 文档队列状态
  - 文档切片列表
  - 文档切片搜索
  - 重新处理文档

当前说明：

- 文本类文件已支持：`txt / md / csv / json / yaml / xml / html`
- PDF 已支持基础文本提取
- 图片类文件已支持 OCR：`png / jpg / jpeg / bmp / gif / webp / tif / tiff`
- 扫描版 PDF 会在“提取不到文本”时自动尝试 OCR
- 文档处理成功后，chunk 会自动写入 Qdrant
- 当前本地 Python 3.11 环境已可启用 `fastembed` 正式 embedding 模型
- 当前检索层已经支持向量召回、关键词补偿、权限过滤和千问 RAG 问答

当前文档处理已经切成独立 worker 模式，Web API 只负责入队，不在主线程里直接做 OCR 或切片。

处理逻辑是：

- 上传文件后立即创建文档任务
- 如果当前 worker 正在处理别的文档，新任务会自动排队
- 如果当前没有任务，worker 会马上开始处理
- 推荐让 `document-worker` 跟 `postgres / redis / minio / qdrant` 一起跑在 Docker 里

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
