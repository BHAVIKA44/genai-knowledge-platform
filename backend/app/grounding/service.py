from dataclasses import dataclass
from datetime import datetime

from app.core.config import Settings
from app.core.errors import DomainError
from app.documents.models import now_utc
from app.llm.client import (
    GeminiConfigurationError,
    GeminiInvalidResponseError,
    GeminiKnowledgeClient,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiTransientError,
)
from app.llm.models import EvidenceSource, KnowledgeClaim


@dataclass(frozen=True)
class ClaimVerificationResult:
    claim: str
    verdict: str
    confidence: float
    explanation: str
    evidence_sources: list[EvidenceSource]
    verified_at: datetime


class GroundedClaimVerificationService:
    def __init__(self, settings: Settings, client: GeminiKnowledgeClient | None = None) -> None:
        self.max_claims = settings.grounding_max_claims
        self.client = client or GeminiKnowledgeClient(settings)

    def verify(self, claims: list[KnowledgeClaim]) -> list[ClaimVerificationResult]:
        eligible_claims = [
            claim
            for claim in claims
            if claim.requires_external_verification or claim.is_time_sensitive
        ][: self.max_claims]
        if not eligible_claims:
            return []
        try:
            analysis = self.client.verify_claims(eligible_claims)
        except (
            GeminiConfigurationError,
            GeminiInvalidResponseError,
            GeminiRateLimitError,
            GeminiTimeoutError,
            GeminiTransientError,
        ) as error:
            raise DomainError(
                "GROUNDING_FAILED",
                "We could not verify these claims right now.",
                "Please try again shortly.",
                503,
            ) from error
        verifications = {
            verification.claim: verification for verification in analysis.verifications
        }
        if any(claim.text not in verifications for claim in eligible_claims):
            raise DomainError(
                "GROUNDING_FAILED",
                "We could not verify these claims right now.",
                "Please try again shortly.",
                503,
            )
        verified_at = now_utc()
        return [
            ClaimVerificationResult(
                claim=claim.text,
                verdict=(
                    verifications[claim.text].verdict
                    if verifications[claim.text].evidence_sources
                    else "INSUFFICIENT_EVIDENCE"
                ),
                confidence=verifications[claim.text].confidence,
                explanation=verifications[claim.text].explanation,
                evidence_sources=verifications[claim.text].evidence_sources,
                verified_at=verified_at,
            )
            for claim in eligible_claims
        ]
