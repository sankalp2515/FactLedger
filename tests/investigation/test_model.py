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
    assert len(selected) <= 24000
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
    assert json.loads(data)["document"]["text"] == original[:24000]
    assert meta["selection_truncated"] is True
    assert meta["selected_ranges"] == [{"start": 0, "end": 24000}]
