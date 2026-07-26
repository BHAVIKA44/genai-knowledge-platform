import json
import time

import structlog
from google import genai

from app.core.config import Settings
from app.llm.models import KnowledgeAnalysis
from app.llm.prompt import KNOWLEDGE_EXTRACTION_PROMPT

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

    @staticmethod
    def _classify_provider_error(error: Exception) -> Exception:
        message = str(error).lower()
        if "rate" in message or "quota" in message or "429" in message:
            return GeminiRateLimitError("Gemini rate limit reached.")
        return GeminiTransientError("Gemini request failed.")
