from datetime import datetime

import pytest

from app.core.config import Settings
from app.core.errors import DomainError
from app.grounding.service import GroundedClaimVerificationService
from app.llm.client import GeminiTransientError
from app.llm.models import (
    EvidenceSource,
    GroundedClaimAnalysis,
    GroundedClaimVerification,
    KnowledgeClaim,
)


def claim(
    text: str,
    *,
    time_sensitive: bool = False,
    externally_verifiable: bool = False,
) -> KnowledgeClaim:
    return KnowledgeClaim(
        text=text,
        confidence=0.8,
        is_time_sensitive=time_sensitive,
        requires_external_verification=externally_verifiable,
    )


class FakeGroundingClient:
    def __init__(self, response: GroundedClaimAnalysis | Exception) -> None:
        self.response = response
        self.calls: list[list[KnowledgeClaim]] = []

    def verify_claims(self, claims: list[KnowledgeClaim]) -> GroundedClaimAnalysis:
        self.calls.append(claims)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def verification(
    text: str, sources: list[EvidenceSource] | None = None
) -> GroundedClaimVerification:
    return GroundedClaimVerification(
        claim=text,
        verdict="SUPPORTED",
        confidence=0.9,
        explanation="The source supports this claim.",
        evidence_sources=sources or [],
    )


def test_only_eligible_claims_are_selected_and_capped() -> None:
    client = FakeGroundingClient(
        GroundedClaimAnalysis(
            verifications=[verification("Time-sensitive"), verification("External")]
        )
    )
    service = GroundedClaimVerificationService(
        Settings(grounding_max_claims=2),
        client,  # type: ignore[arg-type]
    )
    claims = [
        claim("Skip"),
        claim("Time-sensitive", time_sensitive=True),
        claim("External", externally_verifiable=True),
        claim("Beyond limit", externally_verifiable=True),
    ]

    results = service.verify(claims)

    assert [item.text for item in client.calls[0]] == ["Time-sensitive", "External"]
    assert [result.claim for result in results] == ["Time-sensitive", "External"]


def test_non_eligible_claims_skip_the_provider() -> None:
    client = FakeGroundingClient(GroundedClaimAnalysis(verifications=[]))
    service = GroundedClaimVerificationService(Settings(), client)  # type: ignore[arg-type]

    assert service.verify([claim("Static claim")]) == []
    assert client.calls == []


def test_valid_grounded_response_maps_to_provider_neutral_results() -> None:
    source = EvidenceSource(title="Gemini documentation", url="https://example.com/gemini")
    client = FakeGroundingClient(
        GroundedClaimAnalysis(verifications=[verification("Claim", [source])])
    )
    service = GroundedClaimVerificationService(Settings(), client)  # type: ignore[arg-type]

    result = service.verify([claim("Claim", externally_verifiable=True)])[0]

    assert result.claim == "Claim"
    assert result.verdict == "SUPPORTED"
    assert result.confidence == 0.9
    assert result.explanation == "The source supports this claim."
    assert result.evidence_sources == [source]
    assert isinstance(result.verified_at, datetime)
    assert "google" not in repr(result).lower()


def test_verdict_values_are_validated() -> None:
    with pytest.raises(ValueError):
        GroundedClaimVerification.model_validate(
            {
                "claim": "Claim",
                "verdict": "UNCERTAIN",
                "confidence": 0.5,
                "explanation": "Explanation",
            }
        )


def test_missing_citations_are_reported_as_insufficient_evidence() -> None:
    client = FakeGroundingClient(GroundedClaimAnalysis(verifications=[verification("Claim")]))
    service = GroundedClaimVerificationService(Settings(), client)  # type: ignore[arg-type]

    result = service.verify([claim("Claim", externally_verifiable=True)])[0]

    assert result.verdict == "INSUFFICIENT_EVIDENCE"


def test_provider_failures_use_the_safe_grounding_error() -> None:
    client = FakeGroundingClient(GeminiTransientError("provider detail"))
    service = GroundedClaimVerificationService(Settings(), client)  # type: ignore[arg-type]

    with pytest.raises(DomainError) as error:
        service.verify([claim("Claim", externally_verifiable=True)])

    assert error.value.code == "GROUNDING_FAILED"
    assert "provider detail" not in error.value.message
