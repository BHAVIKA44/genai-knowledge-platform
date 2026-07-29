from collections.abc import Sequence
from typing import Protocol

import structlog

from app.core.config import Settings
from app.knowledge_quality.models import (
    FindingSeverity,
    QualityFinding,
    QualityValidationInput,
    QualityValidationResult,
    RecommendedRouting,
    ValidatorResult,
)
from app.knowledge_quality.validators import (
    DeterministicCorrectionValidator,
    DomainRelevanceValidator,
    DuplicateValidator,
    ExtractionQualityValidator,
    LearningMaterialValidator,
)

logger = structlog.get_logger()


class ValidatorExecutionError(Exception):
    pass


class QualityValidator(Protocol):
    def validate(self, value: QualityValidationInput) -> ValidatorResult: ...


class KnowledgeQualityEngine:
    def __init__(
        self, settings: Settings, validators: Sequence[QualityValidator] | None = None
    ) -> None:
        self.low_confidence_review_threshold = settings.low_confidence_review_threshold
        self.validators: list[QualityValidator] = (
            list(validators)
            if validators is not None
            else [
                ExtractionQualityValidator(settings),
                DomainRelevanceValidator(),
                LearningMaterialValidator(),
                DeterministicCorrectionValidator(),
                DuplicateValidator(),
            ]
        )

    def validate(self, value: QualityValidationInput) -> QualityValidationResult:
        findings = []
        topics: set[str] = set()
        for validator in self.validators:
            try:
                result = validator.validate(value)
            except Exception as error:
                logger.exception(
                    "knowledge_quality_validator_failed", validator=type(validator).__name__
                )
                raise ValidatorExecutionError("A quality validator could not complete.") from error
            if not isinstance(result, ValidatorResult):
                logger.error(
                    "knowledge_quality_validator_returned_invalid_result",
                    validator=type(validator).__name__,
                )
                raise ValidatorExecutionError("A quality validator returned an invalid result.")
            findings.extend(result.findings)
            topics.update(result.detected_topics)

        ordered_findings = sorted(findings, key=lambda finding: (finding.severity, finding.code))
        blocking_issues = [
            finding for finding in ordered_findings if finding.severity is FindingSeverity.BLOCKING
        ]
        warning_count = sum(
            finding.severity is FindingSeverity.WARNING for finding in ordered_findings
        )
        overall_confidence = (
            min(finding.confidence for finding in ordered_findings) if ordered_findings else 1.0
        )
        return QualityValidationResult(
            findings=ordered_findings,
            blocking_issues=blocking_issues,
            warning_count=warning_count,
            overall_confidence=overall_confidence,
            recommended_routing=self._route(ordered_findings, blocking_issues, overall_confidence),
            detected_topics=sorted(topics),
        )

    def _route(
        self,
        findings: list[QualityFinding],
        blocking_issues: list[QualityFinding],
        overall_confidence: float,
    ) -> RecommendedRouting:
        if blocking_issues:
            return RecommendedRouting.REJECTED
        if any(finding.code.startswith("DETERMINISTIC_") for finding in findings):
            return RecommendedRouting.CONTRIBUTOR_REVIEW_REQUIRED
        if overall_confidence < self.low_confidence_review_threshold:
            return RecommendedRouting.ADMIN_REVIEW_REQUIRED
        return RecommendedRouting.APPROVED
