from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FastAPI Admin Backend"
    app_host: str = "0.0.0.0"
    app_port: int = 3101
    secret_key: str = "change-me-in-production"
    database_url: str = "sqlite:///./app/data/admin_system.db"
    access_token_ttl_seconds: int = 60 * 60 * 24
    captcha_ttl_seconds: int = 60 * 5
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    redis_url: str = "redis://127.0.0.1:6379/0"
    minio_endpoint: str = "127.0.0.1:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "admin-system"
    minio_secure: bool = False
    minio_region: str | None = None
    minio_console_url: str = "http://127.0.0.1:9001"

    @property
    def database_file_path(self) -> Path | None:
        if self.database_url.startswith("sqlite:///./"):
            return BACKEND_DIR / self.database_url.removeprefix("sqlite:///./")
        if self.database_url.startswith("sqlite:///"):
            return Path(self.database_url.removeprefix("sqlite:///"))
        return None

    @property
    def upload_root(self) -> Path:
        return BACKEND_DIR / "app" / "storage" / "uploads"

    @property
    def redis_key_prefix(self) -> str:
        app_slug = "".join(char if char.isalnum() else "-" for char in self.app_name.lower()).strip("-")
        return app_slug or "fastapi-admin"

    @property
    def minio_public_base_url(self) -> str:
        scheme = "https" if self.minio_secure else "http"
        endpoint = self.minio_endpoint.strip()
        if endpoint.startswith(("http://", "https://")):
            parsed = urlparse(endpoint)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        return f"{scheme}://{endpoint}"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
