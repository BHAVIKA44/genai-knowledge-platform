import re
from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from typing import TypeVar, cast

import structlog
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.documents.chunk_models import DocumentChunk
from app.documents.models import DocumentStatus, KnowledgeDocument
from app.embeddings import DocumentEmbedder

KEYWORD_WEIGHT = 0.5
VECTOR_WEIGHT = 0.5
SNIPPET_LENGTH = 280
KEYWORD_SCORE_FRACTION = 0.25

chunk_table = DocumentChunk.__table__  # type: ignore[attr-defined]
document_table = KnowledgeDocument.__table__  # type: ignore[attr-defined]
logger = structlog.get_logger()
type SearchRow = tuple[str, str, str, int, float]
type ChunkKey = tuple[str, int]
ScoreKey = TypeVar("ScoreKey", bound=Hashable)


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


@dataclass(frozen=True)
class RetrievedKnowledge:
    result: HybridSearchResult
    content: str


class HybridSearchService:
    def __init__(
        self,
        session: Session,
        embedder: DocumentEmbedder | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.embedder = embedder or DocumentEmbedder()
        self.minimum_vector_similarity = (settings or get_settings()).minimum_vector_similarity

    def search(self, query: str) -> list[HybridSearchResult]:
        return self._unique_results(self.retrieve(query))

    def retrieve(self, query: str) -> list[RetrievedKnowledge]:
        if not re.search(r"[\w]", query):
            return []
        try:
            query_vector = self.embedder.embed_query(query)
            keyword_hits = self._keyword_hits(query)
            vector_hits = self._vector_hits(query_vector)
            keyword_scores = self._normalize_scores(
                {chunk_key: hit[3] for chunk_key, hit in keyword_hits.items()}
            )
            vector_scores = self._normalize_scores(
                {chunk_key: hit[3] for chunk_key, hit in vector_hits.items()}
            )
            results = []
            for chunk_key in keyword_hits.keys() | vector_hits.keys():
                keyword_hit = keyword_hits.get(chunk_key)
                vector_hit = vector_hits.get(chunk_key)
                document_hit = keyword_hit or vector_hit
                if document_hit is None:
                    continue
                document_id, _ = chunk_key
                keyword_score = keyword_scores.get(chunk_key, 0.0)
                vector_score = vector_scores.get(chunk_key, 0.0)
                results.append(
                    RetrievedKnowledge(
                        result=HybridSearchResult(
                            document_id=document_id,
                            title=document_hit[0],
                            snippet=self._snippet(document_hit[1]),
                            keyword_score=keyword_score,
                            vector_score=vector_score,
                            final_score=(keyword_score * KEYWORD_WEIGHT)
                            + (vector_score * VECTOR_WEIGHT),
                        ),
                        content=document_hit[1],
                    )
                )
            return sorted(
                results,
                key=lambda item: (
                    -item.result.final_score,
                    -item.result.keyword_score,
                    -item.result.vector_score,
                    item.result.document_id,
                ),
            )
        except HybridSearchError:
            raise
        except Exception as error:
            logger.exception("hybrid_search_failed", failure_category=type(error).__name__)
            raise HybridSearchError("Search could not complete.") from error

    def _keyword_hits(self, query: str) -> dict[ChunkKey, tuple[str, str, int, float]]:
        tsquery = func.websearch_to_tsquery("english", query)
        return self._keyword_hits_for_query(tsquery)

    def _keyword_hits_for_query(
        self, tsquery: object
    ) -> dict[ChunkKey, tuple[str, str, int, float]]:
        title_vector = func.to_tsvector(
            "english",
            func.concat_ws(" ", document_table.c.title, document_table.c.source_filename),
        )
        text_vector = func.to_tsvector("english", chunk_table.c.text)
        search_vector = title_vector.op("||")(text_vector)
        rank = func.ts_rank_cd(text_vector, tsquery) + (2 * func.ts_rank_cd(title_vector, tsquery))
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
            .where(search_vector.op("@@")(tsquery))
            .order_by(rank.desc(), document_table.c.id, chunk_table.c.position)
        )
        rows = cast(Iterable[SearchRow], self.session.exec(statement))
        hits = self._chunk_hits(rows)
        if not hits:
            return hits
        minimum_score = max(hit[3] for hit in hits.values()) * KEYWORD_SCORE_FRACTION
        return {document_id: hit for document_id, hit in hits.items() if hit[3] >= minimum_score}

    def _vector_hits(
        self, query_vector: list[float]
    ) -> dict[ChunkKey, tuple[str, str, int, float]]:
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
        return self._chunk_hits(row for row in rows if row[4] >= self.minimum_vector_similarity)

    @staticmethod
    def _chunk_hits(rows: Iterable[SearchRow]) -> dict[ChunkKey, tuple[str, str, int, float]]:
        hits: dict[ChunkKey, tuple[str, str, int, float]] = {}
        for document_id, title, text, position, score in rows:
            candidate = (title, text, position, score)
            key = (document_id, position)
            current = hits.get(key)
            if current is None or candidate[3] > current[3]:
                hits[key] = candidate
        return hits

    @staticmethod
    def _unique_results(retrieved: list[RetrievedKnowledge]) -> list[HybridSearchResult]:
        results: list[HybridSearchResult] = []
        seen_document_ids: set[str] = set()
        for item in retrieved:
            if item.result.document_id in seen_document_ids:
                continue
            seen_document_ids.add(item.result.document_id)
            results.append(item.result)
        return results

    @staticmethod
    def _normalize_scores(scores: dict[ScoreKey, float]) -> dict[ScoreKey, float]:
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
