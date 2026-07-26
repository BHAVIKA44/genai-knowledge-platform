import pytest
from sqlmodel import select

from app.core.config import Settings
from app.core.errors import DomainError
from app.documents.models import KnowledgeDocument
from app.documents.service import DocumentIngestionService
from app.documents.source_storage import LocalSourceStorage, SourceStorageError


def make_service(session, monkeypatch: pytest.MonkeyPatch, root: str) -> DocumentIngestionService:
    monkeypatch.setattr("app.documents.service.filetype.guess_mime", lambda *_: "text/plain")
    return DocumentIngestionService(
        session,
        Settings(database_url="sqlite://", source_storage_root=root),
        source_storage=LocalSourceStorage(root),
    )


def test_upload_stores_source_and_persists_relative_key(session, monkeypatch, tmp_path) -> None:
    service = make_service(session, monkeypatch, str(tmp_path))
    content = b"Large language models use transformer attention for GenAI applications."
    document = service.submit("notes.txt", content, "text/plain", "Notes")
    assert document.source_storage_key is not None
    assert "/" not in document.source_storage_key
    assert document.source_storage_key != document.source_filename
    assert service.source_storage.load(document.source_storage_key) == content


def test_rejected_or_duplicate_uploads_do_not_create_another_source(
    session, monkeypatch, tmp_path
) -> None:
    service = make_service(session, monkeypatch, str(tmp_path))
    content = b"Large language models use transformer attention for GenAI applications."
    service.submit("notes.txt", content, "text/plain", "Notes")
    with pytest.raises(DomainError):
        service.submit("duplicate.txt", content, "text/plain", "Duplicate")
    assert len(list(tmp_path.iterdir())) == 1
    with pytest.raises(DomainError):
        service.submit("bad.exe", content, "text/plain", "Bad")
    assert len(list(tmp_path.iterdir())) == 1


def test_storage_failure_does_not_persist_document(session, monkeypatch, tmp_path) -> None:
    service = make_service(session, monkeypatch, str(tmp_path))
    monkeypatch.setattr(
        service.source_storage,
        "save",
        lambda *_: (_ for _ in ()).throw(SourceStorageError("filesystem detail")),
    )
    with pytest.raises(SourceStorageError):
        service.submit("notes.txt", b"GenAI document content.", "text/plain", "Notes")
    assert session.exec(select(KnowledgeDocument)).first() is None
