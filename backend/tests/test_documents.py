import fitz
import pytest
from sqlmodel import select

from app.core.errors import DomainError, InvalidStateTransitionError
from app.documents.models import DocumentStatus, KnowledgeDocument
from app.documents.routes import to_response
from app.documents.state import transition_status
from app.llm.client import GeminiTimeoutError
from app.llm.models import KnowledgeAnalysis

VALID_GENAI_TEXT = (
    b"Large language models use transformer attention. Retrieval augmented generation uses "
    b"embeddings and a vector database for grounded answers."
)


def test_valid_markdown_upload_becomes_approved(service) -> None:
    document = service.submit("rag.md", VALID_GENAI_TEXT, "text/markdown", "RAG notes")
    service.process(document.id, VALID_GENAI_TEXT)
    assert service.session.get(KnowledgeDocument, document.id).status is DocumentStatus.APPROVED


def test_only_approved_upload_invokes_indexing(service, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "app.documents.service.DocumentIndexingService",
        lambda *_: type("Indexer", (), {"index": lambda _, document: calls.append(document.id)})(),
    )
    document = service.submit("rag.md", VALID_GENAI_TEXT, "text/markdown", "RAG")
    service.process(document.id, VALID_GENAI_TEXT)
    assert calls == [document.id]


@pytest.mark.parametrize(
    ("title", "content"),
    [
        ("Garden", b"The garden needs sunlight and water for healthy flowers in spring."),
        (None, VALID_GENAI_TEXT),
    ],
)
def test_non_approved_upload_skips_indexing(service, monkeypatch, title, content) -> None:
    monkeypatch.setattr(
        "app.documents.service.DocumentIndexingService",
        lambda *_: pytest.fail("indexer constructed"),
    )
    document = service.submit("notes.txt", content, "text/plain", title)
    service.process(document.id, content)
    assert service.session.get(KnowledgeDocument, document.id).status is not DocumentStatus.APPROVED


def test_analysis_is_persisted_without_changing_deterministic_routing(
    service, analysis_client
) -> None:
    analysis_client.analysis = KnowledgeAnalysis(
        proposed_title="Gemini title",
        summary="Structured summary",
        topics=["RAG", "LLMs"],
        claims=[
            {
                "text": "RAG uses retrieved context.",
                "confidence": 0.9,
                "is_time_sensitive": False,
                "requires_external_verification": False,
            }
        ],
    )
    document = service.submit("rag.md", VALID_GENAI_TEXT, "text/markdown", "Existing title")
    service.process(document.id, VALID_GENAI_TEXT)
    stored = service.session.get(KnowledgeDocument, document.id)
    assert stored.status is DocumentStatus.APPROVED
    assert stored.title == "Existing title"
    assert stored.analysis_proposed_title == "Gemini title"
    assert stored.analysis_summary == "Structured summary"
    assert stored.analysis_topics == ["RAG", "LLMs"]
    assert stored.analysis_claims == [
        {
            "text": "RAG uses retrieved context.",
            "confidence": 0.9,
            "is_time_sensitive": False,
            "requires_external_verification": False,
        }
    ]
    assert stored.analysis_model == "gemini-2.5-flash"
    assert stored.analysis_prompt_version == "v1"
    assert stored.analyzed_at is not None
    assert analysis_client.calls == 1


def test_rejected_document_skips_analysis(service, analysis_client) -> None:
    content = b"The garden needs water and sunlight for healthy flowers in spring."
    document = service.submit("garden.txt", content, "text/plain", "Garden")
    service.process(document.id, content)
    stored = service.session.get(KnowledgeDocument, document.id)
    assert stored.status is DocumentStatus.REJECTED
    assert stored.analysis_summary is None
    assert analysis_client.calls == 0


def test_missing_title_review_status_and_filename_correction_are_preserved(
    service, analysis_client
) -> None:
    document = service.submit("rag_notes.md", VALID_GENAI_TEXT, "text/markdown", None)
    service.process(document.id, VALID_GENAI_TEXT)
    stored = service.session.get(KnowledgeDocument, document.id)
    assert stored.status is DocumentStatus.CONTRIBUTOR_REVIEW_REQUIRED
    assert stored.title == ""
    assert any(finding["suggested_value"] == "rag notes" for finding in stored.validation_findings)
    assert stored.analysis_proposed_title == "Generated title"
    assert analysis_client.calls == 1


def test_analysis_failure_uses_safe_processing_failure(service, analysis_client) -> None:
    analysis_client.analysis = GeminiTimeoutError("provider timeout detail")
    document = service.submit("rag.txt", VALID_GENAI_TEXT, "text/plain", "RAG")
    service.process(document.id, VALID_GENAI_TEXT)
    stored = service.session.get(KnowledgeDocument, document.id)
    finding = stored.validation_findings[0]
    assert stored.status is DocumentStatus.FAILED
    assert finding["code"] == "ANALYSIS_FAILED"
    assert "provider" not in str(finding).lower()
    assert stored.analysis_summary is None


def test_analysis_persistence_failure_rolls_back_analysis_fields(
    service, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_commit = service.session.commit
    commits = 0

    def fail_analysis_commit() -> None:
        nonlocal commits
        commits += 1
        if commits == 3:
            raise RuntimeError("database detail")
        original_commit()

    monkeypatch.setattr(service.session, "commit", fail_analysis_commit)
    document = service.submit("rag.txt", VALID_GENAI_TEXT, "text/plain", "RAG")
    service.process(document.id, VALID_GENAI_TEXT)
    stored = service.session.get(KnowledgeDocument, document.id)
    assert stored.status is DocumentStatus.FAILED
    assert stored.analysis_summary is None
    assert stored.analysis_topics is None
    assert stored.analysis_claims is None


def test_document_response_exposes_nested_analysis_contract(service) -> None:
    document = service.submit("rag.txt", VALID_GENAI_TEXT, "text/plain", "RAG")
    service.process(document.id, VALID_GENAI_TEXT)
    response = to_response(service.session.get(KnowledgeDocument, document.id))
    assert response.analysis is not None
    assert response.analysis.summary == "A concise explanation of the document."
    assert response.analysis.model == "gemini-2.5-flash"


def test_unanalyzed_document_response_has_null_analysis(service) -> None:
    document = service.submit("rag.txt", VALID_GENAI_TEXT, "text/plain", "RAG")
    assert to_response(document).analysis is None


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
        service.stored_document_parser,
        "parse",
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

    monkeypatch.setattr("app.documents.stored_document_parser.DocumentConverter", Converter)
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), "Digital PDF")
    content = pdf.tobytes()
    document = service.submit("notes.pdf", content, "application/pdf", "PDF notes")
    service.process(document.id, content)
    stored = service.session.get(KnowledgeDocument, document.id)
    assert stored.status is DocumentStatus.APPROVED
    assert stored.extracted_text == VALID_GENAI_TEXT.decode()
