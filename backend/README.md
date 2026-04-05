# Backend

FastAPI backend for the Enterprise RAG project.

## Run

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## Environment

Copy `.env.example` to `.env` inside `backend/`.
