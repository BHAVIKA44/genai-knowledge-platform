import pytest

from app.core.config import Settings
from app.documents.models import DocumentStatus
from app.search.hybrid_search import HybridSearchError, HybridSearchService


class FakeEmbedder:
    def __init__(self, result: list[float] | Exception | None = None) -> None:
        self.result = result or [0.1] * 384
        self.queries: list[str] = []

    def embed_query(self, query: str) -> list[float]:
        self.queries.append(query)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeSearchSession:
    def __init__(
        self, keyword_rows: list[tuple[object, ...]], vector_rows: list[tuple[object, ...]]
    ) -> None:
        self.responses = iter([keyword_rows, vector_rows])
        self.statements: list[object] = []

    def exec(self, statement: object) -> list[tuple[object, ...]]:
        self.statements.append(statement)
        return next(self.responses)


def service(
    keyword_rows: list[tuple[object, ...]] | None = None,
    vector_rows: list[tuple[object, ...]] | None = None,
    embedder: FakeEmbedder | None = None,
) -> tuple[HybridSearchService, FakeSearchSession]:
    session = FakeSearchSession(keyword_rows or [], vector_rows or [])
    return HybridSearchService(session, embedder or FakeEmbedder()), session  # type: ignore[arg-type]


def service_with_similarity_threshold(
    vector_rows: list[tuple[object, ...]], similarity: float = 0.6
) -> HybridSearchService:
    return HybridSearchService(
        FakeSearchSession([], vector_rows),  # type: ignore[arg-type]
        FakeEmbedder(),
        Settings(minimum_vector_similarity=similarity),
    )


def test_search_queries_only_approved_documents() -> None:
    search, session = service()

    assert search.search("retrieval") == []
    assert all(
        DocumentStatus.APPROVED in statement.compile().params.values()  # type: ignore[union-attr]
        for statement in session.statements
    )


def test_keyword_only_matches_are_returned() -> None:
    search, _ = service(keyword_rows=[("document-1", "RAG", "keyword excerpt", 0, 0.8)])

    results = search.search("retrieval")

    assert [(result.document_id, result.title, result.snippet) for result in results] == [
        ("document-1", "RAG", "keyword excerpt")
    ]
    assert results[0].keyword_score == 1.0
    assert results[0].vector_score == 0.0


def test_vector_only_matches_are_returned() -> None:
    search, _ = service(vector_rows=[("document-1", "RAG", "vector excerpt", 0, 0.8)])

    results = search.search("retrieval")

    assert [(result.document_id, result.title, result.snippet) for result in results] == [
        ("document-1", "RAG", "vector excerpt")
    ]
    assert results[0].keyword_score == 0.0
    assert results[0].vector_score == 1.0


def test_hybrid_matches_are_deduplicated_by_document() -> None:
    search, _ = service(
        keyword_rows=[("document-1", "RAG", "keyword excerpt", 0, 0.8)],
        vector_rows=[("document-1", "RAG", "vector excerpt", 1, 0.9)],
    )

    results = search.search("retrieval")

    assert len(results) == 1
    assert results[0].document_id == "document-1"
    assert results[0].snippet == "keyword excerpt"


def test_score_fusion_orders_ties_deterministically() -> None:
    search, _ = service(
        keyword_rows=[
            ("document-a", "A", "keyword a", 0, 0.9),
            ("document-b", "B", "keyword b", 0, 0.4),
        ],
        vector_rows=[
            ("document-b", "B", "vector b", 0, 0.9),
            ("document-a", "A", "vector a", 0, 0.4),
        ],
    )

    results = search.search("retrieval")

    assert [result.document_id for result in results] == ["document-a", "document-b"]
    assert [result.final_score for result in results] == [0.5, 0.5]


def test_final_scores_remain_normalized() -> None:
    search, _ = service(
        keyword_rows=[
            ("document-a", "A", "keyword a", 0, 0.9),
            ("document-b", "B", "keyword b", 0, 0.4),
        ],
        vector_rows=[
            ("document-a", "A", "vector a", 0, 0.9),
            ("document-b", "B", "vector b", 0, 0.4),
        ],
    )

    results = search.search("retrieval")

    assert [result.final_score for result in results] == [1.0, 0.0]


def test_empty_keyword_results_do_not_hide_vector_matches() -> None:
    search, _ = service(vector_rows=[("document-1", "RAG", "vector excerpt", 0, 0.8)])

    assert [result.document_id for result in search.search("retrieval")] == ["document-1"]


def test_empty_vector_results_do_not_hide_keyword_matches() -> None:
    search, _ = service(keyword_rows=[("document-1", "RAG", "keyword excerpt", 0, 0.8)])

    assert [result.document_id for result in search.search("retrieval")] == ["document-1"]


def test_relevant_semantic_matches_meet_the_similarity_floor() -> None:
    search = service_with_similarity_threshold(
        [("document-1", "Evaluation", "relevant excerpt", 0, 0.78)]
    )

    assert [result.document_id for result in search.search("assess grounded model answers")] == [
        "document-1"
    ]


def test_paraphrased_semantic_matches_meet_the_similarity_floor() -> None:
    search = service_with_similarity_threshold(
        [("document-1", "RAG", "paraphrased excerpt", 0, 0.63)]
    )

    results = search.search("retrieve context before answering")

    assert [result.document_id for result in results] == ["document-1"]


@pytest.mark.parametrize("similarity", [0.5, 0.52])
def test_low_similarity_vector_matches_are_not_returned(similarity: float) -> None:
    search = service_with_similarity_threshold(
        [("document-1", "Unrelated", "unrelated excerpt", 0, similarity)]
    )

    assert search.search("unrelated query") == []


def test_special_character_query_returns_no_results_without_embedding() -> None:
    embedder = FakeEmbedder()
    search, _ = service(embedder=embedder)

    assert search.search("#$%^&*()") == []
    assert embedder.queries == []


def test_similarity_at_the_configured_floor_is_included() -> None:
    search = service_with_similarity_threshold(
        [("document-1", "Borderline", "borderline excerpt", 0, 0.6)]
    )

    assert [result.document_id for result in search.search("borderline relevant query")] == [
        "document-1"
    ]


def test_empty_search_results_are_returned_as_an_empty_list() -> None:
    search, _ = service()

    assert search.search("retrieval") == []


def test_embedding_failure_is_mapped_without_provider_details() -> None:
    search, _ = service(embedder=FakeEmbedder(RuntimeError("provider detail")))

    with pytest.raises(HybridSearchError) as error:
        search.search("retrieval")

    assert "provider detail" not in str(error.value)


def test_database_failure_is_mapped_without_database_details() -> None:
    class FailingSearchSession:
        def exec(self, _: object) -> list[tuple[object, ...]]:
            raise RuntimeError("database detail")

    search = HybridSearchService(FailingSearchSession(), FakeEmbedder())  # type: ignore[arg-type]

    with pytest.raises(HybridSearchError) as error:
        search.search("retrieval")

    assert "database detail" not in str(error.value)


def test_results_do_not_expose_embeddings_or_sql() -> None:
    search, _ = service(keyword_rows=[("document-1", "RAG", "keyword excerpt", 0, 0.8)])

    result = search.search("retrieval")[0]

    assert set(vars(result)) == {
        "document_id",
        "title",
        "snippet",
        "keyword_score",
        "vector_score",
        "final_score",
    }
