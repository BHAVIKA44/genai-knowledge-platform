from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, delete, select

from app.documents.chunk_models import DocumentChunk

chunk_table = DocumentChunk.__table__  # type: ignore[attr-defined]


class ChunkPersistenceError(Exception):
    pass


class DocumentChunkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_chunks(self, document_id: str, chunks: list[DocumentChunk]) -> None:
        self._validate_document_ids(document_id, chunks)
        try:
            self.session.add_all(chunks)
            self.session.commit()
        except SQLAlchemyError as error:
            self.session.rollback()
            raise ChunkPersistenceError("Document chunks could not be stored.") from error

    def replace_chunks(self, document_id: str, chunks: list[DocumentChunk]) -> None:
        self._validate_document_ids(document_id, chunks)
        try:
            self.session.exec(delete(DocumentChunk).where(chunk_table.c.document_id == document_id))
            self.session.add_all(chunks)
            self.session.commit()
        except SQLAlchemyError as error:
            self.session.rollback()
            raise ChunkPersistenceError("Document chunks could not be replaced.") from error

    def delete_chunks(self, document_id: str) -> None:
        try:
            self.session.exec(delete(DocumentChunk).where(chunk_table.c.document_id == document_id))
            self.session.commit()
        except SQLAlchemyError as error:
            self.session.rollback()
            raise ChunkPersistenceError("Document chunks could not be deleted.") from error

    def get_chunks(self, document_id: str) -> list[DocumentChunk]:
        try:
            return list(
                self.session.exec(
                    select(DocumentChunk)
                    .where(chunk_table.c.document_id == document_id)
                    .order_by(chunk_table.c.position)
                )
            )
        except SQLAlchemyError as error:
            raise ChunkPersistenceError("Document chunks could not be loaded.") from error

    @staticmethod
    def _validate_document_ids(document_id: str, chunks: list[DocumentChunk]) -> None:
        if any(chunk.document_id != document_id for chunk in chunks):
            raise ChunkPersistenceError("Chunks must belong to one document.")
