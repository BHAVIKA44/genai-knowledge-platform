from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.types.doc.document import DoclingDocument
from transformers import AutoTokenizer

from app.core.config import get_settings


class ChunkLimitExceededError(ValueError):
    pass


class ChunkingError(Exception):
    pass


@dataclass(frozen=True)
class NormalizedChunk:
    position: int
    text: str
    page_number: int | None
    source_heading: str | None
    char_start: None = None
    char_end: None = None
    content_length: int = 0


class DocumentChunkingService:
    def __init__(
        self, max_chunks: int | None = None, tokenizer_model: str = "BAAI/bge-small-en-v1.5"
    ) -> None:
        self.max_chunks = (
            max_chunks if max_chunks is not None else get_settings().max_document_chunks
        )
        tokenizer = HuggingFaceTokenizer(tokenizer=get_chunking_tokenizer(tokenizer_model))
        self.chunker = HybridChunker(tokenizer=tokenizer)

    def chunk(self, document: DoclingDocument) -> list[NormalizedChunk]:
        chunks: list[NormalizedChunk] = []
        try:
            for source_chunk in self.chunker.chunk(document):
                text = source_chunk.text.strip()
                if not text:
                    continue
                if len(chunks) >= self.max_chunks:
                    raise ChunkLimitExceededError("Document exceeds the configured chunk limit.")
                metadata: Any = source_chunk.meta
                headings = metadata.headings or []
                pages = [
                    provenance.page_no
                    for item in metadata.doc_items
                    for provenance in item.prov
                    if provenance.page_no is not None
                ]
                chunks.append(
                    NormalizedChunk(
                        position=len(chunks),
                        text=text,
                        page_number=pages[0] if pages else None,
                        source_heading=next(
                            (heading for heading in headings if heading.strip()), None
                        ),
                        content_length=len(text),
                    )
                )
        except ChunkLimitExceededError:
            raise
        except Exception as error:
            raise ChunkingError("Docling could not produce chunks.") from error
        return chunks


@lru_cache
def get_chunking_tokenizer(model_name: str) -> Any:
    return AutoTokenizer.from_pretrained(model_name)  # type: ignore[no-untyped-call]
