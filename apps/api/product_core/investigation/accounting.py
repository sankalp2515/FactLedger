"""Configured-rate estimates, never provider invoice or charge reconciliation."""

from decimal import Decimal


def model_cost(metadata, pricing):
    if not all(
        type(metadata.get(k)) is int and metadata[k] >= 0 for k in ("prompt_tokens", "completion_tokens")
    ):
        return None
    return float(
        (
            Decimal(metadata["prompt_tokens"]) * Decimal(str(pricing["llm_input_usd_per_million"]))
            + Decimal(metadata["completion_tokens"]) * Decimal(str(pricing["llm_output_usd_per_million"]))
        )
        / Decimal(1_000_000)
    )


def cost_summary(run):
    providers = {}
    uncertain = Decimal(0)
    for key, action in (run.checkpoint or {}).get("actions", {}).items():
        amount = action.get("amount", {})
        metadata = action.get("outcome", {}).get("metadata", {})
        if key.startswith("search:") and "searches" in amount:
            provider = "serpapi"
        elif key.startswith("extract:") and "tokens" in amount:
            provider = metadata.get("provider") or (run.plan or {}).get("pricing", {}).get(
                "llm_provider", "llm"
            )
        else:
            continue
        row = providers.setdefault(
            provider,
            {"attempts": 0, "usd": 0, "prompt_tokens": 0, "completion_tokens": 0, "reported_usage_calls": 0},
        )
        row["attempts"] += 1
        usd = Decimal(str(action.get("reconciled", {}).get("usd", amount.get("usd", 0))))
        row["usd"] = float(Decimal(str(row["usd"])) + usd)
        if action.get("state") in {"RESERVED", "ACKNOWLEDGED", "OUTCOME_UNKNOWN"}:
            uncertain += usd
        if all(type(metadata.get(k)) is int for k in ("prompt_tokens", "completion_tokens")):
            row["reported_usage_calls"] += 1
            for name in ("prompt_tokens", "completion_tokens"):
                row[name] += metadata[name]
    return {
        "currency": "USD",
        "estimated": True,
        "total_usd": (run.usage or {}).get("usd", 0),
        "uncertain_reserved_usd": float(uncertain),
        "providers": providers,
        "pricing": (run.plan or {}).get("pricing", {}),
        "invoice_verified": False,
    }
