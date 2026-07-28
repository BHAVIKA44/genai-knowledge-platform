import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.session import get_session
from app.llm.client import GeminiKnowledgeClient
from app.search.answering import SearchAnswerService
from app.search.hybrid_search import HybridSearchError, HybridSearchService

MAX_QUERY_LENGTH = 500
MAX_SEARCH_LIMIT = 25

router = APIRouter(tags=["search"])
logger = structlog.get_logger()


class SearchResultResponse(BaseModel):
    document_id: str
    title: str
    snippet: str
    final_score: float


class SearchAnswerRequest(BaseModel):
    question: str
    limit: int = 5


class SearchAnswerResponse(BaseModel):
    answer: str
    results: list[SearchResultResponse]


@router.get("/search", response_model=list[SearchResultResponse])
def search(
    q: str = Query(),
    limit: int = 10,
    session: Session = Depends(get_session),
) -> list[SearchResultResponse]:
    query = q.strip()
    if not query or len(query) > MAX_QUERY_LENGTH:
        raise DomainError(
            "INVALID_SEARCH_QUERY",
            "Enter a search query with no more than 500 characters.",
            "Try a shorter search query.",
            422,
        )
    if not 1 <= limit <= MAX_SEARCH_LIMIT:
        raise DomainError(
            "INVALID_SEARCH_LIMIT",
            "Choose between 1 and 25 search results.",
            status_code=422,
        )
    try:
        results = HybridSearchService(session).search(query)
    except HybridSearchError as error:
        raise DomainError(
            "SEARCH_FAILED",
            "We could not search the knowledge base right now.",
            "Please try again shortly.",
            503,
        ) from error
    return [
        SearchResultResponse(
            document_id=result.document_id,
            title=result.title,
            snippet=result.snippet,
            final_score=result.final_score,
        )
        for result in results[:limit]
    ]


@router.post("/search/answer", response_model=SearchAnswerResponse)
def answer_search(
    request: SearchAnswerRequest,
    session: Session = Depends(get_session),
) -> SearchAnswerResponse:
    question = request.question.strip()
    if not question or len(question) > MAX_QUERY_LENGTH:
        raise DomainError(
            "INVALID_SEARCH_QUERY",
            "Enter a search query with no more than 500 characters.",
            "Try a shorter search query.",
            422,
        )
    if not 1 <= request.limit <= MAX_SEARCH_LIMIT:
        raise DomainError(
            "INVALID_SEARCH_LIMIT",
            "Choose between 1 and 25 search results.",
            status_code=422,
        )
    try:
        answer = SearchAnswerService(
            HybridSearchService(session),
            GeminiKnowledgeClient(get_settings()),
        ).answer(question)
    except HybridSearchError as error:
        raise DomainError(
            "SEARCH_FAILED",
            "We could not search the knowledge base right now.",
            "Please try again shortly.",
            503,
        ) from error
    except Exception as error:
        logger.warning("search_answer_failed", failure_category=type(error).__name__)
        raise DomainError(
            "ANSWER_FAILED",
            "We could not prepare an answer right now.",
            "Please try again shortly.",
            503,
        ) from error
    return SearchAnswerResponse(
        answer=answer.answer,
        results=[
            SearchResultResponse(
                document_id=result.document_id,
                title=result.title,
                snippet=result.snippet,
                final_score=result.final_score,
            )
            for result in answer.results[: request.limit]
        ],
    )
