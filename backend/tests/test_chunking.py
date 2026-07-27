from types import SimpleNamespace

import pytest

from app.documents.chunking import ChunkingError, ChunkLimitExceededError, DocumentChunkingService


def source_chunk(text: str, pages: list[int] | None = None, headings: list[str] | None = None):
    provenance = [SimpleNamespace(page_no=page) for page in pages or []]
    return SimpleNamespace(
        text=text,
        meta=SimpleNamespace(
            headings=headings,
            doc_items=[SimpleNamespace(prov=provenance)],
        ),
    )


def service(monkeypatch: pytest.MonkeyPatch, chunks: list[object]) -> DocumentChunkingService:
    monkeypatch.setattr(
        "app.documents.chunking.get_chunking_tokenizer", lambda _: SimpleNamespace()
    )
    monkeypatch.setattr(
        "app.documents.chunking.HuggingFaceTokenizer", lambda tokenizer: SimpleNamespace()
    )
    monkeypatch.setattr("app.documents.chunking.HybridChunker", lambda tokenizer: SimpleNamespace())
    instance = DocumentChunkingService()
    instance.chunker = SimpleNamespace(chunk=lambda _: iter(chunks))
    return instance


def test_normalizes_chunk_order_and_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    chunks = service(
        monkeypatch,
        [source_chunk("first", [3, 4], ["Overview"]), source_chunk("second")],
    ).chunk(SimpleNamespace())
    assert [(chunk.position, chunk.text) for chunk in chunks] == [(0, "first"), (1, "second")]
    assert chunks[0].page_number == 3
    assert chunks[0].source_heading == "Overview"
    assert chunks[1].page_number is None
    assert chunks[1].source_heading is None
    assert chunks[0].char_start is None and chunks[0].char_end is None


def test_excludes_empty_chunks_and_enforces_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    chunks = [source_chunk(" "), source_chunk("one"), source_chunk("two")]
    chunking = service(monkeypatch, chunks)
    chunking.max_chunks = 1
    with pytest.raises(ChunkLimitExceededError):
        chunking.chunk(SimpleNamespace())


def test_chunker_failure_uses_typed_error(monkeypatch: pytest.MonkeyPatch) -> None:
    chunking = service(monkeypatch, [])
    chunking.chunker = SimpleNamespace(
        chunk=lambda _: (_ for _ in ()).throw(RuntimeError("docling detail"))
    )
    with pytest.raises(ChunkingError) as error:
        chunking.chunk(SimpleNamespace())
    assert "detail" not in str(error.value)
