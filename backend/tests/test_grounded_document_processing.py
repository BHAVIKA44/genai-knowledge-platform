from datetime import datetime
from typing import cast

import pytest

from app.core.errors import DomainError
from app.documents.models import DocumentStatus, KnowledgeDocument
from app.documents.routes import to_response
from app.documents.service import DocumentIngestionService
from app.grounding.service import ClaimVerificationResult, GroundedClaimVerificationService
from app.llm.models import EvidenceSource, KnowledgeAnalysis, KnowledgeClaim

VALID_GENAI_TEXT = (
    b"Large language models use transformer attention. Retrieval augmented generation uses "
    b"embeddings and a vector database for grounded answers."
)


class FakeGroundingService:
    def __init__(self, results: list[ClaimVerificationResult] | Exception) -> None:
        self.results = results
        self.calls: list[list[KnowledgeClaim]] = []

    def verify(self, claims: list[KnowledgeClaim]) -> list[ClaimVerificationResult]:
        self.calls.append(claims)
        if isinstance(self.results, Exception):
            raise self.results
        return self.results


def _analysis(*claims: KnowledgeClaim) -> KnowledgeAnalysis:
    return KnowledgeAnalysis(
        proposed_title=None,
        summary="A concise explanation of the document.",
        topics=["RAG"],
        claims=list(claims),
    )


def _claim(*, eligible: bool = True) -> KnowledgeClaim:
    return KnowledgeClaim(
        text="The current model supports structured output.",
        confidence=0.9,
        is_time_sensitive=eligible,
        requires_external_verification=False,
    )


def _result(verdict: str = "SUPPORTED") -> ClaimVerificationResult:
    return ClaimVerificationResult(
        claim="The current model supports structured output.",
        verdict=verdict,
        confidence=0.8,
        explanation="The available sources support this assessment.",
        evidence_sources=[
            EvidenceSource(title="Official documentation", url="https://example.com/docs")
        ],
        verified_at=datetime.fromisoformat("2026-07-26T00:00:00+00:00"),
    )


def _process(
    service: DocumentIngestionService,
    analysis_client: object,
    monkeypatch: pytest.MonkeyPatch,
    grounding: FakeGroundingService,
    analysis: KnowledgeAnalysis,
) -> KnowledgeDocument:
    monkeypatch.setattr(service, "_index", lambda _: None)
    service.grounding_service = cast(GroundedClaimVerificationService, grounding)
    monkeypatch.setattr(analysis_client, "analysis", analysis)
    document = service.submit("rag.md", VALID_GENAI_TEXT, "text/markdown", "RAG notes")
    service.process(document.id, VALID_GENAI_TEXT)
    stored = service.session.get(KnowledgeDocument, document.id)
    assert stored is not None
    return stored


