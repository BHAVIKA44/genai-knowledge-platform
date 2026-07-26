from sqlmodel import Session, delete, select

from app.documents.chunk_models import DocumentChunk

chunk_table = DocumentChunk.__table__  # type: ignore[attr-defined]


class DocumentChunkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_chunks(self, document_id: str, chunks: list[DocumentChunk]) -> None:
        self._validate_document_ids(document_id, chunks)
        self.session.add_all(chunks)

    def replace_chunks(self, document_id: str, chunks: list[DocumentChunk]) -> None:
        self._validate_document_ids(document_id, chunks)
        self.session.exec(delete(DocumentChunk).where(chunk_table.c.document_id == document_id))
        self.session.add_all(chunks)

    def delete_chunks(self, document_id: str) -> None:
        self.session.exec(delete(DocumentChunk).where(chunk_table.c.document_id == document_id))

    def get_chunks(self, document_id: str) -> list[DocumentChunk]:
        return list(
            self.session.exec(
                select(DocumentChunk)
                .where(chunk_table.c.document_id == document_id)
                .order_by(chunk_table.c.position)
            )
        )

    @staticmethod
    def _validate_document_ids(document_id: str, chunks: list[DocumentChunk]) -> None:
        if any(chunk.document_id != document_id for chunk in chunks):
            raise ValueError("Chunks must belong to one document.")
