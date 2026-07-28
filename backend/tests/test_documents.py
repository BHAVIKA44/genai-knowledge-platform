import fitz
import pytest
from sqlmodel import select

from app.core.errors import DomainError, InvalidStateTransitionError
from app.documents.models import DocumentStatus, KnowledgeDocument
from app.documents.routes import to_response
from app.documents.state import transition_status
from app.llm.client import GeminiTimeoutError
from app.llm.models import KnowledgeAnalysis, SemanticFinding

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


def test_rejected_upload_skips_indexing(service, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.documents.service.DocumentIndexingService",
        lambda *_: pytest.fail("indexer constructed"),
    )
    content = b"The garden needs sunlight and water for healthy flowers in spring."
    document = service.submit("notes.txt", content, "text/plain", "Garden")
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
    assert stored.analysis_model == "gemini-3.6-flash"
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


def test_missing_optional_title_uses_filename_fallback_and_is_approved(
    service, analysis_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "_index", lambda _: None)
    document = service.submit("rag_notes.md", VALID_GENAI_TEXT, "text/markdown", None)
    service.process(document.id, VALID_GENAI_TEXT)
    stored = service.session.get(KnowledgeDocument, document.id)
    assert stored.status is DocumentStatus.APPROVED
    assert stored.title == "rag notes"
    assert stored.analysis_proposed_title == "Generated title"
    assert analysis_client.calls == 1


def test_missing_optional_title_uses_extracted_markdown_heading(
    service, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "_index", lambda _: None)
    content = b"# Retrieval notes\n\n" + VALID_GENAI_TEXT
    document = service.submit("notes.md", content, "text/markdown", None)
    service.process(document.id, content)
    stored = service.session.get(KnowledgeDocument, document.id)
    assert stored.status is DocumentStatus.APPROVED
    assert stored.title == "Retrieval notes"


