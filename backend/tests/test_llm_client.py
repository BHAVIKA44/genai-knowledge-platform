import pytest

from app.core.config import Settings
from app.llm.client import (
    GeminiConfigurationError,
    GeminiInvalidResponseError,
    GeminiKnowledgeClient,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiTransientError,
)
from app.llm.models import EvidenceSource, KnowledgeAnalysis, KnowledgeClaim


def test_topics_are_normalized_and_deduplicated() -> None:
    analysis = KnowledgeAnalysis(summary="Summary", topics=[" RAG ", "rag", "LLMs"], claims=[])
    assert analysis.topics == ["RAG", "LLMs"]


def test_confidence_outside_range_is_rejected() -> None:
    with pytest.raises(ValueError):
        KnowledgeAnalysis.model_validate(
            {
                "summary": "Summary",
                "topics": [],
                "claims": [
                    {
                        "text": "Claim",
                        "confidence": 2,
                        "is_time_sensitive": False,
                        "requires_external_verification": False,
                    }
                ],
                "semantic_findings": [],
            }
        )


def test_empty_text_is_rejected_without_provider_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.llm.client.genai.Client", lambda **_: pytest.fail("provider must not be called")
    )
    client = GeminiKnowledgeClient(Settings(gemini_api_key="test"))
    with pytest.raises(GeminiInvalidResponseError):
        client.analyze_document(" ")


def test_missing_api_key_is_rejected_without_provider_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.llm.client.genai.Client", lambda **_: pytest.fail("provider must not be called")
    )
    with pytest.raises(GeminiConfigurationError):
        GeminiKnowledgeClient(Settings()).analyze_document("Document text")


def test_rate_limit_is_classified_without_provider_details() -> None:
    error = GeminiKnowledgeClient._classify_provider_error(RuntimeError("429 quota exceeded"))
    assert isinstance(error, GeminiRateLimitError)
    assert "quota" not in str(error).lower()


def test_unavailable_model_is_non_retryable_configuration_error() -> None:
    provider_error = type("ProviderError", (Exception,), {"code": 404})()
    error = GeminiKnowledgeClient._classify_provider_error(provider_error)
    assert isinstance(error, GeminiConfigurationError)


class Response:
    def __init__(self, text: str | None) -> None:
        self.text = text


class FakeClient:
    def __init__(self, responses: list[object]) -> None:
        self.responses = iter(responses)
        self.models = self
        self.calls = 0

    def generate_content(self, **_: object) -> Response:
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return Response(response if isinstance(response, str) else None)


def valid_response() -> str:
    return '{"summary":"Summary","topics":["RAG"],"claims":[]}'


def test_valid_response_after_malformed_response_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient(["not json", valid_response()])
    monkeypatch.setattr("app.llm.client.genai.Client", lambda **_: fake)
    result = GeminiKnowledgeClient(
        Settings(gemini_api_key="test", gemini_max_retries=2)
    ).analyze_document("text")
    assert result.summary == "Summary"
    assert fake.calls == 2


