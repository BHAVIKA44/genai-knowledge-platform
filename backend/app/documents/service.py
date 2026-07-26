import hashlib
import re
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
from app.documents.schemas import FindingSeverity, ValidationFinding
from app.documents.state import transition_status

SUPPORTED_TYPES: dict[str, tuple[DocumentType, set[str]]] = {
    ".md": (DocumentType.MARKDOWN, {"text/markdown", "text/plain"}),
    ".txt": (DocumentType.TEXT, {"text/plain"}),
    ".pdf": (DocumentType.PDF, {"application/pdf"}),
}
TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Large Language Models": ("large language model", "llm", "language model"),
    "Retrieval-Augmented Generation": ("retrieval augmented", "rag", "retrieval"),
    "Embeddings": ("embedding", "embeddings", "vector database", "vector search"),
    "Transformers": ("transformer", "attention mechanism", "self-attention"),
    "Prompt Engineering": ("prompt engineering", "prompt", "few-shot"),
    "Agents": ("agent", "tool calling", "model context protocol", "mcp"),
}
ENGLISH_MARKERS = {"the", "and", "for", "with", "that", "this", "from", "are", "is", "to"}
logger = structlog.get_logger()


def _finding(
    code: str, severity: FindingSeverity, title: str, explanation: str, action: str | None = None
) -> ValidationFinding:
    return ValidationFinding(
        code=code, severity=severity, title=title, explanation=explanation, suggested_action=action
    )


class DocumentIngestionService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

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
            title=title.strip() if title and title.strip() else Path(display_name).stem,
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
            findings, topics = self._validate_extracted_text(text, document.title)

            document = self.session.get(KnowledgeDocument, document_id)
            if document is None:
                return
            document.status = transition_status(document.status, DocumentStatus.VALIDATING)
            document.extracted_text = text
            document.validation_findings = [finding.model_dump() for finding in findings]
            document.detected_topics = topics
            document.updated_at = now_utc()
            self.session.add(document)
            self.session.commit()

            document.status = transition_status(document.status, self._route(findings))
            document.updated_at = now_utc()
            self.session.add(document)
            self.session.commit()
        except DomainError as error:
            self._fail(document_id, error.code, error.message, error.action)
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
            _finding(
                code,
                FindingSeverity.BLOCKING,
                "Document processing could not finish",
                message,
                action,
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

    def _validate_extracted_text(
        self, text: str, title: str
    ) -> tuple[list[ValidationFinding], list[str]]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            raise DomainError(
                "EMPTY_DOCUMENT",
                "This document does not contain readable text.",
                "Upload a document with selectable text.",
            )
        if len(re.sub(r"\W", "", normalized)) < self.settings.min_meaningful_characters:
            raise DomainError(
                "INSUFFICIENT_CONTENT",
                "This document does not contain enough useful text.",
                "Upload a document with at least 50 meaningful characters.",
            )

        lower_text = normalized.lower()
        words = re.findall(r"[a-zA-Z]+", lower_text)
        english_hits = sum(word in ENGLISH_MARKERS for word in words)
        if len(words) < 10 or english_hits == 0:
            raise DomainError(
                "UNSUPPORTED_LANGUAGE",
                "This document does not appear to be English-language content.",
                "Upload an English GenAI learning resource.",
            )

        topics = [
            topic
            for topic, keywords in TOPIC_KEYWORDS.items()
            if any(keyword in lower_text for keyword in keywords)
        ]
        if not topics:
            raise DomainError(
                "NON_GENAI_CONTENT",
                "This document does not appear to be about Generative AI.",
                (
                    "Upload a GenAI learning resource, such as material about LLMs, RAG, "
                    "embeddings, or agents."
                ),
            )

        findings: list[ValidationFinding] = []
        if not title.strip():
            findings.append(
                _finding(
                    "MISSING_TITLE",
                    FindingSeverity.WARNING,
                    "Title is missing",
                    "A title makes this knowledge easier to identify.",
                    "Add a clear title before publishing.",
                )
            )
        findings.append(
            _finding(
                "GENAI_RELEVANT",
                FindingSeverity.INFO,
                "GenAI relevance confirmed",
                "The document matches supported Generative AI topics.",
            )
        )
        return findings, topics

    @staticmethod
    def _route(findings: list[ValidationFinding]) -> DocumentStatus:
        if any(finding.severity is FindingSeverity.BLOCKING for finding in findings):
            return DocumentStatus.REJECTED
        if any(finding.severity is FindingSeverity.WARNING for finding in findings):
            return DocumentStatus.CONTRIBUTOR_REVIEW_REQUIRED
        return DocumentStatus.APPROVED