def test_analysis_failure_uses_safe_processing_failure(
    service, analysis_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_events: list[tuple[str, dict[str, object]]] = []

    def capture_error(event: str, **values: object) -> None:
        log_events.append((event, values))

    monkeypatch.setattr("app.documents.service.logger.error", capture_error)
    analysis_client.analysis = GeminiTimeoutError("provider timeout detail")
    document = service.submit("rag.txt", VALID_GENAI_TEXT, "text/plain", "RAG")
    service.process(document.id, VALID_GENAI_TEXT)
    stored = service.session.get(KnowledgeDocument, document.id)
    finding = stored.validation_findings[0]
    assert stored.status is DocumentStatus.FAILED
    assert finding["code"] == "ANALYSIS_FAILED"
    assert "provider" not in str(finding).lower()
    assert stored.analysis_summary is None
    assert log_events[0][0] == "document_analysis_failed"
    assert "provider timeout detail" not in str(log_events)
    assert VALID_GENAI_TEXT.decode() not in str(log_events)


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
    assert response.analysis.model == "gemini-3.6-flash"


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
    assert error.value.message == "This exact document has already been uploaded."
    assert error.value.action == "Please upload a different version if you made changes."
    assert len(service.session.exec(select(KnowledgeDocument)).all()) == 1


def test_duplicate_detection_uses_file_bytes_not_filename(service) -> None:
    first = service.submit("same-name.txt", VALID_GENAI_TEXT, "text/plain", "First")
    different_content = (
        b"Large language models use attention. Prompt engineering uses examples to guide "
        b"model behavior in Generative AI applications."
    )
    second = service.submit("same-name.txt", different_content, "text/plain", "Second")
    assert first.id != second.id


def test_edited_pdf_is_not_a_duplicate_when_its_bytes_change(service, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.documents.service.filetype.guess_mime", lambda *_args: "application/pdf"
    )
    original = fitz.open()
    original.new_page()
    original.new_page()
    edited = fitz.open()
    edited.new_page()

    first = service.submit("genai-principles.pdf", original.tobytes(), "application/pdf", "GenAI")
    second = service.submit("genai-principles.pdf", edited.tobytes(), "application/pdf", "GenAI")

    assert first.id != second.id
    assert first.sha256 != second.sha256


@pytest.mark.parametrize("category", ["Technical ambiguity", "Missing context"])
def test_minor_semantic_suggestions_do_not_block_approval(
    service, analysis_client, monkeypatch: pytest.MonkeyPatch, category: str
) -> None:
    monkeypatch.setattr(service, "_index", lambda _: None)
    analysis_client.analysis = KnowledgeAnalysis(
        proposed_title=None,
        summary="A concise explanation of the document.",
        topics=["RAG"],
        claims=[],
        semantic_findings=[
            SemanticFinding(
                category=category,
                severity="WARNING",
                confidence=0.9,
                explanation="This could be explained in more depth.",
                suggested_improvement="Add optional context.",
                contributor_fix_possible=True,
                admin_review_required=False,
            )
        ],
    )
    document = service.submit("rag.md", VALID_GENAI_TEXT, "text/markdown", "RAG")
    service.process(document.id, VALID_GENAI_TEXT)
    assert service.session.get(KnowledgeDocument, document.id).status is DocumentStatus.APPROVED


def test_materially_misleading_semantic_finding_requires_admin_review(
    service, analysis_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "_index", lambda _: None)
    analysis_client.analysis = KnowledgeAnalysis(
        proposed_title=None,
        summary="A concise explanation of the document.",
        topics=["RAG"],
        claims=[],
        semantic_findings=[
            SemanticFinding(
                category="Materially misleading claim",
                severity="BLOCKING",
                confidence=0.95,
                explanation="The claim is materially incorrect.",
                suggested_improvement=None,
                contributor_fix_possible=False,
                admin_review_required=True,
            )
        ],
    )
    document = service.submit("rag.md", VALID_GENAI_TEXT, "text/markdown", "RAG")
    service.process(document.id, VALID_GENAI_TEXT)
    assert (
        service.session.get(KnowledgeDocument, document.id).status
        is DocumentStatus.ADMIN_REVIEW_REQUIRED
    )


def test_required_contributor_correction_routes_to_contributor_review(
    service, analysis_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    analysis_client.analysis = KnowledgeAnalysis(
        proposed_title="RAG guide",
        summary="A concise explanation of the document.",
        topics=["RAG"],
        claims=[],
        semantic_findings=[
            SemanticFinding(
                category="Missing title",
                severity="BLOCKING",
                confidence=0.95,
                explanation="The contributor needs to confirm a clear title before publication.",
                suggested_improvement="Use the proposed title.",
                contributor_fix_possible=True,
                admin_review_required=False,
            )
        ],
    )
    document = service.submit("rag.md", VALID_GENAI_TEXT, "text/markdown", "RAG")
    service.process(document.id, VALID_GENAI_TEXT)
    assert (
        service.session.get(KnowledgeDocument, document.id).status
        is DocumentStatus.CONTRIBUTOR_REVIEW_REQUIRED
    )


def test_unstructured_contributor_fix_routes_to_admin_review(
    service, analysis_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "_index", lambda _: None)
    analysis_client.analysis = KnowledgeAnalysis(
        proposed_title=None,
        summary="A concise explanation of the document.",
        topics=["RAG"],
        claims=[],
        semantic_findings=[
            SemanticFinding(
                category="Missing context",
                severity="BLOCKING",
                confidence=0.95,
                explanation="The resource is incomplete.",
                suggested_improvement="Add the missing explanation.",
                contributor_fix_possible=True,
                admin_review_required=False,
            )
        ],
    )
    document = service.submit("rag.md", VALID_GENAI_TEXT, "text/markdown", "RAG")
    service.process(document.id, VALID_GENAI_TEXT)

    assert (
        service.session.get(KnowledgeDocument, document.id).status
        is DocumentStatus.ADMIN_REVIEW_REQUIRED
    )


def test_title_correction_with_another_blocker_routes_to_admin_review(
    service, analysis_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "_index", lambda _: None)
    analysis_client.analysis = KnowledgeAnalysis(
        proposed_title="RAG guide",
        summary="A concise explanation of the document.",
        topics=["RAG"],
        claims=[],
        semantic_findings=[
            SemanticFinding(
                category="Missing title",
                severity="BLOCKING",
                confidence=0.95,
                explanation="The contributor needs to confirm a clear title before publication.",
                suggested_improvement="Use the proposed title.",
                contributor_fix_possible=True,
                admin_review_required=False,
            ),
            SemanticFinding(
                category="Materially misleading claim",
                severity="BLOCKING",
                confidence=0.95,
                explanation="The claim requires independent review.",
                suggested_improvement=None,
                contributor_fix_possible=False,
                admin_review_required=False,
            ),
        ],
    )
    document = service.submit("rag.md", VALID_GENAI_TEXT, "text/markdown", "RAG")
    service.process(document.id, VALID_GENAI_TEXT)

    assert (
        service.session.get(KnowledgeDocument, document.id).status
        is DocumentStatus.ADMIN_REVIEW_REQUIRED
    )


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
    monkeypatch.setattr(service, "_index", lambda _: None)

    class ExtractedDocument:
        def export_to_markdown(self) -> str:
            return VALID_GENAI_TEXT.decode()

    class ConversionResult:
        document = ExtractedDocument()

    class Converter:
        def __init__(self, **_: object) -> None:
            pass

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