def test_eligible_claims_are_grounded_persisted_and_exposed_safely(
    service: DocumentIngestionService, analysis_client: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    grounding = FakeGroundingService([_result()])

    stored = _process(service, analysis_client, monkeypatch, grounding, _analysis(_claim()))

    assert [claim.text for claim in grounding.calls[0]] == [_claim().text]
    assert stored.grounded_claim_verifications == [
        {
            "claim": "The current model supports structured output.",
            "verdict": "SUPPORTED",
            "confidence": 0.8,
            "explanation": "The available sources support this assessment.",
            "evidence_sources": [
                {"title": "Official documentation", "url": "https://example.com/docs"}
            ],
            "verified_at": "2026-07-26T00:00:00+00:00",
        }
    ]
    response = to_response(stored).model_dump()
    source = response["grounded_claim_verifications"][0]["evidence_sources"][0]
    assert set(source) == {"title", "url", "domain", "summary"}
    assert source["domain"] == "example.com"
    assert "grounding_metadata" not in str(response)
    assert "provider" not in str(response).lower()


def test_non_eligible_claims_skip_grounding_and_persist_an_empty_list(
    service: DocumentIngestionService, analysis_client: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    grounding = FakeGroundingService([])

    stored = _process(
        service, analysis_client, monkeypatch, grounding, _analysis(_claim(eligible=False))
    )

    assert grounding.calls == []
    assert stored.grounded_claim_verifications == []
    assert stored.status is DocumentStatus.APPROVED


def test_supported_claims_do_not_add_grounding_findings(
    service: DocumentIngestionService, analysis_client: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    stored = _process(
        service,
        analysis_client,
        monkeypatch,
        FakeGroundingService([_result()]),
        _analysis(_claim()),
    )

    assert not any(
        finding["code"].startswith("GROUNDED_CLAIM") for finding in stored.validation_findings
    )
    assert stored.status is DocumentStatus.APPROVED


@pytest.mark.parametrize(
    ("verdict", "severity", "expected_phrase"),
    [
        ("PARTIALLY_SUPPORTED", "WARNING", "partially supported"),
        ("NOT_SUPPORTED", "BLOCKING", "not supported"),
        ("INSUFFICIENT_EVIDENCE", "WARNING", "additional evidence"),
    ],
)
def test_grounded_verdicts_create_deterministic_review_findings(
    service: DocumentIngestionService,
    analysis_client: object,
    monkeypatch: pytest.MonkeyPatch,
    verdict: str,
    severity: str,
    expected_phrase: str,
) -> None:
    stored = _process(
        service,
        analysis_client,
        monkeypatch,
        FakeGroundingService([_result(verdict)]),
        _analysis(_claim()),
    )

    finding = next(
        item for item in stored.validation_findings if item["code"].startswith("GROUNDED_CLAIM")
    )
    assert stored.status is DocumentStatus.ADMIN_REVIEW_REQUIRED
    assert finding["severity"] == severity
    assert expected_phrase in finding["title"].lower()
    if verdict == "INSUFFICIENT_EVIDENCE":
        assert "false" not in finding["explanation"].lower()


def test_grounding_failure_routes_safely_without_provider_details(
    service: DocumentIngestionService, analysis_client: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    stored = _process(
        service,
        analysis_client,
        monkeypatch,
        FakeGroundingService(
            DomainError("GROUNDING_FAILED", "provider secret detail", "retry", 503)
        ),
        _analysis(_claim()),
    )

    finding = next(
        item for item in stored.validation_findings if item["code"] == "GROUNDING_FAILED"
    )
    assert stored.status is DocumentStatus.ADMIN_REVIEW_REQUIRED
    assert stored.grounded_claim_verifications == []
    assert "provider secret detail" not in str(finding)


def test_document_response_safelists_evidence_and_omits_unsafe_urls(
    service: DocumentIngestionService,
) -> None:
    document = service.submit("rag.md", VALID_GENAI_TEXT, "text/markdown", "RAG notes")
    document.grounded_claim_verifications = [
        {
            "claim": "A claim",
            "verdict": "INSUFFICIENT_EVIDENCE",
            "confidence": 0.4,
            "explanation": "Evidence was limited.",
            "verified_at": "2026-07-26T00:00:00+00:00",
            "provider_payload": {"secret": "do-not-return"},
            "evidence_sources": [
                {"title": "Unsafe", "url": "javascript:alert(1)"},
                {
                    "title": "Safe",
                    "url": "https://example.com/evidence",
                    "grounding_metadata": {"hidden": "value"},
                },
            ],
        }
    ]

    response = to_response(document).model_dump()

    verification = response["grounded_claim_verifications"][0]
    assert set(verification) == {
        "claim",
        "verdict",
        "confidence",
        "explanation",
        "evidence_sources",
        "verified_at",
    }
    assert verification["evidence_sources"] == [
        {
            "title": "Safe",
            "url": "https://example.com/evidence",
            "domain": "example.com",
            "summary": None,
        }
    ]
    assert "do-not-return" not in str(response)
    assert "grounding_metadata" not in str(response)
