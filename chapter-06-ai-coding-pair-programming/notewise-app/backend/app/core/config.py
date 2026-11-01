# from functools import lru_cache
# from pathlib import Path

# from pydantic import Field, SecretStr, model_validator
# from pydantic_settings import BaseSettings, SettingsConfigDict


# class Settings(BaseSettings):
#     app_name: str = "NoteWise API"
#     app_env: str = "development"
#     api_v1_prefix: str = "/api/v1"
#     secret_key: SecretStr = SecretStr("")
#     access_token_expire_minutes: int = Field(default=60, gt=0, le=1440)
#     document_storage_path: Path = Path("storage/uploads")
#     max_upload_size_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
#     openai_api_key: SecretStr | None = None
    
#     # === BỔ SUNG DÒNG NÀY ĐỂ NHẬN GOOGLE GEMINI API KEY ===
#     google_api_key: SecretStr | None = None
    
#     database_url: str = (
#         "postgresql+asyncpg://notewise:notewise@localhost:5432/notewise"
#     )
#     cors_origins: list[str] = ["http://localhost:3000"]

#     model_config = SettingsConfigDict(
#         env_file="../.env",
#         env_file_encoding="utf-8",
#         case_sensitive=False,
#         extra="ignore",
#     )

#     @model_validator(mode="after")
#     def validate_production_secrets(self) -> "Settings":
#         if self.app_env.lower() == "production":
#             secret = self.secret_key.get_secret_value()
#             if len(secret) < 32 or secret.startswith("replace-with-"):
#                 raise ValueError(
#                     "SECRET_KEY must be a unique value of at least 32 characters in production"
#                 )
#         return self


# @lru_cache
# def get_settings() -> Settings:
#     return Settings()


# settings = get_settings()

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NoteWise API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    secret_key: SecretStr = SecretStr("")
    access_token_expire_minutes: int = Field(default=60, gt=0, le=1440)
    document_storage_path: Path = Path("storage/uploads")
    max_upload_size_bytes: int = Field(default=20 * 1024 * 1024, gt=0)

    # Giữ lại để code cũ nào còn tham chiếu không bị lỗi AttributeError
    openai_api_key: SecretStr | None = None

    # Google Gemini API key (lấy miễn phí tại Google AI Studio)
    google_api_key: SecretStr | None = None

    database_url: str = (
        "postgresql+asyncpg://notewise:notewise@localhost:5432/notewise"
    )
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        # Tìm .env trong thư mục backend trước, sau đó tới thư mục cha
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env.lower() == "production":
            secret = self.secret_key.get_secret_value()
            if len(secret) < 32 or secret.startswith("replace-with-"):
                raise ValueError(
                    "SECRET_KEY must be a unique value of at least 32 characters in production"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()