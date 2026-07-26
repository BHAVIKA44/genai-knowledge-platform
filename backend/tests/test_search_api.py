from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app
from app.search.hybrid_search import HybridSearchError, HybridSearchResult


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_session] = lambda: object()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def search_results(count: int) -> list[HybridSearchResult]:
    return [
        HybridSearchResult(
            document_id=f"document-{index}",
            title=f"Document {index}",
            snippet=f"Snippet {index}",
            keyword_score=0.8,
            vector_score=0.7,
            final_score=0.75,
        )
        for index in range(count)
    ]


def install_search_service(
    monkeypatch: pytest.MonkeyPatch,
    search: Callable[[str], list[HybridSearchResult]],
) -> None:
    class SearchService:
        def __init__(self, _: object) -> None:
            pass

        def search(self, query: str) -> list[HybridSearchResult]:
            return search(query)

    monkeypatch.setattr("app.search.routes.HybridSearchService", SearchService)


def test_search_delegates_a_valid_query_to_hybrid_search_service(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    queries: list[str] = []
    install_search_service(monkeypatch, lambda query: queries.append(query) or search_results(1))

    response = client.get("/search", params={"q": "retrieval"})

    assert response.status_code == 200
    assert queries == ["retrieval"]


def test_search_uses_a_default_limit_of_ten(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_search_service(monkeypatch, lambda _: search_results(12))

    response = client.get("/search", params={"q": "retrieval"})

    assert response.status_code == 200
    assert len(response.json()) == 10


def test_search_accepts_a_custom_limit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    install_search_service(monkeypatch, lambda _: search_results(12))

    response = client.get("/search", params={"q": "retrieval", "limit": 2})

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.parametrize("query", ["", "   "])
def test_search_rejects_empty_queries(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, query: str
) -> None:
    install_search_service(monkeypatch, lambda _: pytest.fail("search service was called"))

    response = client.get("/search", params={"q": query})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SEARCH_QUERY"


def test_search_rejects_queries_that_exceed_the_maximum_length(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_search_service(monkeypatch, lambda _: pytest.fail("search service was called"))

    response = client.get("/search", params={"q": "x" * 501})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SEARCH_QUERY"


@pytest.mark.parametrize("limit", [0, 26])
def test_search_rejects_limits_outside_the_supported_range(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, limit: int
) -> None:
    install_search_service(monkeypatch, lambda _: pytest.fail("search service was called"))

    response = client.get("/search", params={"q": "retrieval", "limit": limit})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SEARCH_LIMIT"


def test_search_errors_use_the_safe_error_envelope(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(_: str) -> list[HybridSearchResult]:
        raise HybridSearchError("database detail")

    install_search_service(monkeypatch, fail)

    response = client.get("/search", params={"q": "retrieval"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SEARCH_FAILED"
    assert "database detail" not in response.text


def test_search_response_exposes_only_public_result_fields(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_search_service(monkeypatch, lambda _: search_results(1))

    response = client.get("/search", params={"q": "retrieval"})

    assert response.status_code == 200
    assert set(response.json()[0]) == {"document_id", "title", "snippet", "final_score"}
    assert "keyword_score" not in response.text
    assert "vector_score" not in response.text
    assert "embedding" not in response.text
    assert "SELECT" not in response.text


def test_search_route_is_registered() -> None:
    assert "get" in app.openapi()["paths"]["/search"]
