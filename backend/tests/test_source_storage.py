import pytest

from app.documents.source_storage import LocalSourceStorage, SourceNotFoundError, SourceStorageError


def test_stores_relative_unique_sources_with_extension(tmp_path) -> None:
    storage = LocalSourceStorage(str(tmp_path))
    first = storage.save(b"one", ".pdf")
    second = storage.save(b"two", ".pdf")
    assert first != second
    assert first.endswith(".pdf")
    assert storage.load(first) == b"one"


def test_missing_and_invalid_source_references_are_safe(tmp_path) -> None:
    storage = LocalSourceStorage(str(tmp_path))
    with pytest.raises(SourceNotFoundError):
        storage.load("missing.pdf")
    with pytest.raises(SourceStorageError):
        storage.load("../outside.pdf")
