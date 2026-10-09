from types import SimpleNamespace

import pytest
from product_core.investigation.accounting import cost_summary, model_cost


def test_model_cost_uses_reported_split_and_pinned_rates():
    pricing = {"llm_input_usd_per_million": 0.6, "llm_output_usd_per_million": 0.8}
    assert model_cost({"prompt_tokens": 1000, "completion_tokens": 500}, pricing) == pytest.approx(0.001)
    assert model_cost({"usage_reported": True}, pricing) is None


@pytest.mark.parametrize("pending_state", ["OUTCOME_UNKNOWN", "ACKNOWLEDGED"])
def test_breakdown_includes_unknown_reservations_and_reconciled_models(pending_state):
    run = SimpleNamespace(
        plan={"pricing": {"llm_provider": "groq"}},
        usage={"usd": 0.011},
        checkpoint={
            "actions": {
                "search:one": {"state": pending_state, "amount": {"searches": 1, "usd": 0.01}},
                "extract:one": {
                    "state": "COMPLETED",
                    "amount": {"usd": 0.03, "tokens": 5000},
                    "reconciled": {"usd": 0.001, "tokens": 1500},
                    "outcome": {
                        "metadata": {"provider": "groq", "prompt_tokens": 1000, "completion_tokens": 500}
                    },
                },
                "extract:fixture": {"state": "COMPLETED", "amount": {}, "outcome": {}},
            }
        },
    )
    summary = cost_summary(run)
    assert summary["estimated"] is True
    assert summary["total_usd"] == pytest.approx(0.011)
    assert summary["uncertain_reserved_usd"] == pytest.approx(0.01)
    assert summary["providers"]["serpapi"]["attempts"] == 1
    assert summary["providers"]["groq"]["usd"] == pytest.approx(0.001)
    assert summary["providers"]["groq"]["prompt_tokens"] == 1000
    assert summary["providers"]["groq"]["completion_tokens"] == 500
