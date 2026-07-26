from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.documents.models import KnowledgeDocument
from app.documents.schemas import DocumentResponse
from app.documents.service import DocumentIngestionService

router = APIRouter(prefix="/api/documents", tags=["documents"])


def to_response(document: KnowledgeDocument) -> DocumentResponse:
    return DocumentResponse.model_validate(document)


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
