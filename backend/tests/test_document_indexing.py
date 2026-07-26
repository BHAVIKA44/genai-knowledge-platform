from types import SimpleNamespace

import pytest

from app.documents.chunking import NormalizedChunk
from app.documents.indexing import DocumentIndexingError, DocumentIndexingService
from app.documents.models import DocumentStatus, DocumentType, KnowledgeDocument


def document(source_storage_key: str | None = "source.pdf") -> KnowledgeDocument:
    return KnowledgeDocument(
        id="document-id",
        title="Title",
        source_filename="source.pdf",
        storage_filename="stored.pdf",
        source_storage_key=source_storage_key,
        document_type=DocumentType.PDF,
        status=DocumentStatus.APPROVED,
        sha256="hash",
    )


class FakeParser:
    def __init__(self, events: list[str], failure: Exception | None = None) -> None:
        self.events = events
        self.failure = failure

    def parse(self, *_: object) -> SimpleNamespace:
        self.events.append("parser")
        if self.failure:
            raise self.failure
        return SimpleNamespace(document=SimpleNamespace())


class FakeChunker:
    def __init__(
        self, events: list[str], chunks: list[NormalizedChunk], failure: Exception | None = None
    ) -> None:
        self.events, self.chunks, self.failure = events, chunks, failure

    def chunk(self, _: object) -> list[NormalizedChunk]:
        self.events.append("chunker")
        if self.failure:
            raise self.failure
        return self.chunks


class FakeEmbedder:
    model_name = "BAAI/bge-small-en-v1.5"

    def __init__(
        self, events: list[str], vectors: list[list[float]], failure: Exception | None = None
    ) -> None:
        self.events, self.vectors, self.failure = events, vectors, failure

    def embed_documents(self, _: list[str]) -> list[list[float]]:
        self.events.append("embedder")
        if self.failure:
            raise self.failure
        return self.vectors


class FakeRepository:
    def __init__(self, events: list[str], failure: Exception | None = None) -> None:
        self.events, self.failure = events, failure
        self.records = []

    def replace_chunks(self, _: str, records: list[object]) -> None:
        self.events.append("repository")
        if self.failure:
            raise self.failure
        self.records = records


def indexing_service(
    events: list[str],
    chunks: list[NormalizedChunk],
    vectors: list[list[float]],
    **failures: Exception,
):
    parser = FakeParser(events, failures.get("parser"))
    chunker = FakeChunker(events, chunks, failures.get("chunker"))
    embedder = FakeEmbedder(events, vectors, failures.get("embedder"))
    repository = FakeRepository(events, failures.get("repository"))
    session = SimpleNamespace(
        commit=lambda: pytest.fail("commit"), rollback=lambda: pytest.fail("rollback")
    )
    return DocumentIndexingService(session, parser, chunker, embedder, repository), repository


def test_indexes_in_dependency_order_and_maps_chunks() -> None:
    events: list[str] = []
    chunk = NormalizedChunk(0, "text", 2, "Heading", content_length=4)
    service, repository = indexing_service(events, [chunk], [[1.0] + [0.0] * 383])
    result = service.index(document())
    assert events == ["parser", "chunker", "embedder", "repository"]
    assert result.chunk_count == 1
    assert result.embedding_model == "BAAI/bge-small-en-v1.5"
    record = repository.records[0]
    assert (record.position, record.text, record.page_number, record.source_heading) == (
        0,
        "text",
        2,
        "Heading",
    )


def test_invalid_inputs_fail_before_persistence() -> None:
    events: list[str] = []
    service, _ = indexing_service(events, [], [])
    with pytest.raises(DocumentIndexingError):
        service.index(document(None))
    assert events == []
    with pytest.raises(DocumentIndexingError):
        service.index(document())
    assert events == ["parser", "chunker"]


@pytest.mark.parametrize("failure", ["parser", "chunker", "embedder", "repository"])
def test_dependency_failures_are_mapped(failure: str) -> None:
    events: list[str] = []
    service, _ = indexing_service(
        events,
        [NormalizedChunk(0, "text", None, None, content_length=4)],
        [[1.0] + [0.0] * 383],
        **{failure: RuntimeError("provider detail")},
    )
    with pytest.raises(DocumentIndexingError) as error:
        service.index(document())
    assert "detail" not in str(error.value)


@pytest.mark.parametrize("vectors", [[], [[1.0]], [[1.0] + [0.0] * 383, [1.0] + [0.0] * 383]])
def test_vector_mismatches_fail_before_persistence(vectors: list[list[float]]) -> None:
    events: list[str] = []
    service, _ = indexing_service(
        events, [NormalizedChunk(0, "text", None, None, content_length=4)], vectors
    )
    with pytest.raises(DocumentIndexingError):
        service.index(document())
    assert "repository" not in events
