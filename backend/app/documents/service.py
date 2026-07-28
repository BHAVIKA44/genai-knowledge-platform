import hashlib
import re
import time
from pathlib import Path
from uuid import uuid4

import filetype
import fitz
import structlog
from sqlmodel import Session, select

from app.core.config import Settings
from app.core.errors import DomainError
from app.documents.chunk_repository import DocumentChunkRepository
from app.documents.chunking import DocumentChunkingService
from app.documents.indexing import DocumentIndexingService
from app.documents.models import DocumentStatus, DocumentType, KnowledgeDocument, now_utc
from app.documents.source_storage import LocalSourceStorage
from app.documents.state import transition_status
from app.documents.stored_document_parser import StoredDocumentParser
from app.embeddings import DocumentEmbedder
from app.grounding.service import ClaimVerificationResult, GroundedClaimVerificationService
from app.knowledge_quality.engine import KnowledgeQualityEngine, ValidatorExecutionError
from app.knowledge_quality.models import (
    FindingCategory,
    FindingSeverity,
    QualityFinding,
    QualityValidationInput,
)
from app.llm.client import (
    GeminiConfigurationError,
    GeminiInvalidResponseError,
    GeminiKnowledgeClient,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiTransientError,
)
from app.llm.models import KnowledgeAnalysis

SUPPORTED_TYPES: dict[str, tuple[DocumentType, set[str]]] = {
    ".md": (DocumentType.MARKDOWN, {"text/markdown", "text/plain"}),
    ".txt": (DocumentType.TEXT, {"text/plain"}),
    ".pdf": (DocumentType.PDF, {"application/pdf"}),
}
logger = structlog.get_logger()


