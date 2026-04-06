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

## Auth Features

- `POST /api/auth/login`: supports username or email plus password.
- `POST /api/auth/password-reset/code`: sends a 6-digit password reset code to email.
- `POST /api/auth/password-reset/confirm`: resets password with email + code + new password.
- `GET /api/auth/session`: validates the current JWT and returns the signed-in user profile.

When SMTP is not configured, the backend falls back to logging the reset code. If `AUTH_DEBUG_EXPOSE_RESET_CODE=true`, the code is also returned in the API response for local development.
