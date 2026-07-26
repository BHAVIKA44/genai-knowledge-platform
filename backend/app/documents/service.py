import hashlib
import tempfile
from pathlib import Path
from uuid import uuid4

import filetype
import fitz
import structlog
from docling.document_converter import DocumentConverter
from sqlmodel import Session, select

from app.core.config import Settings
from app.core.errors import DomainError
from app.documents.models import DocumentStatus, DocumentType, KnowledgeDocument, now_utc
from app.documents.state import transition_status
from app.knowledge_quality.engine import KnowledgeQualityEngine, ValidatorExecutionError
from app.knowledge_quality.models import (
    FindingCategory,
    FindingSeverity,
    QualityFinding,
    QualityValidationInput,
)

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
    ) -> None:
        self.session = session
        self.settings = settings
        self.quality_engine = quality_engine or KnowledgeQualityEngine(settings)

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
                "This exact document has already been submitted.",
                "Open the existing document instead of uploading it again.",
                409,
            )

        display_name = Path(filename).name or "uploaded-document"
        document = KnowledgeDocument(
            title=title.strip() if title and title.strip() else "",
            source_filename=display_name,
            storage_filename=f"{uuid4()}{Path(display_name).suffix.lower()}",
            document_type=document_type,
            status=DocumentStatus.UPLOADED,
            sha256=digest,
        )
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
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

            text = self._extract_text(document.document_type, document.source_filename, content)
            quality_result = self.quality_engine.validate(
                QualityValidationInput(
                    title=document.title,
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

            document.status = transition_status(
                document.status, DocumentStatus(quality_result.recommended_routing)
            )
            document.updated_at = now_utc()
            self.session.add(document)
            self.session.commit()
        except DomainError as error:
            self._fail(document_id, error.code, error.message, error.action)
        except ValidatorExecutionError:
            self._fail(
                document_id,
                "QUALITY_VALIDATION_FAILED",
                "We could not validate this document safely.",
                "Please try again shortly.",
            )
        except Exception:
            logger.exception("document_processing_failed", document_id=document_id)
            self._fail(
                document_id,
                "PROCESSING_FAILED",
                "We could not process this document safely.",
                "Please try a clean digital PDF or a plain-text file.",
            )

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

    def _extract_text(self, document_type: DocumentType, filename: str, content: bytes) -> str:
        if document_type in {DocumentType.TEXT, DocumentType.MARKDOWN}:
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError as error:
                raise DomainError(
                    "UNREADABLE_DOCUMENT",
                    "This text file could not be read as UTF-8.",
                    "Save it as a UTF-8 text file and try again.",
                ) from error

        with tempfile.NamedTemporaryFile(suffix=".pdf") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            try:
                result = DocumentConverter().convert(temporary_file.name)
                return result.document.export_to_markdown()
            except Exception as error:
                raise DomainError(
                    "UNREADABLE_DOCUMENT",
                    "We could not reliably read this PDF.",
                    "Upload a clean, digitally generated PDF.",
                ) from error
