from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    sqlite_database_url: str = "sqlite+aiosqlite:///./data/notewise.db"
    chroma_persist_directory: str = "./data/chroma"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
