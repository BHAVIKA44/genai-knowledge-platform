from datetime import datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.documents.models import now_utc


class DocumentChunk(SQLModel, table=True):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "position", name="uq_document_chunks_document_position"),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    document_id: str = Field(
        sa_column=Column(
            ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    position: int
    text: str
    page_number: int | None = None
    source_heading: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    content_length: int
    embedding_model: str
    embedding: list[float] = Field(sa_column=Column(Vector(384), nullable=False))
    created_at: datetime = Field(default_factory=now_utc, nullable=False)
