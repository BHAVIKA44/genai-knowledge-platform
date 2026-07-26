from typing import Literal

from pydantic import BaseModel, Field, field_validator


class KnowledgeClaim(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    is_time_sensitive: bool
    requires_external_verification: bool


class SemanticFinding(BaseModel):
    category: str = Field(min_length=1)
    severity: str = Field(pattern="^(INFO|WARNING|BLOCKING)$")
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(min_length=1)
    suggested_improvement: str | None = None
    contributor_fix_possible: bool
    admin_review_required: bool


class KnowledgeAnalysis(BaseModel):
    proposed_title: str | None = None
    summary: str = Field(min_length=1)
    topics: list[str]
    claims: list[KnowledgeClaim]
    semantic_findings: list[SemanticFinding] = Field(default_factory=list)

    @field_validator("topics")
    @classmethod
    def normalize_topics(cls, value: list[str]) -> list[str]:
        normalized: dict[str, str] = {}
        for topic in value:
            cleaned = " ".join(topic.split())
            if cleaned:
                normalized.setdefault(cleaned.casefold(), cleaned)
        return list(normalized.values())


class EvidenceSource(BaseModel):
    title: str | None = None
    url: str = Field(min_length=1)


class GroundedClaimVerification(BaseModel):
    claim: str = Field(min_length=1)
    verdict: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_SUPPORTED", "INSUFFICIENT_EVIDENCE"]
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(min_length=1)
    evidence_sources: list[EvidenceSource] = Field(default_factory=list)


class GroundedClaimAnalysis(BaseModel):
    verifications: list[GroundedClaimVerification]
