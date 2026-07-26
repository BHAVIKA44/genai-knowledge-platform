from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.documents.models import DocumentStatus, DocumentType
from app.knowledge_quality.models import QualityFinding


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    source_filename: str
    document_type: DocumentType
    status: DocumentStatus
    detected_topics: list[str]
    validation_findings: list[QualityFinding]
    contributor_review_decision: str | None
    created_at: datetime
    updated_at: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str
    action: str | None = None
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
