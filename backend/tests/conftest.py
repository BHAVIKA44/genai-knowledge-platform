import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import Settings
from app.documents.service import DocumentIngestionService
from app.llm.models import KnowledgeAnalysis


class FakeAnalysisClient:
    model = "gemini-2.5-flash"
    prompt_version = "v1"

    def __init__(self, analysis: KnowledgeAnalysis | Exception | None = None) -> None:
        self.analysis = analysis or KnowledgeAnalysis(
            proposed_title="Generated title",
            summary="A concise explanation of the document.",
            topics=["RAG"],
            claims=[],
        )
        self.calls = 0

    def analyze_document(self, _: str) -> KnowledgeAnalysis:
        self.calls += 1
        if isinstance(self.analysis, Exception):
            raise self.analysis
        return self.analysis


@pytest.fixture
def analysis_client() -> FakeAnalysisClient:
    return FakeAnalysisClient()


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as current_session:
        yield current_session


@pytest.fixture
def service(
    session: Session, monkeypatch: pytest.MonkeyPatch, analysis_client: FakeAnalysisClient
) -> DocumentIngestionService:
    monkeypatch.setattr("app.documents.service.filetype.guess_mime", lambda *_args: "text/plain")
    return DocumentIngestionService(
        session, Settings(database_url="sqlite://"), analysis_client=analysis_client
    )
