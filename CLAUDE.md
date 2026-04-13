# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an enterprise-grade admin system with RAG (Retrieval-Augmented Generation) capabilities, combining a Vue 3 management frontend with a FastAPI backend. The system supports document processing, vector search, and AI-powered Q&A using Alibaba's Qwen LLM.

## Tech Stack

**Frontend:**
- Vue 3 + Vite + Element Plus
- Pinia for state management
- Vue Router for routing

**Backend:**
- FastAPI + SQLAlchemy
- PostgreSQL for persistence
- Redis for caching and task queues
- MinIO for object storage
- Qdrant for vector search
- fastembed for embeddings
- Qwen (via DashScope) for LLM

## Development Setup

### Prerequisites
- Python 3.11 (required for stable fastembed/onnxruntime)
- Node.js 20+
- Docker Desktop

### Quick Start

**Recommended local development mode:**

1. Start infrastructure services:
```powershell
docker compose up -d postgres redis minio qdrant document-worker
```

2. Start backend (in separate terminal):
```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\start-backend.ps1
```

3. Start frontend (in separate terminal):
```powershell
cd frontend
pnpm dev
```

**Alternative: Full container mode:**
```powershell
docker compose up -d
cd frontend
pnpm dev
```

### Backend Setup

First-time installation:
```powershell
cd backend
uv venv --python 3.11 .venv-fastapi311
uv pip install --python .venv-fastapi311\Scripts\python.exe -r requirements.txt
```

The backend uses a fixed Python 3.11 virtual environment at `backend/.venv-fastapi311` for stable embedding support.

### Access Points

- Frontend: http://127.0.0.1:5173
- Backend API docs: http://127.0.0.1:3101/docs
- MinIO Console: http://127.0.0.1:9001
- Default admin: `admin / 123456`
- MinIO credentials: `minioadmin / minioadmin`

## Architecture

### Backend Structure

```
backend/app/
├── api/              # API route handlers
│   ├── auth.py       # Login, captcha, logout
│   ├── users.py      # User CRUD
│   ├── roles.py      # Role management
│   ├── menus.py      # Dynamic menu & button permissions
│   ├── departments.py # Department tree
│   ├── dicts.py      # Data dictionary
│   ├── uploads.py    # File upload/download
│   └── documents.py  # Document processing & RAG Q&A
├── core/             # Core infrastructure
│   ├── config.py     # Settings (loads from .env)
│   ├── database.py   # SQLAlchemy setup
│   ├── security.py   # JWT & password hashing
│   ├── deps.py       # FastAPI dependencies
│   ├── redis_client.py # Redis connection
│   └── captcha.py    # Captcha generation
├── services/         # Business logic
│   ├── document_processor.py  # Text extraction, chunking
│   ├── document_queue.py      # Redis task queue
│   ├── embedding.py           # fastembed wrapper
│   ├── qdrant_vector_store.py # Vector DB operations
│   ├── rag_retrieval.py       # Hybrid search (vector + keyword)
│   ├── rag_answer.py          # LLM-based Q&A
│   ├── llm_service.py         # OpenAI-compatible LLM client
│   ├── object_storage.py      # MinIO operations
│   └── document_permissions.py # Permission filtering
├── workers/
│   └── document_worker.py     # Background document processor
├── models.py         # SQLAlchemy models
├── schemas.py        # Pydantic schemas
└── main.py           # FastAPI app entry
```

### Key Concepts

**Document Processing Pipeline:**
1. File uploaded → saved to MinIO → record created in PostgreSQL
2. Document task created → pushed to Redis queue
3. `document-worker` pops task → extracts text (PDF/OCR/plain text)
4. Text chunked → chunks saved to PostgreSQL
5. Chunks embedded → vectors upserted to Qdrant

**Permission Model:**
- Platform RBAC: menu/button permissions via roles
- Data scope: department-based access control (all/dept/dept-and-below/self)
- Knowledge space ACL: planned for fine-grained document sharing

**RAG Retrieval:**
- Hybrid search: vector similarity + keyword matching
- Permission filtering: only returns chunks user can access
- Reranking: exact match bonus + configurable weights
- LLM answer generation: uses top chunks as context for Qwen

## Configuration

Backend configuration is in `backend/.env` (see `backend/.env.example` for template).

**Critical settings:**
- `DATABASE_URL`: PostgreSQL connection (port 5433 for local, 5432 in container)
- `REDIS_URL`: Redis connection
- `MINIO_ENDPOINT`: MinIO endpoint (127.0.0.1:9000 for local, minio:9000 in container)
- `QDRANT_URL`: Qdrant endpoint
- `DOCUMENT_PROCESSING_MODE`: Set to `worker` (async processing)
- `LLM_API_KEY`: Alibaba DashScope API key (optional, falls back to retrieval-only mode)

**Embedding configuration:**
- `EMBEDDING_PROVIDER`: `fastembed` (default)
- `EMBEDDING_MODEL_NAME`: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- `EMBEDDING_VECTOR_SIZE`: 384
- `EMBEDDING_FALLBACK_TO_HASH`: `true` (falls back to hash vectors if model unavailable)

## Common Tasks

**Run backend locally:**
```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\start-backend.ps1
```

**Run frontend dev server:**
```powershell
cd frontend
pnpm dev
```

**Build frontend:**
```powershell
cd frontend
pnpm build
```

**Start document worker (if not using Docker):**
```powershell
cd backend
.venv-fastapi311\Scripts\python.exe -m app.workers.document_worker
```

**View Docker logs:**
```powershell
docker compose logs -f document-worker
docker compose logs -f backend
```

**Restart services:**
```powershell
docker compose restart document-worker
docker compose restart backend
```

## Important Notes

- Always use Python 3.11 for backend to ensure fastembed stability
- The `document-worker` should run as a separate process (Docker recommended)
- Document processing is async: upload returns immediately, processing happens in background
- Supported document types: txt, md, csv, json, yaml, xml, html, PDF, images (with OCR)
- RAG Q&A requires `LLM_API_KEY` to be set; otherwise falls back to retrieval-only mode
- Frontend proxies `/api` requests to `http://localhost:3101`

## Planned Features

The README describes a planned "knowledge space" feature for enterprise knowledge management:
- Multi-tenant knowledge spaces with ACL
- Space-level permissions (owner/manager/editor/viewer)
- Department/role/user-based sharing
- Audit logs and content governance

This is not yet implemented. Current permission model uses department-based data scopes.
