from collections.abc import Iterable
from dataclasses import dataclass
from typing import cast

import structlog
from sqlalchemy import func
from sqlmodel import Session, select

from app.documents.chunk_models import DocumentChunk
from app.documents.models import DocumentStatus, KnowledgeDocument
from app.embeddings import DocumentEmbedder

KEYWORD_WEIGHT = 0.5
VECTOR_WEIGHT = 0.5
SNIPPET_LENGTH = 280

chunk_table = DocumentChunk.__table__  # type: ignore[attr-defined]
document_table = KnowledgeDocument.__table__  # type: ignore[attr-defined]
logger = structlog.get_logger()
type SearchRow = tuple[str, str, str, int, float]


@dataclass(frozen=True)
class HybridSearchResult:
    document_id: str
    title: str
    snippet: str
    keyword_score: float
    vector_score: float
    final_score: float


class HybridSearchError(Exception):
    pass


class HybridSearchService:
    def __init__(self, session: Session, embedder: DocumentEmbedder | None = None) -> None:
        self.session = session
        self.embedder = embedder or DocumentEmbedder()

    def search(self, query: str) -> list[HybridSearchResult]:
        try:
            query_vector = self.embedder.embed_query(query)
            keyword_hits = self._keyword_hits(query)
            vector_hits = self._vector_hits(query_vector)
            keyword_scores = self._normalize_scores(
                {document_id: hit[3] for document_id, hit in keyword_hits.items()}
            )
            vector_scores = self._normalize_scores(
                {document_id: hit[3] for document_id, hit in vector_hits.items()}
            )
            results = []
            for document_id in keyword_hits.keys() | vector_hits.keys():
                keyword_hit = keyword_hits.get(document_id)
                vector_hit = vector_hits.get(document_id)
                document_hit = keyword_hit or vector_hit
                if document_hit is None:
                    continue
                keyword_score = keyword_scores.get(document_id, 0.0)
                vector_score = vector_scores.get(document_id, 0.0)
                results.append(
                    HybridSearchResult(
                        document_id=document_id,
                        title=document_hit[0],
                        snippet=self._snippet(document_hit[1]),
                        keyword_score=keyword_score,
                        vector_score=vector_score,
                        final_score=(keyword_score * KEYWORD_WEIGHT)
                        + (vector_score * VECTOR_WEIGHT),
                    )
                )
            return sorted(
                results,
                key=lambda result: (
                    -result.final_score,
                    -result.keyword_score,
                    -result.vector_score,
                    result.document_id,
                ),
            )
        except HybridSearchError:
            raise
        except Exception as error:
            logger.exception("hybrid_search_failed", failure_category=type(error).__name__)
            raise HybridSearchError("Search could not complete.") from error

    def _keyword_hits(self, query: str) -> dict[str, tuple[str, str, int, float]]:
        tsquery = func.websearch_to_tsquery("english", query)
        text_vector = func.to_tsvector("english", chunk_table.c.text)
        rank = func.ts_rank_cd(text_vector, tsquery)
        statement = (
            select(  # type: ignore[call-overload]
                document_table.c.id,
                document_table.c.title,
                chunk_table.c.text,
                chunk_table.c.position,
                rank.label("score"),
            )
            .join(chunk_table, chunk_table.c.document_id == document_table.c.id)
            .where(document_table.c.status == DocumentStatus.APPROVED)
            .where(text_vector.op("@@")(tsquery))
            .order_by(rank.desc(), document_table.c.id, chunk_table.c.position)
        )
        rows = cast(Iterable[SearchRow], self.session.exec(statement))
        return self._best_hits(rows)

    def _vector_hits(self, query_vector: list[float]) -> dict[str, tuple[str, str, int, float]]:
        distance = chunk_table.c.embedding.cosine_distance(query_vector)
        similarity = (1 - distance).label("score")
        statement = (
            select(  # type: ignore[call-overload]
                document_table.c.id,
                document_table.c.title,
                chunk_table.c.text,
                chunk_table.c.position,
                similarity,
            )
            .join(chunk_table, chunk_table.c.document_id == document_table.c.id)
            .where(document_table.c.status == DocumentStatus.APPROVED)
            .order_by(distance, document_table.c.id, chunk_table.c.position)
        )
        rows = cast(Iterable[SearchRow], self.session.exec(statement))
        return self._best_hits(rows)

    @staticmethod
    def _best_hits(rows: Iterable[SearchRow]) -> dict[str, tuple[str, str, int, float]]:
        hits: dict[str, tuple[str, str, int, float]] = {}
        for document_id, title, text, position, score in rows:
            candidate = (title, text, position, score)
            current = hits.get(document_id)
            if current is None or candidate[3] > current[3]:
                hits[document_id] = candidate
        return hits

    @staticmethod
    def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
        if not scores:
            return {}
        minimum = min(scores.values())
        maximum = max(scores.values())
        if minimum == maximum:
            return {document_id: 1.0 for document_id in scores}
        return {
            document_id: (score - minimum) / (maximum - minimum)
            for document_id, score in scores.items()
        }

    @staticmethod
    def _snippet(text: str) -> str:
        return " ".join(text.split())[:SNIPPET_LENGTH]
