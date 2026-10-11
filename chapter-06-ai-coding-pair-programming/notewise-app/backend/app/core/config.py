from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://notewise:notewise_dev_password@localhost:5432/notewise"
    )
    jwt_secret: str = "development-only-change-this-jwt-secret"
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_seconds: Literal[900] = 900
    auth_rate_limit_window_seconds: int = Field(default=60, gt=0)
    auth_register_rate_limit: int = Field(default=5, gt=0)
    auth_login_rate_limit: int = Field(default=10, gt=0)
    document_upload_rate_limit: int = Field(default=20, gt=0)
    document_max_upload_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    document_max_uncompressed_bytes: int = Field(
        default=250 * 1024 * 1024,
        gt=0,
    )
    document_max_pages: int = Field(default=2000, gt=0)
    document_storage_dir: str = str(
        Path(__file__).resolve().parents[2] / "data" / "documents"
    )
    document_worker_poll_interval_seconds: float = Field(default=1.0, gt=0)
    document_job_lease_seconds: int = Field(default=300, gt=0)
    document_job_max_attempts: int = Field(default=3, gt=0)
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    ai_embedding_model: str = "text-embedding-3-small"
    ai_chat_model: str = "gpt-4o-mini"
    ai_embedding_dimensions: Literal[1536] = 1536
    ai_similarity_threshold: float = Field(default=0.35, ge=-1, le=1)
    ai_retrieval_limit: Literal[5] = 5
    ai_request_timeout_seconds: float = Field(default=30.0, gt=0)
    ai_max_context_characters: int = Field(default=100_000, gt=1000)
    ai_request_rate_limit: int = Field(default=20, gt=0)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def require_production_secret(self) -> "Settings":
        if (
            self.app_env.lower() not in {"development", "test"}
            and (
                self.jwt_secret == "development-only-change-this-jwt-secret"
                or len(self.jwt_secret.encode("utf-8")) < 32
            )
        ):
            raise ValueError(
                "JWT_SECRET must contain at least 32 bytes outside development."
            )
        return self


settings = Settings()