class DocumentIngestionService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        quality_engine: KnowledgeQualityEngine | None = None,
        analysis_client: GeminiKnowledgeClient | None = None,
        source_storage: LocalSourceStorage | None = None,
        grounding_service: GroundedClaimVerificationService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.quality_engine = quality_engine or KnowledgeQualityEngine(settings)
        self.analysis_client = analysis_client or GeminiKnowledgeClient(settings)
        self.source_storage = source_storage or LocalSourceStorage(settings.source_storage_root)
        self.stored_document_parser = StoredDocumentParser(self.source_storage)
        self.grounding_service = grounding_service or GroundedClaimVerificationService(
            settings, self.analysis_client
        )

    def submit(
        self, filename: str, content: bytes, declared_mime: str | None, title: str | None
    ) -> KnowledgeDocument:
        document_type = self._validate_upload(filename, content, declared_mime)
        digest = hashlib.sha256(content).hexdigest()
        existing = self.session.exec(
            select(KnowledgeDocument).where(KnowledgeDocument.sha256 == digest)
        ).first()
        if existing:
            raise DomainError(
                "DUPLICATE_SUBMISSION",
                "This exact document has already been uploaded.",
                "Please upload a different version if you made changes.",
                409,
            )

        display_name = Path(filename).name or "uploaded-document"
        source_key = self.source_storage.save(content, Path(display_name).suffix)
        fallback_title = self._fallback_title(display_name)
        document = KnowledgeDocument(
            title=title.strip() if title and title.strip() else fallback_title,
            source_filename=display_name,
            storage_filename=f"{uuid4()}{Path(display_name).suffix.lower()}",
            source_storage_key=source_key,
            document_type=document_type,
            status=DocumentStatus.UPLOADED,
            sha256=digest,
        )
        try:
            self.session.add(document)
            self.session.commit()
            self.session.refresh(document)
        except Exception:
            self.session.rollback()
            self.source_storage.delete(source_key)
            raise
        return document

    def process(self, document_id: str, content: bytes) -> None:
        document = self.session.get(KnowledgeDocument, document_id)
        if document is None:
            return
        try:
            document.status = transition_status(document.status, DocumentStatus.PROCESSING)
            document.updated_at = now_utc()
            self.session.add(document)
            self.session.commit()

            parsed_document = self.stored_document_parser.parse(
                document.source_storage_key, document.document_type
            )
            text = parsed_document.text
            if document.title == self._fallback_title(document.source_filename):
                document.title = self._extracted_title(text) or document.title
            quality_result = self.quality_engine.validate(
                QualityValidationInput(
                    title=document.title,
                    source_filename=document.source_filename,
                    extracted_text=text,
                    document_type=document.document_type,
                )
            )

            document = self.session.get(KnowledgeDocument, document_id)
            if document is None:
                return
            document.status = transition_status(document.status, DocumentStatus.VALIDATING)
            document.extracted_text = text
            document.validation_findings = [
                finding.model_dump() for finding in quality_result.findings
            ]
            document.detected_topics = quality_result.detected_topics
            document.updated_at = now_utc()
            self.session.add(document)
            self.session.commit()

            target_status = DocumentStatus(quality_result.recommended_routing)
            if target_status is DocumentStatus.REJECTED:
                self._complete_processing(document, target_status)
                return

            analysis = self._analyze(document, text)
            semantic_findings = self._semantic_findings(analysis)
            title_correction = self._title_correction(document, analysis)
            processing_findings = [*semantic_findings, *title_correction]
            document.validation_findings = [
                *document.validation_findings,
                *(finding.model_dump() for finding in processing_findings),
            ]
            grounding_results, grounding_findings = self._ground_claims(analysis)
            document.validation_findings = [
                *document.validation_findings,
                *(finding.model_dump() for finding in grounding_findings),
            ]
            all_processing_findings = [*processing_findings, *grounding_findings]
            requires_contributor_review = self._requires_contributor_review(processing_findings)
            has_unstructured_blocking_finding = any(
                finding.severity is FindingSeverity.BLOCKING and finding.code != "TITLE_CORRECTION"
                for finding in all_processing_findings
            )
            if (
                any(finding.admin_review_required for finding in all_processing_findings)
                or has_unstructured_blocking_finding
            ):
                target_status = DocumentStatus.ADMIN_REVIEW_REQUIRED
            elif requires_contributor_review and target_status is DocumentStatus.APPROVED:
                target_status = DocumentStatus.CONTRIBUTOR_REVIEW_REQUIRED
            self._persist_analysis(document, analysis, grounding_results, target_status)
        except DomainError as error:
            self._fail(document_id, error.code, error.message, error.action)
        except ValidatorExecutionError:
            self._fail(
                document_id,
                "QUALITY_VALIDATION_FAILED",
                "We could not validate this document safely.",
                "Please try again shortly.",
            )
        except (
            GeminiConfigurationError,
            GeminiInvalidResponseError,
            GeminiRateLimitError,
            GeminiTimeoutError,
            GeminiTransientError,
        ):
            self._fail(
                document_id,
                "ANALYSIS_FAILED",
                "We could not finish analyzing this resource right now.",
                "Please try again shortly.",
            )
        except Exception as error:
            logger.error(
                "document_processing_failed",
                document_id=document_id,
                failure_category=type(error).__name__,
            )
            self._fail(
                document_id,
                "PROCESSING_FAILED",
                "We could not process this document safely.",
                "Please try a clean digital PDF or a plain-text file.",
            )

    def _analyze(self, document: KnowledgeDocument, text: str) -> KnowledgeAnalysis:
        started_at = time.monotonic()
        try:
            return self.analysis_client.analyze_document(text)
        except Exception as error:
            logger.error(
                "document_analysis_failed",
                document_id=document.id,
                model=self.analysis_client.model,
                prompt_version=self.analysis_client.prompt_version,
                failure_category=type(error).__name__,
                elapsed_ms=round((time.monotonic() - started_at) * 1000),
            )
            raise

    def _persist_analysis(
        self,
        document: KnowledgeDocument,
        analysis: KnowledgeAnalysis,
        grounding_results: list[ClaimVerificationResult],
        target_status: DocumentStatus,
    ) -> None:
        document.analysis_summary = analysis.summary
        document.analysis_topics = analysis.topics
        document.analysis_claims = [claim.model_dump() for claim in analysis.claims]
        document.analysis_proposed_title = analysis.proposed_title
        document.analysis_model = self.analysis_client.model
        document.analysis_prompt_version = self.analysis_client.prompt_version
        document.analyzed_at = now_utc()
        document.grounded_claim_verifications = [
            {
                "claim": result.claim,
                "verdict": result.verdict,
                "confidence": result.confidence,
                "explanation": result.explanation,
                "evidence_sources": [source.model_dump() for source in result.evidence_sources],
                "verified_at": result.verified_at.isoformat(),
            }
            for result in grounding_results
        ]
        if target_status is DocumentStatus.APPROVED:
            self._index(document)
        self._complete_processing(document, target_status)

    def _index(self, document: KnowledgeDocument) -> None:
        DocumentIndexingService(
            self.session,
            self.stored_document_parser,
            DocumentChunkingService(),
            DocumentEmbedder(),
            DocumentChunkRepository(self.session),
        ).index(document)

    @staticmethod
    def _semantic_findings(analysis: KnowledgeAnalysis) -> list[QualityFinding]:
        return [
            QualityFinding(
                code=f"SEMANTIC_{index}",
                category=FindingCategory.SEMANTIC_QUALITY,
                severity=FindingSeverity(finding.severity),
                confidence=finding.confidence,
                title=finding.category.replace("_", " ").title(),
                explanation=finding.explanation,
                suggested_action=finding.suggested_improvement,
                original_value="" if "title" in finding.category.casefold() else None,
                suggested_value=(
                    analysis.proposed_title
                    if "title" in finding.category.casefold() and analysis.proposed_title
                    else None
                ),
                admin_review_required=finding.admin_review_required,
            )
            for index, finding in enumerate(analysis.semantic_findings, start=1)
            if not ("title" in finding.category.casefold() and analysis.proposed_title)
        ]

    @staticmethod
    def _requires_contributor_review(findings: list[QualityFinding]) -> bool:
        return any(
            finding.code == "TITLE_CORRECTION"
            and finding.severity is FindingSeverity.BLOCKING
            and finding.suggested_value
            for finding in findings
        )

    def _title_correction(
        self, document: KnowledgeDocument, analysis: KnowledgeAnalysis
    ) -> list[QualityFinding]:
        fallback_title = self._fallback_title(document.source_filename)
        proposed_title = " ".join((analysis.proposed_title or "").split())
        if (
            document.title != fallback_title
            or not proposed_title
            or proposed_title.casefold() == fallback_title.casefold()
        ):
            return []
        return [
            QualityFinding(
                code="TITLE_CORRECTION",
                category=FindingCategory.METADATA,
                severity=FindingSeverity.BLOCKING,
                confidence=1,
                title="A clearer title is needed",
                explanation="Please confirm the suggested title before publication.",
                suggested_action="Use the suggested title.",
                original_value="",
                suggested_value=proposed_title,
            )
        ]

    @staticmethod
    def _fallback_title(filename: str) -> str:
        cleaned = re.sub(r"[_-]+", " ", Path(filename).stem).strip()
        return cleaned or "Uploaded document"

    @staticmethod
    def _extracted_title(text: str) -> str | None:
        match = re.search(r"^\s*#\s+(.+?)\s*$", text, flags=re.MULTILINE)
        if not match:
            return None
        title = " ".join(match.group(1).split())
        return title[:200] or None

    def _ground_claims(
        self, analysis: KnowledgeAnalysis
    ) -> tuple[list[ClaimVerificationResult], list[QualityFinding]]:
        eligible_claims = [
            claim
            for claim in analysis.claims
            if claim.is_time_sensitive or claim.requires_external_verification
        ]
        if not eligible_claims:
            return [], []
        try:
            results = self.grounding_service.verify(eligible_claims)
        except DomainError as error:
            if error.code != "GROUNDING_FAILED":
                raise
            return [], [
                QualityFinding(
                    code="GROUNDING_FAILED",
                    category=FindingCategory.SEMANTIC_QUALITY,
                    severity=FindingSeverity.WARNING,
                    confidence=1,
                    title="Claim verification could not finish",
                    explanation="We could not verify the time-sensitive claims in this document.",
                    suggested_action="External references could not be checked right now.",
                )
            ]
        return results, self._grounding_findings(results)

    @staticmethod
    def _grounding_findings(results: list[ClaimVerificationResult]) -> list[QualityFinding]:
        findings = []
        for index, result in enumerate(results, start=1):
            if result.verdict == "SUPPORTED":
                continue
            if result.verdict == "NOT_SUPPORTED":
                severity = FindingSeverity.BLOCKING
                title = "Claim is not supported by grounded evidence"
            elif result.verdict == "INSUFFICIENT_EVIDENCE":
                severity = FindingSeverity.WARNING
                title = "Claim requires additional evidence"
            else:
                severity = FindingSeverity.WARNING
                title = "Claim is only partially supported"
            findings.append(
                QualityFinding(
                    code=f"GROUNDED_CLAIM_{index}",
                    category=FindingCategory.SEMANTIC_QUALITY,
                    severity=severity,
                    confidence=result.confidence,
                    title=title,
                    explanation=result.explanation,
                    suggested_action=(
                        "An administrator should review the available evidence."
                        if result.verdict == "NOT_SUPPORTED"
                        else "Consider adding clearer supporting context."
                    ),
                    admin_review_required=result.verdict == "NOT_SUPPORTED",
                )
            )
        return findings

    def _complete_processing(
        self, document: KnowledgeDocument, target_status: DocumentStatus
    ) -> None:
        document.status = transition_status(document.status, target_status)
        document.updated_at = now_utc()
        self.session.add(document)
        self.session.commit()

    def _fail(self, document_id: str, code: str, message: str, action: str | None) -> None:
        self.session.rollback()
        document = self.session.get(KnowledgeDocument, document_id)
        if document is None or document.status in {DocumentStatus.REJECTED, DocumentStatus.FAILED}:
            return
        document.status = transition_status(document.status, DocumentStatus.FAILED)
        document.validation_findings = [
            QualityFinding(
                code=code,
                category=FindingCategory.EXTRACTION_QUALITY,
                severity=FindingSeverity.BLOCKING,
                confidence=1,
                title="Document processing could not finish",
                explanation=message,
                suggested_action=action,
            ).model_dump()
        ]
        document.updated_at = now_utc()
        self.session.add(document)
        self.session.commit()

    def _validate_upload(
        self, filename: str, content: bytes, declared_mime: str | None
    ) -> DocumentType:
        suffix = Path(filename).suffix.lower()
        supported = SUPPORTED_TYPES.get(suffix)
        if supported is None:
            raise DomainError(
                "UNSUPPORTED_FILE_TYPE",
                "This file type is not supported.",
                "Upload a .md, .txt, or digital .pdf file.",
                415,
            )
        if not content:
            raise DomainError(
                "EMPTY_DOCUMENT",
                "This file is empty.",
                "Upload a document containing GenAI learning content.",
            )
        if len(content) > self.settings.max_upload_bytes:
            raise DomainError(
                "DOCUMENT_TOO_LARGE",
                "This file is larger than the 10 MB limit.",
                "Choose a smaller file or split it into parts.",
                413,
            )
        detected_mime = filetype.guess_mime(content) or "text/plain"
        document_type, accepted_mimes = supported
        if declared_mime and declared_mime not in accepted_mimes:
            raise DomainError(
                "MIME_MISMATCH",
                "The file content does not match its declared type.",
                "Upload the original file without renaming it.",
                415,
            )
        if detected_mime not in accepted_mimes:
            raise DomainError(
                "MIME_MISMATCH",
                "The file content does not match its extension.",
                "Upload the original file without renaming it.",
                415,
            )
        if document_type is DocumentType.PDF:
            try:
                with fitz.open(stream=content, filetype="pdf") as pdf:
                    if pdf.page_count > self.settings.max_pdf_pages:
                        raise DomainError(
                            "DOCUMENT_TOO_LONG",
                            "This PDF exceeds the 50-page limit.",
                            "Split it into smaller PDFs and try again.",
                        )
            except DomainError:
                raise
            except Exception as error:
                raise DomainError(
                    "UNREADABLE_DOCUMENT",
                    "This PDF could not be read.",
                    "Upload a clean, digitally generated PDF.",
                ) from error
        return document_type
