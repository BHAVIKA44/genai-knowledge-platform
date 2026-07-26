import json
import time

import structlog
from google import genai
from google.genai import types

from app.core.config import Settings
from app.llm.models import (
    EvidenceSource,
    GroundedClaimAnalysis,
    KnowledgeAnalysis,
    KnowledgeClaim,
)
from app.llm.prompt import CLAIM_GROUNDING_PROMPT, KNOWLEDGE_EXTRACTION_PROMPT

logger = structlog.get_logger()


class GeminiConfigurationError(Exception):
    pass


class GeminiTimeoutError(Exception):
    pass


class GeminiRateLimitError(Exception):
    pass


class GeminiTransientError(Exception):
    pass


class GeminiInvalidResponseError(Exception):
    pass


class GeminiKnowledgeClient:
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.timeout_seconds = settings.gemini_timeout_seconds
        self.max_retries = settings.gemini_max_retries
        self.prompt_version = settings.gemini_prompt_version

    def analyze_document(self, text: str) -> KnowledgeAnalysis:
        if not text.strip():
            raise GeminiInvalidResponseError("Document text is empty.")
        if not self.api_key:
            raise GeminiConfigurationError("Gemini API key is not configured.")
        client = genai.Client(
            api_key=self.api_key,
            http_options={"timeout": int(self.timeout_seconds * 1000)},
        )
        for attempt in range(self.max_retries + 1):
            started_at = time.monotonic()
            failure: Exception
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=KNOWLEDGE_EXTRACTION_PROMPT.format(text=text),
                    config={"response_mime_type": "application/json"},
                )
                if not response.text:
                    raise GeminiInvalidResponseError("Gemini returned an empty response.")
                return KnowledgeAnalysis.model_validate(json.loads(response.text))
            except GeminiInvalidResponseError as error:
                failure = error
            except (json.JSONDecodeError, ValueError):
                failure = GeminiInvalidResponseError("Gemini returned invalid structured output.")
            except TimeoutError:
                failure = GeminiTimeoutError("Gemini request timed out.")
            except Exception as error:
                failure = self._classify_provider_error(error)
            logger.warning(
                "gemini_analysis_attempt_failed",
                model=self.model,
                prompt_version=self.prompt_version,
                attempt=attempt + 1,
                failure_category=type(failure).__name__,
                elapsed_ms=round((time.monotonic() - started_at) * 1000),
            )
            if isinstance(failure, GeminiConfigurationError) or attempt == self.max_retries:
                raise failure
        raise GeminiTransientError("Gemini request failed.")

    def verify_claims(self, claims: list[KnowledgeClaim]) -> GroundedClaimAnalysis:
        if not claims:
            raise GeminiInvalidResponseError("No claims were supplied for verification.")
        if not self.api_key:
            raise GeminiConfigurationError("Gemini API key is not configured.")
        client = genai.Client(
            api_key=self.api_key,
            http_options={"timeout": int(self.timeout_seconds * 1000)},
        )
        for attempt in range(self.max_retries + 1):
            started_at = time.monotonic()
            failure: Exception
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=CLAIM_GROUNDING_PROMPT.format(
                        claims=json.dumps([claim.model_dump() for claim in claims])
                    ),
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                    ),
                )
                if not response.text:
                    raise GeminiInvalidResponseError("Gemini returned an empty response.")
                analysis = GroundedClaimAnalysis.model_validate(json.loads(response.text))
                sources = self._grounding_sources(response)
                return GroundedClaimAnalysis(
                    verifications=[
                        verification.model_copy(update={"evidence_sources": sources})
                        for verification in analysis.verifications
                    ]
                )
            except GeminiInvalidResponseError as error:
                failure = error
            except (json.JSONDecodeError, ValueError):
                failure = GeminiInvalidResponseError("Gemini returned invalid structured output.")
            except TimeoutError:
                failure = GeminiTimeoutError("Gemini request timed out.")
            except Exception as error:
                failure = self._classify_provider_error(error)
            logger.warning(
                "gemini_grounding_attempt_failed",
                model=self.model,
                prompt_version=self.prompt_version,
                attempt=attempt + 1,
                failure_category=type(failure).__name__,
                elapsed_ms=round((time.monotonic() - started_at) * 1000),
            )
            if isinstance(failure, GeminiConfigurationError) or attempt == self.max_retries:
                raise failure
        raise GeminiTransientError("Gemini request failed.")

    @staticmethod
    def _grounding_sources(response: object) -> list[EvidenceSource]:
        sources: dict[str, EvidenceSource] = {}
        candidates = getattr(response, "candidates", []) or []
        metadata = getattr(candidates[0], "grounding_metadata", None) if candidates else None
        for chunk in getattr(metadata, "grounding_chunks", []) or []:
            web = getattr(chunk, "web", None)
            raw_url = getattr(web, "uri", None)
            url = str(raw_url).strip() if raw_url else ""
            if url:
                raw_title = getattr(web, "title", None)
                title = str(raw_title).strip() if raw_title else None
                sources.setdefault(
                    url,
                    EvidenceSource(title=title, url=url),
                )
        return list(sources.values())

    @staticmethod
    def _classify_provider_error(error: Exception) -> Exception:
        message = str(error).lower()
        if "rate" in message or "quota" in message or "429" in message:
            return GeminiRateLimitError("Gemini rate limit reached.")
        return GeminiTransientError("Gemini request failed.")
