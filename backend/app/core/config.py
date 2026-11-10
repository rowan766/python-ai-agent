from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator, model_validator
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
    secret_key: str = Field(min_length=32, description="JWT 签名密钥，生产环境必须修改")
    database_url: str = "sqlite:///./app/data/admin_system.db"
    access_token_ttl_seconds: int = 60 * 60 * 24
    captcha_ttl_seconds: int = 60 * 5
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    document_processing_mode: str = "worker"
    document_chunk_size: int = 800
    document_chunk_overlap: int = 120
    embedding_provider: str = "fastembed"
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_batch_size: int = 32
    embedding_fallback_to_hash: bool = True
    embedding_vector_size: int = 384
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "document_chunks"
    retrieval_default_limit: int = 8
    retrieval_candidate_limit: int = 24
    retrieval_keyword_weight: float = 0.22
    retrieval_exact_match_bonus: float = 0.08
    retrieval_relevance_threshold: float = 0.3
    rag_answer_max_chunks: int = 4
    rag_answer_max_context_chars: int = 2400
    llm_provider: str = "dashscope"
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "DASHSCOPE_API_KEY", "DEEPSEEK_API_KEY"),
    )
    llm_model_name: str = "qwen-plus"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 900
    llm_timeout_seconds: float = 60.0
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

    @property
    def llm_enabled(self) -> bool:
        return bool((self.llm_api_key or "").strip())

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v == "change-me-in-production":
            raise ValueError(
                "SECRET_KEY 不能使用默认值，请在 .env 文件中设置一个至少 32 位的随机字符串"
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY 长度必须至少为 32 个字符")
        return v

    @model_validator(mode="after")
    def validate_settings(self):
        # 验证 worker 模式必须配置 Redis
        if self.document_processing_mode == "worker" and not self.redis_url:
            raise ValueError("文档处理模式为 worker 时必须配置 REDIS_URL")

        # 验证数据库 URL
        if not self.database_url:
            raise ValueError("DATABASE_URL 不能为空")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
