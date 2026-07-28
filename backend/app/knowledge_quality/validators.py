import re
from pathlib import Path

from app.core.config import Settings
from app.knowledge_quality.models import (
    FindingCategory,
    FindingSeverity,
    QualityFinding,
    QualityValidationInput,
    ValidatorResult,
)

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Generative AI": ("generative ai", "genai", "generative artificial intelligence"),
    "Large Language Models": ("large language model", "llm", "language model"),
    "Retrieval-Augmented Generation": ("retrieval augmented", "rag", "retrieval"),
    "Embeddings": ("embedding", "embeddings", "vector database", "vector search"),
    "Transformers": ("transformer", "attention mechanism", "self-attention"),
    "Prompt Engineering": ("prompt engineering", "prompt", "few-shot"),
    "Agents": ("agent", "tool calling", "model context protocol", "mcp"),
}
ENGLISH_MARKERS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "before",
    "can",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "that",
    "the",
    "this",
    "to",
    "will",
    "with",
}


class MetadataValidator:
    def validate(self, value: QualityValidationInput) -> ValidatorResult:
        if value.title.strip():
            return ValidatorResult()
        return ValidatorResult(
            findings=[
                QualityFinding(
                    code="MISSING_TITLE",
                    category=FindingCategory.METADATA,
                    severity=FindingSeverity.INFO,
                    confidence=1,
                    title="Title is missing",
                    explanation="A title makes this knowledge easier to identify.",
                    suggested_action=(
                        "You can add a clear title to make this resource easier to identify."
                    ),
                    original_value="",
                    suggested_value=Path(value.source_filename).stem.replace("_", " ").strip(),
                )
            ]
        )


class ExtractionQualityValidator:
    def __init__(self, settings: Settings) -> None:
        self.minimum_meaningful_characters = settings.min_meaningful_characters

    def validate(self, value: QualityValidationInput) -> ValidatorResult:
        normalized = re.sub(r"\s+", " ", value.extracted_text).strip()
        if not normalized:
            return ValidatorResult(
                findings=[
                    QualityFinding(
                        code="EMPTY_DOCUMENT",
                        category=FindingCategory.EXTRACTION_QUALITY,
                        severity=FindingSeverity.BLOCKING,
                        confidence=1,
                        title="Document has no readable text",
                        explanation="The extracted document content is empty.",
                        suggested_action="Upload a document with selectable text.",
                    )
                ]
            )
        meaningful_characters = len(re.sub(r"\W", "", normalized))
        if meaningful_characters < self.minimum_meaningful_characters:
            return ValidatorResult(
                findings=[
                    QualityFinding(
                        code="INSUFFICIENT_CONTENT",
                        category=FindingCategory.EXTRACTION_QUALITY,
                        severity=FindingSeverity.BLOCKING,
                        confidence=1,
                        title="Document does not contain enough useful text",
                        explanation="The extracted content is below the minimum useful length.",
                        suggested_action=(
                            "Upload a document with at least "
                            f"{self.minimum_meaningful_characters} meaningful characters."
                        ),
                    )
                ]
            )
        return ValidatorResult()


class DomainRelevanceValidator:
    def validate(self, value: QualityValidationInput) -> ValidatorResult:
        words = re.findall(r"[a-zA-Z]+", value.extracted_text.lower())
        english_hits = sum(word in ENGLISH_MARKERS for word in words)
        if len(words) < 10 or english_hits == 0:
            return ValidatorResult(
                findings=[
                    QualityFinding(
                        code="UNSUPPORTED_LANGUAGE",
                        category=FindingCategory.DOMAIN_RELEVANCE,
                        severity=FindingSeverity.BLOCKING,
                        confidence=0.95,
                        title="English-language content is required",
                        explanation="This document does not appear to contain enough English text.",
                        suggested_action="Upload an English GenAI learning resource.",
                    )
                ]
            )
        topics = [
            topic
            for topic, keywords in TOPIC_KEYWORDS.items()
            if any(keyword in value.extracted_text.lower() for keyword in keywords)
        ]
        if not topics:
            return ValidatorResult(
                findings=[
                    QualityFinding(
                        code="NON_GENAI_CONTENT",
                        category=FindingCategory.DOMAIN_RELEVANCE,
                        severity=FindingSeverity.BLOCKING,
                        confidence=0.95,
                        title="Document is outside the GenAI knowledge scope",
                        explanation="The document does not match supported Generative AI topics.",
                        suggested_action="Upload material about LLMs, RAG, embeddings, or agents.",
                    )
                ]
            )
        return ValidatorResult(
            findings=[
                QualityFinding(
                    code="GENAI_RELEVANT",
                    category=FindingCategory.DOMAIN_RELEVANCE,
                    severity=FindingSeverity.INFO,
                    confidence=0.95,
                    title="GenAI relevance confirmed",
                    explanation="The document matches supported Generative AI topics.",
                )
            ],
            detected_topics=topics,
        )


class DuplicateValidator:
    def validate(self, value: QualityValidationInput) -> ValidatorResult:
        if not value.is_exact_duplicate:
            return ValidatorResult()
        return ValidatorResult(
            findings=[
                QualityFinding(
                    code="EXACT_DUPLICATE",
                    category=FindingCategory.DUPLICATE,
                    severity=FindingSeverity.BLOCKING,
                    confidence=1,
                    title="Exact duplicate detected",
                    explanation="This document matches an existing submission exactly.",
                    suggested_action="Open the existing document instead of uploading it again.",
                )
            ]
        )
