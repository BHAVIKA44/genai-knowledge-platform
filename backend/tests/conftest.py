import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import Settings
from app.documents.service import DocumentIngestionService


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as current_session:
        yield current_session


@pytest.fixture
def service(session: Session, monkeypatch: pytest.MonkeyPatch) -> DocumentIngestionService:
    monkeypatch.setattr("app.documents.service.filetype.guess_mime", lambda *_args: "text/plain")
    return DocumentIngestionService(session, Settings(database_url="sqlite://"))
