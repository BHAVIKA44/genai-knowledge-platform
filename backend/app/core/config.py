from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://knowledge:knowledge@localhost:5432/knowledge"
    frontend_origin: str = "http://localhost:5173"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pdf_pages: int = 50
    max_document_chunks: int = Field(default=500, ge=1)
    minimum_vector_similarity: float = Field(default=0.72, ge=-1, le=1)
    min_meaningful_characters: int = 150
    low_confidence_review_threshold: float = 0.7
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"
    gemini_timeout_seconds: float = Field(default=20, gt=0)
    gemini_max_retries: int = Field(default=2, ge=0)
    gemini_prompt_version: str = "v1"
    grounding_max_claims: int = Field(default=5, ge=1, le=25)
    source_storage_root: str = "./.source-storage"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
