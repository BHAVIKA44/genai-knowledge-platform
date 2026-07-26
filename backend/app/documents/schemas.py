from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.documents.models import DocumentStatus, DocumentType


class FindingSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    BLOCKING = "BLOCKING"


class ValidationFinding(BaseModel):
    code: str
    severity: FindingSeverity
    title: str
    explanation: str
    suggested_action: str | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    source_filename: str
    document_type: DocumentType
    status: DocumentStatus
    detected_topics: list[str]
    validation_findings: list[ValidationFinding]
    created_at: datetime
    updated_at: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str
    action: str | None = None
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
