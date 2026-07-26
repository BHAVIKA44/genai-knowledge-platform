import math

import pytest

from app.embeddings import (
    EMBEDDING_DIMENSIONS,
    QUERY_PREFIX,
    DocumentEmbedder,
    EmbeddingInputError,
    EmbeddingOutputError,
    EmbeddingProviderError,
    get_embedding_model,
)


class EncodedVectors:
    def __init__(self, values: list[list[float]]) -> None:
        self.values = values

    def tolist(self) -> list[list[float]]:
        return self.values


class FakeModel:
    def __init__(self, values: list[list[float]] | Exception) -> None:
        self.values = values
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str], **_: object) -> EncodedVectors:
        self.calls.append(texts)
        if isinstance(self.values, Exception):
            raise self.values
        return EncodedVectors(self.values)


def normalized_vector() -> list[float]:
    return [1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1)


def test_document_and_query_embedding_prefixes(monkeypatch: pytest.MonkeyPatch) -> None:
    model = FakeModel([normalized_vector()])
    monkeypatch.setattr("app.embeddings.get_embedding_model", lambda: model)
    embedder = DocumentEmbedder()
    assert embedder.embed_documents(["document text"])[0] == normalized_vector()
    embedder.embed_query("query text")
    embedder.embed_query(QUERY_PREFIX + "query text")
    assert model.calls == [
        ["document text"],
        [QUERY_PREFIX + "query text"],
        [QUERY_PREFIX + "query text"],
    ]


def test_empty_input_is_rejected_before_model_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.embeddings.get_embedding_model", lambda: pytest.fail("model called"))
    with pytest.raises(EmbeddingInputError):
        DocumentEmbedder().embed_documents([" "])
    with pytest.raises(EmbeddingInputError):
        DocumentEmbedder().embed_query("")


def test_output_dimensions_and_provider_failures_are_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.embeddings.get_embedding_model", lambda: FakeModel([[0.0]]))
    with pytest.raises(EmbeddingOutputError):
        DocumentEmbedder().embed_documents(["text"])
    monkeypatch.setattr(
        "app.embeddings.get_embedding_model", lambda: FakeModel(RuntimeError("detail"))
    )
    with pytest.raises(EmbeddingProviderError) as error:
        DocumentEmbedder().embed_documents(["text"])
    assert "detail" not in str(error.value)


def test_model_factory_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    get_embedding_model.cache_clear()
    calls = 0

    def build(*_: object, **__: object) -> FakeModel:
        nonlocal calls
        calls += 1
        return FakeModel([normalized_vector()])

    monkeypatch.setattr("app.embeddings.SentenceTransformer", build)
    assert get_embedding_model() is get_embedding_model()
    assert calls == 1
    get_embedding_model.cache_clear()


def test_returned_vectors_are_plain_normalized_values(monkeypatch: pytest.MonkeyPatch) -> None:
    vector = normalized_vector()
    monkeypatch.setattr("app.embeddings.get_embedding_model", lambda: FakeModel([vector]))
    result = DocumentEmbedder().embed_documents(["text"])[0]
    assert isinstance(result, list)
    assert all(isinstance(value, float) for value in result)
    assert math.isclose(sum(value * value for value in result), 1.0)
