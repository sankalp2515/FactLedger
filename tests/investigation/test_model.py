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
    assert result.metadata["prompt_tokens"] == 10
    assert result.metadata["completion_tokens"] == 5


@pytest.mark.parametrize(
    "usage", [{"prompt_tokens": -1, "completion_tokens": 2}, {"prompt_tokens": True, "completion_tokens": 2}]
)
def test_rejects_invalid_usage_split(usage):
    model = StructuredModel(
        "groq",
        "local-key",
        "test",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"choices": [{"message": {"content": '{"candidates":[]}'}}], "usage": usage}
            )
        ),
    )
    with pytest.raises(ModelError, match="MODEL_INVALID_USAGE"):
        model.extract({"id": "c"}, {"id": "s", "text": "Exact"})


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


def test_long_document_includes_late_relevant_literal_passage():
    import json

    from product_core.investigation.model import prepare_input

    passage = "Project Lotus was approved in India on 29 February 2024."
    original = "Menu and navigation. " * 3000 + passage + " Footer. " * 3000
    data, meta = prepare_input(
        {"subject": "Project Lotus", "stage": "APPROVED"}, {"id": "s", "text": original}
    )
    selected = json.loads(data)["document"]["text"]
    assert passage in selected
    assert len(selected) <= 8000
    assert meta["selection_truncated"] is True
    for region in meta["selected_ranges"]:
        assert original[region["start"] : region["end"]] in selected
    assert any(region["start"] > 24000 for region in meta["selected_ranges"])


def test_small_document_is_not_rewritten_by_selection():
    import json

    from product_core.investigation.model import prepare_input

    original = "Heading\n\n  Exact record with spacing and Unicode: \u20b9 75,021 crore."
    data, meta = prepare_input({"subject": "Record"}, {"id": "s", "text": original})
    assert json.loads(data)["document"]["text"] == original
    assert meta["selected_ranges"] == [{"start": 0, "end": len(original)}]
    assert meta["selection_truncated"] is False


def test_irrelevant_long_document_remains_explicitly_partial():
    import json

    from product_core.investigation.model import prepare_input

    original = "Unrelated record. " * 2000
    data, meta = prepare_input({"subject": "Absent project"}, {"id": "s", "text": original})
    assert json.loads(data)["document"]["text"] == original[:8000]
    assert meta["selection_truncated"] is True
    assert meta["selected_ranges"] == [{"start": 0, "end": 8000}]


def test_rate_limit_waits_for_provider_then_returns_only_successful_usage():
    calls = []
    waits = []

    def respond(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "3"})
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"content": '{"candidates":[]}'}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            },
        )

    model = StructuredModel(
        "groq",
        "test",
        "test",
        transport=httpx.MockTransport(respond),
        on_rate_limit=lambda seconds, attempt: waits.append((seconds, attempt)),
    )
    result = model.extract({}, {"id": "s", "text": "Exact"})
    assert result.tokens == 120
    assert result.metadata["rate_limit_retries"] == 1
    assert waits == [(3, 1)]


def test_rate_limit_retries_are_bounded_without_shortening_provider_wait():
    waits = []
    model = StructuredModel(
        "groq",
        "test",
        "test",
        transport=httpx.MockTransport(lambda _: httpx.Response(429, headers={"retry-after": "20"})),
        on_rate_limit=lambda seconds, attempt: waits.append((seconds, attempt)),
    )
    with pytest.raises(ModelError, match="MODEL_PROVIDER_HTTP_429"):
        model.extract({}, {"id": "s", "text": "Exact"})
    assert waits == [(20, 1), (20, 2)]
    waits.clear()
    model.transport = httpx.MockTransport(lambda _: httpx.Response(429, headers={"retry-after": "120"}))
    with pytest.raises(ModelError, match="MODEL_PROVIDER_HTTP_429"):
        model.extract({}, {"id": "s", "text": "Exact"})
    assert waits == []


def test_network_failures_are_not_blindly_retried():
    attempts = []

    def fail(request):
        attempts.append(request)
        raise httpx.ReadTimeout("Private provider message", request=request)

    model = StructuredModel("groq", "test", "test", transport=httpx.MockTransport(fail))
    with pytest.raises(ModelError, match="^MODEL_PROVIDER_NETWORK_ERROR$"):
        model.extract({}, {"id": "s", "text": "Exact"})
    assert len(attempts) == 1


def test_large_record_uses_compact_literal_windows_without_losing_late_subject():
    import json

    from product_core.investigation.model import prepare_input

    passage = "Atal Setu was inaugurated in Navi Mumbai in January 2024."
    original = "Menu navigation and unrelated archive entries. " * 350 + passage + " Footer. " * 100
    data, meta = prepare_input({"subject": "Atal Setu"}, {"id": "s", "text": original})
    selected = json.loads(data)["document"]["text"]
    assert len(selected) <= 8000
    assert passage in selected
    assert meta["selection_truncated"] is True
    for region in meta["selected_ranges"]:
        assert original[region["start"] : region["end"]] in selected


def test_groq_gpt_oss_uses_supported_strict_evidence_schema():
    import json

    def respond(request):
        body = json.loads(request.content)
        fmt = body["response_format"]
        if fmt.get("type") != "json_schema" or not fmt.get("json_schema", {}).get("strict"):
            return httpx.Response(400)
        schema = fmt["json_schema"]["schema"]
        item = schema["properties"]["candidates"]["items"]
        assert schema["additionalProperties"] is False
        assert item["additionalProperties"] is False
        assert {"quote", "relation", "geography", "period", "stage"} <= set(item["required"])
        assert body["reasoning_effort"] == "low"
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"content": '{"candidates":[]}'}}],
                "usage": {"prompt_tokens": 80, "completion_tokens": 20},
            },
        )

    result = StructuredModel(
        "groq", "test", "openai/gpt-oss-120b", transport=httpx.MockTransport(respond)
    ).extract({"subject": "Atal Setu"}, {"id": "s", "text": "Exact preserved record."})
    assert result.candidates == []
    assert result.tokens == 100
