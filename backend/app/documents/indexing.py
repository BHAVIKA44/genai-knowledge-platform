from dataclasses import dataclass

from sqlmodel import Session

from app.documents.chunk_models import DocumentChunk
from app.documents.chunk_repository import DocumentChunkRepository
from app.documents.chunking import DocumentChunkingService
from app.documents.models import KnowledgeDocument
from app.documents.stored_document_parser import StoredDocumentParser
from app.embeddings import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, DocumentEmbedder


class DocumentIndexingError(Exception):
    pass


@dataclass(frozen=True)
class DocumentIndexingResult:
    chunk_count: int
    embedding_model: str


class DocumentIndexingService:
    def __init__(
        self,
        session: Session,
        parser: StoredDocumentParser,
        chunker: DocumentChunkingService,
        embedder: DocumentEmbedder,
        repository: DocumentChunkRepository,
    ) -> None:
        self.session = session
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder
        self.repository = repository

    def index(self, document: KnowledgeDocument) -> DocumentIndexingResult:
        if not document.source_storage_key:
            raise DocumentIndexingError("Stored source is required for indexing.")
        try:
            parsed = self.parser.parse(document.source_storage_key, document.document_type)
            chunks = self.chunker.chunk(parsed.document)
            if not chunks:
                raise DocumentIndexingError("No indexable document content was produced.")
            vectors = self.embedder.embed_documents([chunk.text for chunk in chunks])
            if len(chunks) != len(vectors) or any(
                len(vector) != EMBEDDING_DIMENSIONS for vector in vectors
            ):
                raise DocumentIndexingError("Document indexing output is invalid.")
            records = [
                DocumentChunk(
                    document_id=document.id,
                    position=chunk.position,
                    text=chunk.text,
                    page_number=chunk.page_number,
                    source_heading=chunk.source_heading,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    content_length=chunk.content_length,
                    embedding_model=EMBEDDING_MODEL,
                    embedding=vector,
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
            self.repository.replace_chunks(document.id, records)
            return DocumentIndexingResult(len(records), EMBEDDING_MODEL)
        except DocumentIndexingError:
            raise
        except Exception as error:
            raise DocumentIndexingError("Document indexing could not complete.") from error
