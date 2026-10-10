import json

import httpx
import pytest
from product_core.config import Settings
from product_core.investigation.model import ModelError, StructuredModel


@pytest.mark.parametrize(
    "provider,model",
    [("openai", "gpt-4.1-mini"), ("anthropic", "claude-sonnet-4-6"), ("gemini", "gemini-2.5-flash")],
)
def test_provider_protocol_and_accounting(provider, model):
    def respond(request):
        body = json.loads(request.content)
        assert "private-test-key" not in str(request.url)
        content = '{"candidates":[{"quote":"Exact"}]}'
        if provider == "openai":
            assert request.url == "https://api.openai.com/v1/chat/completions"
            assert request.headers["authorization"] == "Bearer private-test-key"
            assert body["max_completion_tokens"] == 2500
            return httpx.Response(
                200,
                json={
                    "choices": [{"finish_reason": "stop", "message": {"content": content}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                },
            )
        if provider == "anthropic":
            # Newer Claude models reject custom sampling parameters.
            if "temperature" in body:
                return httpx.Response(400, json={"error": {"type": "invalid_request_error"}})
            assert request.url == "https://api.anthropic.com/v1/messages"
            assert request.headers["x-api-key"] == "private-test-key"
            assert request.headers["anthropic-version"] == "2023-06-01"
            assert body["system"] and body["max_tokens"] == 2500
            return httpx.Response(
                200,
                json={
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": content}],
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            )
        assert (
            request.url
            == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        )
        assert request.headers["x-goog-api-key"] == "private-test-key"
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        assert body["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 0
        return httpx.Response(
            200,
            json={
                "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": content}]}}],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 3,
                    "thoughtsTokenCount": 2,
                    "totalTokenCount": 15,
                },
            },
        )

    result = StructuredModel(
        provider, "private-test-key", model, transport=httpx.MockTransport(respond)
    ).extract({"id": "c"}, {"id": "s", "text": "Exact"})
    assert result.candidates == [{"quote": "Exact"}]
    assert result.tokens == 15
    assert result.metadata["prompt_tokens"] == 10
    assert result.metadata["completion_tokens"] == 5
    assert result.metadata["provider"] == provider


@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini"])
def test_provider_defaults_and_key_selection(provider):
    settings = Settings(_env_file=None, llm_provider=provider, **{provider + "_api_key": "test-only"})
    assert settings.llm_model.startswith(
        {"openai": "gpt-", "anthropic": "claude-", "gemini": "gemini-"}[provider]
    )
    assert settings.model_api_key(provider).get_secret_value() == "test-only"
    assert settings.model_api_key("groq").get_secret_value() == ""


@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini"])
def test_provider_failure_is_safe(provider):
    model = StructuredModel(
        provider,
        "private-test-key",
        "test",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(429, headers={"retry-after": "120"}, text="private-test-key")
        ),
    )
    with pytest.raises(ModelError, match="^MODEL_PROVIDER_HTTP_429$"):
        model.extract({}, {"id": "s", "text": "Exact"})


@pytest.mark.parametrize(
    "provider,payload",
    [
        ("openai", {"choices": [{"finish_reason": "length", "message": {"content": '{"candidates":[]}'}}]}),
        (
            "anthropic",
            {"stop_reason": "max_tokens", "content": [{"type": "text", "text": '{"candidates":[]}'}]},
        ),
        (
            "gemini",
            {
                "candidates": [
                    {"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": '{"candidates":[]}'}]}}
                ]
            },
        ),
    ],
)
def test_truncated_response_is_not_accepted(provider, payload):
    model = StructuredModel(
        provider, "test", "test", transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    )
    with pytest.raises(ModelError, match="MODEL_INVALID_STRUCTURED_OUTPUT"):
        model.extract({}, {"id": "s", "text": "Exact"})


def test_gemini_model_cannot_change_request_url():
    with pytest.raises(ModelError, match="MODEL_NAME_INVALID"):
        StructuredModel("gemini", "test", "../../other?key=secret")


@pytest.mark.parametrize(
    "provider,payload",
    [
        (
            "openai",
            {"choices": [{"message": {"content": '{"candidates":[]}'}}], "usage": {"prompt_tokens": 10}},
        ),
        (
            "anthropic",
            {
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": '{"candidates":[]}'}],
                "usage": {"input_tokens": 10},
            },
        ),
        (
            "gemini",
            {
                "candidates": [
                    {"finishReason": "STOP", "content": {"parts": [{"text": '{"candidates":[]}'}]}}
                ],
                "usageMetadata": {"promptTokenCount": 10},
            },
        ),
    ],
)
def test_incomplete_usage_does_not_release_token_reservation(provider, payload):
    model = StructuredModel(
        provider, "test", "test", transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    )
    result = model.extract({}, {"id": "s", "text": "Exact"})
    assert result.tokens == 0
    assert result.metadata["usage_reported"] is False
