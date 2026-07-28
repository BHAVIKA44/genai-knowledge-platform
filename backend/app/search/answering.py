from dataclasses import dataclass

from app.llm.client import GeminiKnowledgeClient
from app.search.hybrid_search import (
    HybridSearchResult,
    HybridSearchService,
    RetrievedKnowledge,
)

MAX_ANSWER_CONTEXT_CHARACTERS = 12_000


@dataclass(frozen=True)
class SearchAnswer:
    answer: str
    results: list[HybridSearchResult]


class SearchAnswerService:
    def __init__(self, retrieval: HybridSearchService, client: GeminiKnowledgeClient) -> None:
        self.retrieval = retrieval
        self.client = client

    def answer(self, question: str) -> SearchAnswer:
        retrieved = self.retrieval.retrieve(question)
        results = [item.result for item in retrieved]
        if not retrieved:
            return SearchAnswer(
                answer="No reviewed knowledge was found for this question.",
                results=[],
            )
        context = self._context(retrieved)
        return SearchAnswer(
            answer=self.client.answer_question(question, context),
            results=results,
        )

    @staticmethod
    def _context(retrieved: list[RetrievedKnowledge]) -> str:
        remaining = MAX_ANSWER_CONTEXT_CHARACTERS
        sections = []
        for item in retrieved:
            if remaining <= 0:
                break
            text = item.content[:remaining]
            sections.append(f"Source: {item.result.title}\n{text}")
            remaining -= len(text)
        return "\n\n".join(sections)
