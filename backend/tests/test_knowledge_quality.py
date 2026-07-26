from typing import cast

from app.core.config import Settings
from app.documents.models import DocumentType
from app.knowledge_quality.engine import (
    KnowledgeQualityEngine,
    QualityValidator,
    ValidatorExecutionError,
)
from app.knowledge_quality.models import (
    FindingCategory,
    FindingSeverity,
    QualityFinding,
    QualityValidationInput,
    RecommendedRouting,
    ValidatorResult,
)

VALID_INPUT = QualityValidationInput(
    title="RAG notes",
    source_filename="rag-notes.md",
    extracted_text=(
        "Large language models use transformer attention. Retrieval augmented generation "
        "uses embeddings and a vector database for grounded answers."
    ),
    document_type=DocumentType.MARKDOWN,
)


def test_complete_metadata_and_relevant_content_is_approved() -> None:
    result = KnowledgeQualityEngine(Settings()).validate(VALID_INPUT)
    assert result.recommended_routing is RecommendedRouting.APPROVED
    assert result.warning_count == 0
    assert result.detected_topics


def test_missing_title_requires_contributor_review() -> None:
    result = KnowledgeQualityEngine(Settings()).validate(
        VALID_INPUT.model_copy(update={"title": ""})
    )
    assert result.recommended_routing is RecommendedRouting.CONTRIBUTOR_REVIEW_REQUIRED
    assert [finding.code for finding in result.findings] == ["GENAI_RELEVANT", "MISSING_TITLE"]


def test_non_genai_document_is_rejected() -> None:
    result = KnowledgeQualityEngine(Settings()).validate(
        VALID_INPUT.model_copy(
            update={
                "extracted_text": (
                    "The garden needs sunlight and water. Plant flowers in rich soil during spring."
                )
            }
        )
    )
    assert result.recommended_routing is RecommendedRouting.REJECTED
    assert any(finding.code == "NON_GENAI_CONTENT" for finding in result.blocking_issues)


def test_blocking_finding_overrides_other_routing_signals() -> None:
    blocking = QualityFinding(
        code="BLOCKED",
        category=FindingCategory.DUPLICATE,
        severity=FindingSeverity.BLOCKING,
        confidence=1,
        title="Blocked",
        explanation="Blocked",
    )
    warning = QualityFinding(
        code="WARN",
        category=FindingCategory.METADATA,
        severity=FindingSeverity.WARNING,
        confidence=1,
        title="Warning",
        explanation="Warning",
    )

    class BlockingValidator:
        def validate(self, _: QualityValidationInput) -> ValidatorResult:
            return ValidatorResult(findings=[blocking, warning])

    result = KnowledgeQualityEngine(Settings(), [BlockingValidator()]).validate(VALID_INPUT)
    assert result.recommended_routing is RecommendedRouting.REJECTED
    assert result.warning_count == 1
    assert result.blocking_issues == [blocking]


def test_validator_order_does_not_change_routing() -> None:
    warning = QualityFinding(
        code="WARN",
        category=FindingCategory.METADATA,
        severity=FindingSeverity.WARNING,
        confidence=1,
        title="Warning",
        explanation="Warning",
    )
    info = QualityFinding(
        code="INFO",
        category=FindingCategory.METADATA,
        severity=FindingSeverity.INFO,
        confidence=0.9,
        title="Info",
        explanation="Info",
    )

    class WarningValidator:
        def validate(self, _: QualityValidationInput) -> ValidatorResult:
            return ValidatorResult(findings=[warning])

    class InfoValidator:
        def validate(self, _: QualityValidationInput) -> ValidatorResult:
            return ValidatorResult(findings=[info])

    first = KnowledgeQualityEngine(Settings(), [WarningValidator(), InfoValidator()]).validate(
        VALID_INPUT
    )
    second = KnowledgeQualityEngine(Settings(), [InfoValidator(), WarningValidator()]).validate(
        VALID_INPUT
    )
    assert first.recommended_routing is second.recommended_routing
    assert first.findings == second.findings


def test_invalid_validator_result_fails_safely() -> None:
    class InvalidValidator:
        def validate(self, _: QualityValidationInput) -> object:
            return {"findings": []}

    try:
        KnowledgeQualityEngine(Settings(), [cast(QualityValidator, InvalidValidator())]).validate(
            VALID_INPUT
        )
    except ValidatorExecutionError:
        return
    raise AssertionError("Invalid validator output must fail safely")
