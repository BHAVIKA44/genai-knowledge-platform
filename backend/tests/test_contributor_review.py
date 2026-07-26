import pytest

from app.core.errors import DomainError
from app.documents.models import DocumentStatus, KnowledgeDocument
from app.documents.service import DocumentIngestionService
from app.reviews.service import ContributorReviewService

VALID_TEXT = (
    b"Large language models use transformer attention. Retrieval augmented generation uses "
    b"embeddings and a vector database for grounded answers."
)


def reviewed_document(service: DocumentIngestionService) -> KnowledgeDocument:
    document = service.submit("rag_notes.md", VALID_TEXT, "text/markdown", None)
    service.process(document.id, VALID_TEXT)
    return service.session.get(KnowledgeDocument, document.id)


def test_review_details_are_available_only_while_review_is_required(service) -> None:
    document = reviewed_document(service)
    details = ContributorReviewService(service.session).get_details(document.id)
    assert details[1].suggested_value == "rag notes"


def test_accepting_title_suggestion_updates_record_and_approves(service) -> None:
    document = reviewed_document(service)
    updated = ContributorReviewService(service.session).decide(document.id, "ACCEPT")
    assert updated.status is DocumentStatus.APPROVED
    assert updated.title == "rag notes"
    assert updated.contributor_review_decision == "ACCEPT"


def test_declining_title_suggestion_rejects_document(service) -> None:
    document = reviewed_document(service)
    updated = ContributorReviewService(service.session).decide(document.id, "DECLINE")
    assert updated.status is DocumentStatus.REJECTED
    assert updated.contributor_review_decision == "DECLINE"


def test_repeated_decision_is_idempotent(service) -> None:
    document = reviewed_document(service)
    review_service = ContributorReviewService(service.session)
    first = review_service.decide(document.id, "ACCEPT")
    second = review_service.decide(document.id, "ACCEPT")
    assert second.id == first.id
    assert second.status is DocumentStatus.APPROVED


def test_review_action_in_invalid_state_is_rejected(service) -> None:
    document = service.submit("rag.md", VALID_TEXT, "text/markdown", "RAG")
    service.process(document.id, VALID_TEXT)
    with pytest.raises(DomainError) as error:
        ContributorReviewService(service.session).decide(document.id, "ACCEPT")
    assert error.value.code == "INVALID_REVIEW_STATE"
