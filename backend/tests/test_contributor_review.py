import pytest

from app.core.errors import DomainError
from app.documents.models import DocumentStatus, DocumentType, KnowledgeDocument
from app.documents.service import DocumentIngestionService
from app.knowledge_quality.models import FindingCategory, FindingSeverity, QualityFinding
from app.reviews.service import ContributorReviewService

VALID_TEXT = (
    b"Large language models use transformer attention. Retrieval augmented generation uses "
    b"embeddings and a vector database for grounded answers. It retrieves relevant passages "
    b"before a model responds, which helps people verify claims against reviewed context."
)


def reviewed_document(service: DocumentIngestionService) -> KnowledgeDocument:
    document = KnowledgeDocument(
        title="RAG notes",
        source_filename="rag_notes.md",
        storage_filename="rag_notes.md",
        source_storage_key="reviewed.md",
        document_type=DocumentType.MARKDOWN,
        status=DocumentStatus.CONTRIBUTOR_REVIEW_REQUIRED,
        sha256="reviewed-document",
        extracted_text="Retrieval augmented generation is is a pattern for grounded answers.",
        validation_findings=[
            QualityFinding(
                code="DETERMINISTIC_DUPLICATED_WORD",
                category=FindingCategory.EXTRACTION_QUALITY,
                severity=FindingSeverity.WARNING,
                confidence=1,
                title="A duplicated word needs your confirmation",
                explanation=(
                    "The same word appears twice in a row, which is likely an accidental " "typo."
                ),
                original_value="is is",
                suggested_value="is",
            ).model_dump()
        ],
    )
    service.session.add(document)
    service.session.commit()
    return document


def test_review_details_are_available_only_while_review_is_required(service) -> None:
    document = reviewed_document(service)
    details = ContributorReviewService(service.session).get_details(document.id)
    assert details[1].suggested_value == "is"


def test_blocking_deterministic_correction_is_available_for_contributor_review(service) -> None:
    document = reviewed_document(service)
    document.validation_findings = [
        {**document.validation_findings[0], "severity": FindingSeverity.BLOCKING}
    ]
    service.session.add(document)
    service.session.commit()

    _, finding = ContributorReviewService(service.session).get_details(document.id)

    assert finding.suggested_value == "is"
    assert finding.severity is FindingSeverity.BLOCKING


def test_accepting_deterministic_correction_indexes_and_commits_updated_record(
    service, monkeypatch: pytest.MonkeyPatch
) -> None:
    indexed_documents: list[tuple[str, str]] = []

    class Indexer:
        def __init__(self, *_: object) -> None:
            pass

        def index(self, document: KnowledgeDocument, **_: object) -> None:
            indexed_documents.append((document.id, document.title))

    monkeypatch.setattr("app.reviews.service.DocumentIndexingService", Indexer)
    document = reviewed_document(service)
    updated = ContributorReviewService(service.session).decide(document.id, "ACCEPT")

    assert indexed_documents == [(updated.id, "RAG notes")]
    assert updated.status is DocumentStatus.APPROVED
    assert (
        updated.extracted_text
        == "Retrieval augmented generation is a pattern for grounded answers."
    )
    assert updated.contributor_review_decision == "ACCEPT"


def test_declining_deterministic_correction_removes_chunks_and_rejects_document(
    service, monkeypatch: pytest.MonkeyPatch
) -> None:
    deleted_document_ids: list[str] = []

    class ChunkRepository:
        def __init__(self, *_: object) -> None:
            pass

        def delete_chunks(self, document_id: str) -> None:
            deleted_document_ids.append(document_id)

    monkeypatch.setattr("app.reviews.service.DocumentChunkRepository", ChunkRepository)
    document = reviewed_document(service)
    updated = ContributorReviewService(service.session).decide(document.id, "DECLINE")

    assert deleted_document_ids == [document.id]
    assert updated.status is DocumentStatus.REJECTED
    assert updated.contributor_review_decision == "DECLINE"


def test_indexing_failure_rolls_back_the_review_update(
    service, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FailingIndexer:
        def __init__(self, *_: object) -> None:
            pass

        def index(self, _: KnowledgeDocument, **__: object) -> None:
            raise RuntimeError("indexing failed")

    monkeypatch.setattr("app.reviews.service.DocumentIndexingService", FailingIndexer)
    document = reviewed_document(service)

    with pytest.raises(RuntimeError, match="indexing failed"):
        ContributorReviewService(service.session).decide(document.id, "ACCEPT")

    service.session.expire_all()
    unchanged = service.session.get(KnowledgeDocument, document.id)
    assert unchanged is not None
    assert unchanged.status is DocumentStatus.CONTRIBUTOR_REVIEW_REQUIRED
    assert (
        unchanged.extracted_text
        == "Retrieval augmented generation is is a pattern for grounded answers."
    )
    assert unchanged.contributor_review_decision is None


def test_repeated_decision_is_idempotent(service, monkeypatch: pytest.MonkeyPatch) -> None:
    class Indexer:
        def __init__(self, *_: object) -> None:
            pass

        def index(self, _: KnowledgeDocument, **__: object) -> None:
            pass

    monkeypatch.setattr("app.reviews.service.DocumentIndexingService", Indexer)
    document = reviewed_document(service)
    review_service = ContributorReviewService(service.session)
    first = review_service.decide(document.id, "ACCEPT")
    second = review_service.decide(document.id, "ACCEPT")
    assert second.id == first.id
    assert second.status is DocumentStatus.APPROVED


def test_review_action_in_invalid_state_is_rejected(
    service, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Indexer:
        def __init__(self, *_: object) -> None:
            pass

        def index(self, _: KnowledgeDocument) -> None:
            pass

    monkeypatch.setattr("app.documents.service.DocumentIndexingService", Indexer)
    document = service.submit("rag.md", VALID_TEXT, "text/markdown", "RAG")
    service.process(document.id, VALID_TEXT)
    with pytest.raises(DomainError) as error:
        ContributorReviewService(service.session).decide(document.id, "ACCEPT")
    assert error.value.code == "INVALID_REVIEW_STATE"
