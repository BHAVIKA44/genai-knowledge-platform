import fitz
import pytest
from sqlmodel import select

from app.core.errors import DomainError, InvalidStateTransitionError
from app.documents.models import DocumentStatus, KnowledgeDocument
from app.documents.state import transition_status

VALID_GENAI_TEXT = (
    b"Large language models use transformer attention. Retrieval augmented generation uses "
    b"embeddings and a vector database for grounded answers."
)


def test_valid_markdown_upload_becomes_approved(service) -> None:
    document = service.submit("rag.md", VALID_GENAI_TEXT, "text/markdown", "RAG notes")
    service.process(document.id, VALID_GENAI_TEXT)
    assert service.session.get(KnowledgeDocument, document.id).status is DocumentStatus.APPROVED


def test_valid_text_upload_becomes_approved(service) -> None:
    document = service.submit("agents.txt", VALID_GENAI_TEXT, "text/plain", "Agent notes")
    service.process(document.id, VALID_GENAI_TEXT)
    assert service.session.get(KnowledgeDocument, document.id).status is DocumentStatus.APPROVED


def test_zero_byte_file_is_rejected_before_persistence(service) -> None:
    with pytest.raises(DomainError, match="empty"):
        service.submit("empty.txt", b"", "text/plain", "Empty")
    assert service.session.exec(select(KnowledgeDocument)).first() is None


def test_whitespace_only_document_fails_safely(service) -> None:
    content = b" " * 100
    document = service.submit("empty.txt", content, "text/plain", "Empty")
    service.process(document.id, content)
    assert service.session.get(KnowledgeDocument, document.id).status is DocumentStatus.REJECTED


def test_short_document_fails_safely(service) -> None:
    content = b"LLM prompt"
    document = service.submit("short.txt", content, "text/plain", "Short")
    service.process(document.id, content)
    assert service.session.get(KnowledgeDocument, document.id).status is DocumentStatus.REJECTED


def test_unsupported_extension_is_rejected(service) -> None:
    with pytest.raises(DomainError) as error:
        service.submit("notes.docx", VALID_GENAI_TEXT, "text/plain", "Notes")
    assert error.value.code == "UNSUPPORTED_FILE_TYPE"


def test_mime_mismatch_is_rejected(service) -> None:
    with pytest.raises(DomainError) as error:
        service.submit("notes.md", VALID_GENAI_TEXT, "application/pdf", "Notes")
    assert error.value.code == "MIME_MISMATCH"


def test_oversized_upload_is_rejected(service) -> None:
    service.settings.max_upload_bytes = 5
    with pytest.raises(DomainError) as error:
        service.submit("notes.txt", VALID_GENAI_TEXT, "text/plain", "Notes")
    assert error.value.code == "DOCUMENT_TOO_LARGE"


def test_exact_duplicate_does_not_create_second_record(service) -> None:
    service.submit("one.txt", VALID_GENAI_TEXT, "text/plain", "One")
    with pytest.raises(DomainError) as error:
        service.submit("two.txt", VALID_GENAI_TEXT, "text/plain", "Two")
    assert error.value.code == "DUPLICATE_SUBMISSION"
    assert len(service.session.exec(select(KnowledgeDocument)).all()) == 1


def test_invalid_state_transition_is_rejected() -> None:
    with pytest.raises(InvalidStateTransitionError):
        transition_status(DocumentStatus.UPLOADED, DocumentStatus.APPROVED)


def test_non_genai_content_fails_safely(service) -> None:
    content = (
        b"The garden needs sunlight and water. Plant flowers in rich soil during spring "
        b"for a healthy garden."
    )
    document = service.submit("garden.txt", content, "text/plain", "Garden")
    service.process(document.id, content)
    assert service.session.get(KnowledgeDocument, document.id).status is DocumentStatus.REJECTED


def test_parser_failure_never_exposes_internal_exception(service, monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "_extract_text",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("hidden detail")),
    )
    document = service.submit("notes.txt", VALID_GENAI_TEXT, "text/plain", "Notes")
    service.process(document.id, VALID_GENAI_TEXT)
    finding = service.session.get(KnowledgeDocument, document.id).validation_findings[0]
    assert "hidden detail" not in str(finding)
    assert finding["code"] == "PROCESSING_FAILED"


def test_pdf_page_limit_is_rejected(service, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.documents.service.filetype.guess_mime", lambda *_args: "application/pdf"
    )
    document = fitz.open()
    for _ in range(2):
        document.new_page()
    content = document.tobytes()
    service.settings.max_pdf_pages = 1
    with pytest.raises(DomainError) as error:
        service.submit("large.pdf", content, "application/pdf", "Large")
    assert error.value.code == "DOCUMENT_TOO_LONG"


def test_supported_pdf_is_extracted_with_docling(service, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.documents.service.filetype.guess_mime", lambda *_args: "application/pdf"
    )

    class ExtractedDocument:
        def export_to_markdown(self) -> str:
            return VALID_GENAI_TEXT.decode()

    class ConversionResult:
        document = ExtractedDocument()

    class Converter:
        def convert(self, _: str) -> ConversionResult:
            return ConversionResult()

    monkeypatch.setattr("app.documents.service.DocumentConverter", Converter)
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), "Digital PDF")
    content = pdf.tobytes()
    document = service.submit("notes.pdf", content, "application/pdf", "PDF notes")
    service.process(document.id, content)
    stored = service.session.get(KnowledgeDocument, document.id)
    assert stored.status is DocumentStatus.APPROVED
    assert stored.extracted_text == VALID_GENAI_TEXT.decode()
