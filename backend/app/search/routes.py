from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.core.errors import DomainError
from app.db.session import get_session
from app.search.hybrid_search import HybridSearchError, HybridSearchService

MAX_QUERY_LENGTH = 500
MAX_SEARCH_LIMIT = 25

router = APIRouter(tags=["search"])


class SearchResultResponse(BaseModel):
    document_id: str
    title: str
    snippet: str
    final_score: float


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
