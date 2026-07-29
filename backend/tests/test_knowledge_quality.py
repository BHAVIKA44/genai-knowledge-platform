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
        "uses embeddings and a vector database for grounded answers. It retrieves relevant "
        "passages before a model responds, which helps people verify claims against reviewed "
        "context."
    ),
    document_type=DocumentType.MARKDOWN,
)


def test_complete_metadata_and_relevant_content_is_approved() -> None:
    result = KnowledgeQualityEngine(Settings()).validate(VALID_INPUT)
    assert result.recommended_routing is RecommendedRouting.APPROVED
    assert result.warning_count == 0
    assert result.detected_topics


def test_missing_title_is_a_non_blocking_suggestion() -> None:
    result = KnowledgeQualityEngine(Settings()).validate(
        VALID_INPUT.model_copy(update={"title": ""})
    )
    assert result.recommended_routing is RecommendedRouting.APPROVED
    assert [finding.code for finding in result.findings] == ["GENAI_RELEVANT"]


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


def test_generative_ai_content_is_within_the_supported_scope() -> None:
    result = KnowledgeQualityEngine(Settings()).validate(
        VALID_INPUT.model_copy(
            update={
                "extracted_text": (
                    "Generative AI evaluation helps teams assess whether model responses are "
                    "useful, clear, and grounded in approved context. Teams can use the "
                    "results to compare retrieval quality, answer relevance, and factual "
                    "support across different prompts."
                )
            }
        )
    )
    assert result.recommended_routing is RecommendedRouting.APPROVED
    assert "Generative AI" in result.detected_topics


def test_english_genai_content_with_common_short_words_is_not_rejected_as_non_english() -> None:
    result = KnowledgeQualityEngine(Settings()).validate(
        VALID_INPUT.model_copy(
            update={
                "extracted_text": (
                    "Generative AI retrieval retrieves approved context before a language model "
                    "answers. Engineers evaluate source relevance and citations."
                )
            }
        )
    )
    assert not any(finding.code == "UNSUPPORTED_LANGUAGE" for finding in result.findings)


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


def test_minor_warnings_do_not_block_otherwise_approved_content() -> None:
    warning = QualityFinding(
        code="MISSING_CONTEXT",
        category=FindingCategory.SEMANTIC_QUALITY,
        severity=FindingSeverity.WARNING,
        confidence=0.9,
        title="More context would help",
        explanation="The definition could be more complete.",
    )

    class WarningValidator:
        def validate(self, _: QualityValidationInput) -> ValidatorResult:
            return ValidatorResult(findings=[warning])

    result = KnowledgeQualityEngine(Settings(), [WarningValidator()]).validate(VALID_INPUT)
    assert result.recommended_routing is RecommendedRouting.APPROVED


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
