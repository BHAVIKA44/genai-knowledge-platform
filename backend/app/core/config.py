from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://knowledge:knowledge@localhost:5432/knowledge"
    frontend_origin: str = "http://localhost:5173"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pdf_pages: int = 50
    min_meaningful_characters: int = 50
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
