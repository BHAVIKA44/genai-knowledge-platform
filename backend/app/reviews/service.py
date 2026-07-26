from sqlmodel import Session

from app.core.errors import DomainError
from app.documents.models import DocumentStatus, KnowledgeDocument, now_utc
from app.documents.state import transition_status
from app.knowledge_quality.models import FindingSeverity, QualityFinding


class ContributorReviewService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_details(self, document_id: str) -> tuple[KnowledgeDocument, QualityFinding]:
        document = self._get_document(document_id)
        if document.status is not DocumentStatus.CONTRIBUTOR_REVIEW_REQUIRED:
            raise DomainError(
                "INVALID_REVIEW_STATE",
                "This document is not waiting for your review.",
                "Return to the document result to see its current status.",
                409,
            )
        return document, self._correction_finding(document)

    def decide(self, document_id: str, action: str) -> KnowledgeDocument:
        document = self._get_document(document_id)
        if document.contributor_review_decision == action:
            return document
        if document.status is not DocumentStatus.CONTRIBUTOR_REVIEW_REQUIRED:
            raise DomainError(
                "INVALID_REVIEW_STATE",
                "This document is not waiting for your review.",
                "Return to the document result to see its current status.",
                409,
            )
        finding = self._correction_finding(document)
        if action not in {"ACCEPT", "DECLINE"}:
            raise DomainError(
                "INVALID_REVIEW_ACTION", "That review action is not supported.", status_code=422
            )

        try:
            if action == "ACCEPT":
                document.title = finding.suggested_value or ""
                document.validation_findings = [
                    item
                    for item in document.validation_findings
                    if item.get("code") != finding.code
                ]
                unresolved_blocking = any(
                    item.get("severity") == FindingSeverity.BLOCKING
                    for item in document.validation_findings
                )
                target = DocumentStatus.REJECTED if unresolved_blocking else DocumentStatus.APPROVED
            else:
                target = DocumentStatus.REJECTED
            document.status = transition_status(document.status, target)
            document.contributor_review_decision = action
            document.updated_at = now_utc()
            self.session.add(document)
            self.session.commit()
            self.session.refresh(document)
            return document
        except Exception:
            self.session.rollback()
            raise

    def _get_document(self, document_id: str) -> KnowledgeDocument:
        document = self.session.get(KnowledgeDocument, document_id)
        if document is None:
            raise DomainError(
                "DOCUMENT_NOT_FOUND", "We could not find that document.", status_code=404
            )
        return document

    @staticmethod
    def _correction_finding(document: KnowledgeDocument) -> QualityFinding:
        for stored_finding in document.validation_findings:
            finding = QualityFinding.model_validate(stored_finding)
            if finding.suggested_value and finding.severity is FindingSeverity.WARNING:
                return finding
        raise DomainError(
            "NO_CORRECTION_AVAILABLE",
            "This document does not have a correction ready for review.",
            status_code=409,
        )
