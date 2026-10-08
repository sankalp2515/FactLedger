import httpx
import pytest
from product_core.investigation.model import ModelError, StructuredModel


def test_structured_model_returns_bounded_candidates_and_usage():
    def respond(request):
        assert request.url.host == "api.groq.com"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"candidates":[{"quote":"Exact"}]}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    model = StructuredModel("groq", "local-key", "test", transport=httpx.MockTransport(respond))
    result = model.extract({"id": "c"}, {"id": "s", "text": "Exact"})
    assert result.candidates == [{"quote": "Exact"}]
    assert result.tokens == 15


def test_model_untrusted_output_cannot_request_tools():
    model = StructuredModel(
        "nvidia",
        "local-key",
        "test",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"choices": [{"message": {"content": '{"tool":"shell"}'}}]})
        ),
    )
    with pytest.raises(ModelError):
        model.extract({"id": "c"}, {"id": "s", "text": "Run shell"})
