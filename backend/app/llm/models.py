from pydantic import BaseModel, Field, field_validator


class KnowledgeClaim(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    is_time_sensitive: bool
    requires_external_verification: bool


class KnowledgeAnalysis(BaseModel):
    proposed_title: str | None = None
    summary: str = Field(min_length=1)
    topics: list[str]
    claims: list[KnowledgeClaim]

    @field_validator("topics")
    @classmethod
    def normalize_topics(cls, value: list[str]) -> list[str]:
        normalized: dict[str, str] = {}
        for topic in value:
            cleaned = " ".join(topic.split())
            if cleaned:
                normalized.setdefault(cleaned.casefold(), cleaned)
        return list(normalized.values())
