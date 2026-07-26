from enum import StrEnum

from pydantic import BaseModel, Field

from app.documents.models import DocumentType


class FindingCategory(StrEnum):
    METADATA = "METADATA"
    EXTRACTION_QUALITY = "EXTRACTION_QUALITY"
    DOMAIN_RELEVANCE = "DOMAIN_RELEVANCE"
    DUPLICATE = "DUPLICATE"


class FindingSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    BLOCKING = "BLOCKING"


class RecommendedRouting(StrEnum):
    APPROVED = "APPROVED"
    CONTRIBUTOR_REVIEW_REQUIRED = "CONTRIBUTOR_REVIEW_REQUIRED"
    ADMIN_REVIEW_REQUIRED = "ADMIN_REVIEW_REQUIRED"
    REJECTED = "REJECTED"


class QualityFinding(BaseModel):
    code: str
    category: FindingCategory
    severity: FindingSeverity
    confidence: float = Field(ge=0, le=1)
    title: str
    explanation: str
    suggested_action: str | None = None


class QualityValidationInput(BaseModel):
    title: str
    extracted_text: str
    document_type: DocumentType
    is_exact_duplicate: bool = False


class ValidatorResult(BaseModel):
    findings: list[QualityFinding] = Field(default_factory=list)
    detected_topics: list[str] = Field(default_factory=list)


class QualityValidationResult(BaseModel):
    findings: list[QualityFinding]
    blocking_issues: list[QualityFinding]
    warning_count: int
    overall_confidence: float
    recommended_routing: RecommendedRouting
    detected_topics: list[str]
