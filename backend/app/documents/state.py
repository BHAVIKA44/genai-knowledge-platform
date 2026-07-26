from app.core.errors import InvalidStateTransitionError
from app.documents.models import DocumentStatus

ALLOWED_TRANSITIONS: dict[DocumentStatus, set[DocumentStatus]] = {
    DocumentStatus.UPLOADED: {
        DocumentStatus.PROCESSING,
        DocumentStatus.REJECTED,
        DocumentStatus.FAILED,
    },
    DocumentStatus.PROCESSING: {
        DocumentStatus.VALIDATING,
        DocumentStatus.REJECTED,
        DocumentStatus.FAILED,
    },
    DocumentStatus.VALIDATING: {
        DocumentStatus.APPROVED,
        DocumentStatus.CONTRIBUTOR_REVIEW_REQUIRED,
        DocumentStatus.ADMIN_REVIEW_REQUIRED,
        DocumentStatus.REJECTED,
        DocumentStatus.FAILED,
    },
    DocumentStatus.APPROVED: set(),
    DocumentStatus.CONTRIBUTOR_REVIEW_REQUIRED: set(),
    DocumentStatus.ADMIN_REVIEW_REQUIRED: set(),
    DocumentStatus.REJECTED: set(),
    DocumentStatus.FAILED: set(),
}


def transition_status(current: DocumentStatus, target: DocumentStatus) -> DocumentStatus:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStateTransitionError()
    return target