def test_retries_stop_at_configured_maximum(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient(["not json", "not json", "not json"])
    monkeypatch.setattr("app.llm.client.genai.Client", lambda **_: fake)
    with pytest.raises(GeminiInvalidResponseError):
        GeminiKnowledgeClient(
            Settings(gemini_api_key="test", gemini_max_retries=2)
        ).analyze_document("text")
    assert fake.calls == 3


def test_timeout_and_unexpected_errors_are_safely_mapped(monkeypatch: pytest.MonkeyPatch) -> None:
    timeout = FakeClient([TimeoutError()])
    monkeypatch.setattr("app.llm.client.genai.Client", lambda **_: timeout)
    with pytest.raises(GeminiTimeoutError):
        GeminiKnowledgeClient(
            Settings(gemini_api_key="test", gemini_max_retries=0)
        ).analyze_document("text")
    unexpected = FakeClient([RuntimeError("SDK secret detail")])
    monkeypatch.setattr("app.llm.client.genai.Client", lambda **_: unexpected)
    with pytest.raises(GeminiTransientError) as error:
        GeminiKnowledgeClient(
            Settings(gemini_api_key="test", gemini_max_retries=0)
        ).analyze_document("text")
    assert "secret" not in str(error.value)


def test_rate_limit_error_is_safely_mapped(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient([RuntimeError("429 quota exceeded")])
    monkeypatch.setattr("app.llm.client.genai.Client", lambda **_: fake)
    with pytest.raises(GeminiRateLimitError) as error:
        GeminiKnowledgeClient(
            Settings(gemini_api_key="test", gemini_max_retries=0)
        ).analyze_document("text")
    assert "quota" not in str(error.value).lower()


def test_returned_analysis_contains_only_domain_values(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient(
        [
            '{"proposed_title":"Title","summary":"Summary","topics":["RAG"],'
            '"claims":[{"text":"Claim","confidence":0.8,"is_time_sensitive":false,'
            '"requires_external_verification":false}]}'
        ]
    )
    monkeypatch.setattr("app.llm.client.genai.Client", lambda **_: fake)
    result = GeminiKnowledgeClient(Settings(gemini_api_key="test")).analyze_document("text")
    assert isinstance(result, KnowledgeAnalysis)
    assert result.model_dump() == {
        "proposed_title": "Title",
        "summary": "Summary",
        "topics": ["RAG"],
        "claims": [
            {
                "text": "Claim",
                "confidence": 0.8,
                "is_time_sensitive": False,
                "requires_external_verification": False,
            }
        ],
        "semantic_findings": [],
    }


class LogRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def warning(self, event: str, **fields: object) -> None:
        self.calls.append((event, fields))


def test_failure_logs_diagnostics_without_sensitive_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeClient([RuntimeError("provider detail")])
    recorder = LogRecorder()
    document_text = "Private document body"
    api_key = "secret-api-key"
    monkeypatch.setattr("app.llm.client.genai.Client", lambda **_: fake)
    monkeypatch.setattr("app.llm.client.logger", recorder)
    with pytest.raises(GeminiTransientError):
        GeminiKnowledgeClient(
            Settings(
                gemini_api_key=api_key,
                gemini_model="gemini-test",
                gemini_prompt_version="v1",
                gemini_max_retries=0,
            )
        ).analyze_document(document_text)
    assert len(recorder.calls) == 1
    event, fields = recorder.calls[0]
    assert event == "gemini_analysis_attempt_failed"
    assert fields["model"] == "gemini-test"
    assert fields["prompt_version"] == "v1"
    assert fields["attempt"] == 1
    assert fields["failure_category"] == "GeminiTransientError"
    assert isinstance(fields["elapsed_ms"], int)
    logged_values = repr(recorder.calls)
    assert document_text not in logged_values
    assert api_key not in logged_values
    assert "provider detail" not in logged_values


class GroundingResponse:
    def __init__(self, text: str, chunks: list[object]) -> None:
        self.text = text
        self.candidates = [
            type(
                "Candidate",
                (),
                {"grounding_metadata": type("Metadata", (), {"grounding_chunks": chunks})()},
            )()
        ]


class GroundingClient:
    def __init__(self, response: GroundingResponse | Exception) -> None:
        self.response = response
        self.models = self

    def generate_content(self, **_: object) -> GroundingResponse:
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_grounding_evidence_sources_are_normalized_and_do_not_leak_sdk_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunks = [
        type(
            "Chunk",
            (),
            {
                "web": type(
                    "Web", (), {"title": " Gemini Docs ", "uri": "https://example.com/docs "}
                )()
            },
        )(),
        type(
            "Chunk",
            (),
            {"web": type("Web", (), {"title": "Gemini Docs", "uri": "https://example.com/docs"})()},
        )(),
    ]
    response = GroundingResponse(
        '{"verifications":[{"claim":"Claim","verdict":"SUPPORTED","confidence":0.9,'
        '"explanation":"Supported."}]}',
        chunks,
    )
    monkeypatch.setattr("app.llm.client.genai.Client", lambda **_: GroundingClient(response))

    result = GeminiKnowledgeClient(Settings(gemini_api_key="test")).verify_claims(
        [
            KnowledgeClaim(
                text="Claim",
                confidence=0.8,
                is_time_sensitive=True,
                requires_external_verification=False,
            )
        ]
    )

    assert result.verifications[0].evidence_sources == [
        EvidenceSource(title="Gemini Docs", url="https://example.com/docs")
    ]
    assert "Chunk" not in repr(result)
    assert "Web" not in repr(result)


def test_grounding_failure_logs_no_claim_content_or_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claim_text = "Full document content must not be logged"
    api_key = "secret-api-key"
    recorder = LogRecorder()
    monkeypatch.setattr(
        "app.llm.client.genai.Client",
        lambda **_: GroundingClient(RuntimeError("raw provider payload")),
    )
    monkeypatch.setattr("app.llm.client.logger", recorder)

    with pytest.raises(GeminiTransientError):
        GeminiKnowledgeClient(Settings(gemini_api_key=api_key, gemini_max_retries=0)).verify_claims(
            [
                KnowledgeClaim(
                    text=claim_text,
                    confidence=0.8,
                    is_time_sensitive=False,
                    requires_external_verification=True,
                )
            ]
        )

    logged_values = repr(recorder.calls)
    assert claim_text not in logged_values
    assert api_key not in logged_values
    assert "raw provider payload" not in logged_values
