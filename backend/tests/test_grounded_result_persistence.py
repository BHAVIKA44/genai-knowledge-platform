import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import JSON

from app.documents.models import DocumentStatus, DocumentType, KnowledgeDocument


def document(
    grounded_claim_verifications: list[dict[str, object]] | None = None,
) -> KnowledgeDocument:
    return KnowledgeDocument(
        title="Grounded claims",
        source_filename="claims.md",
        storage_filename="claims.md",
        document_type=DocumentType.MARKDOWN,
        status=DocumentStatus.APPROVED,
        sha256="grounded-claims",
        grounded_claim_verifications=grounded_claim_verifications,
    )


def test_normalized_grounded_results_persist_on_a_document(session) -> None:
    verifications = [
        {
            "claim": "Gemini supports grounding.",
            "verdict": "SUPPORTED",
            "confidence": 0.9,
            "explanation": "The cited documentation describes grounding.",
            "evidence_sources": [{"title": "Documentation", "url": "https://example.com"}],
            "verified_at": "2026-07-26T12:00:00+00:00",
        },
        {
            "claim": "A model feature changed recently.",
            "verdict": "INSUFFICIENT_EVIDENCE",
            "confidence": 0.3,
            "explanation": "No source was returned.",
            "evidence_sources": [],
            "verified_at": "2026-07-26T12:01:00+00:00",
        },
    ]
    record = document(verifications)
    session.add(record)
    session.commit()
    session.expire_all()

    stored = session.get(KnowledgeDocument, record.id)

    assert stored is not None
    assert stored.grounded_claim_verifications == verifications


def test_document_without_grounded_results_remains_readable(session) -> None:
    record = document()
    session.add(record)
    session.commit()
    session.expire_all()

    stored = session.get(KnowledgeDocument, record.id)

    assert stored is not None
    assert stored.grounded_claim_verifications is None


def test_non_serializable_provider_values_are_rejected_before_persistence() -> None:
    with pytest.raises(ValueError, match="JSON values"):
        document([{"claim": "Claim", "raw_response": object()}])


class Operations:
    def __init__(self) -> None:
        self.added: list[tuple[str, object]] = []
        self.dropped: list[tuple[str, str]] = []

    def add_column(self, table: str, column: object) -> None:
        self.added.append((table, column))

    def drop_column(self, table: str, column: str) -> None:
        self.dropped.append((table, column))


def migration_module():
    path = Path(__file__).parents[1] / "alembic/versions/0006_add_grounded_claim_verifications.py"
    specification = importlib.util.spec_from_file_location("grounded_results_migration", path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_grounded_results_migration_adds_only_the_nullable_json_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = migration_module()
    operations = Operations()
    monkeypatch.setattr(migration, "op", operations)

    migration.upgrade()

    assert len(operations.added) == 1
    table, column = operations.added[0]
    assert table == "knowledge_documents"
    assert column.name == "grounded_claim_verifications"
    assert isinstance(column.type, JSON)
    assert column.nullable is True


def test_grounded_results_migration_downgrade_removes_only_its_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = migration_module()
    operations = Operations()
    monkeypatch.setattr(migration, "op", operations)

    migration.downgrade()

    assert operations.dropped == [("knowledge_documents", "grounded_claim_verifications")]
