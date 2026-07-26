from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import JSON, Column, Enum
from sqlmodel import Field, SQLModel


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    VALIDATING = "VALIDATING"
    APPROVED = "APPROVED"
    CONTRIBUTOR_REVIEW_REQUIRED = "CONTRIBUTOR_REVIEW_REQUIRED"
    ADMIN_REVIEW_REQUIRED = "ADMIN_REVIEW_REQUIRED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class DocumentType(StrEnum):
    MARKDOWN = "MARKDOWN"
    TEXT = "TEXT"
    PDF = "PDF"


def now_utc() -> datetime:
    return datetime.now(UTC)


class KnowledgeDocument(SQLModel, table=True):
    __tablename__ = "knowledge_documents"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    title: str
    source_filename: str
    storage_filename: str
    document_type: DocumentType
    extracted_text: str | None = None
    detected_topics: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    status: DocumentStatus = Field(
        sa_column=Column(Enum(DocumentStatus, native_enum=False, length=48), nullable=False)
    )
    validation_findings: list[dict[str, object]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    contributor_review_decision: str | None = None
    analysis_summary: str | None = None
    analysis_topics: list[str] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    analysis_claims: list[dict[str, object]] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    analysis_proposed_title: str | None = None
    analysis_model: str | None = None
    analysis_prompt_version: str | None = None
    analyzed_at: datetime | None = None
    sha256: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=now_utc, nullable=False)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)
