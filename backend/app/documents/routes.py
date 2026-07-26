from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.documents.models import KnowledgeDocument
from app.documents.schemas import DocumentAnalysisResponse, DocumentResponse
from app.documents.service import DocumentIngestionService
from app.reviews.schemas import ContributorReviewDecision, ContributorReviewDetails
from app.reviews.service import ContributorReviewService

router = APIRouter(prefix="/api/documents", tags=["documents"])


def to_response(document: KnowledgeDocument) -> DocumentResponse:
    response = DocumentResponse.model_validate(document)
    if document.analysis_summary is None:
        return response
    return response.model_copy(
        update={
            "analysis": DocumentAnalysisResponse(
                proposed_title=document.analysis_proposed_title,
                summary=document.analysis_summary,
                topics=document.analysis_topics or [],
                claims=document.analysis_claims or [],
                model=document.analysis_model or "",
                prompt_version=document.analysis_prompt_version or "",
                analyzed_at=document.analyzed_at or document.updated_at,
            )
        }
    )


def process_submission(document_id: str, content: bytes) -> None:
    from app.db.session import engine

    with Session(engine) as session:
        DocumentIngestionService(session, get_settings()).process(document_id, content)


@router.post("", response_model=DocumentResponse, status_code=202)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> DocumentResponse:
    content = await file.read()
    document = DocumentIngestionService(session, settings).submit(
        file.filename or "", content, file.content_type, title
    )
    background_tasks.add_task(process_submission, document.id, content)
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
    return to_response(document)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, session: Session = Depends(get_session)) -> DocumentResponse:
    document = session.get(KnowledgeDocument, document_id)
    if document is None:
        from app.core.errors import DomainError

        raise DomainError(
            "DOCUMENT_NOT_FOUND",
            "We could not find that document.",
            "Return to the upload page and try again.",
            404,
        )
    return to_response(document)


@router.get("/{document_id}/contributor-review", response_model=ContributorReviewDetails)
def get_contributor_review(
    document_id: str, session: Session = Depends(get_session)
) -> ContributorReviewDetails:
    document, finding = ContributorReviewService(session).get_details(document_id)
    return ContributorReviewDetails(document=to_response(document), finding=finding)


@router.post("/{document_id}/contributor-review", response_model=DocumentResponse)
def decide_contributor_review(
    document_id: str,
    decision: ContributorReviewDecision,
    session: Session = Depends(get_session),
) -> DocumentResponse:
    document = ContributorReviewService(session).decide(document_id, decision.action)
    return to_response(document)
