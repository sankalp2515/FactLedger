from datetime import timedelta

import pytest
from product_core.investigation import executor
from product_core.models import Case, Run, RunEvent, Source, now
from sqlalchemy import select


def test_fixture_execution_is_run_owned_and_preserves_case_head(database):
    executor.execute_run("run")
    with database() as s:
        run = s.get(Run, "run")
        assert run.state in {"COMPLETED", "PARTIAL"}
        assert run.results["sources"][0]["metadata"]["synthetic"] is True
        assert run.results["evidence"][0]["relation"] == "CONTEXT"
        assert s.get(Case, "case").revision == 1
        assert run.usage["rounds"] <= 3
        assert len(s.scalars(select(Source)).all()) >= 1
        events = s.scalars(select(RunEvent).order_by(RunEvent.seq)).all()
        assert [e.seq for e in events] == list(range(1, len(events) + 1))


def test_cancel_preserves_results_without_dispatch(database):
    with database.begin() as s:
        s.get(Run, "run").state = "CANCEL_REQUESTED"
    executor.execute_run("run")
    with database() as s:
        assert s.get(Run, "run").state == "CANCELLED"
        assert not s.scalars(select(Source)).all()


def test_pause_has_no_budget_reset(database):
    with database.begin() as s:
        run = s.get(Run, "run")
        run.state = "PAUSE_REQUESTED"
        run.usage = {"searches": 2, "tokens": 120}
    executor.execute_run("run")
    with database() as s:
        run = s.get(Run, "run")
        assert run.state == "PAUSED"
        assert run.usage["tokens"] == 120


def test_expired_worker_generation_cannot_commit(database):
    lease = executor.claim_run("run", "old")
    with database.begin() as s:
        s.get(Run, "run").lease_expires_at = now() - timedelta(seconds=1)
    newer = executor.claim_run("run", "new")
    assert newer.generation > lease.generation
    with pytest.raises(executor.Fenced):
        executor.update_run(lease, lambda s, r: setattr(r, "error", "stale"))
    with database() as s:
        assert s.get(Run, "run").error is None


def test_unknown_reservation_retained_and_not_replayed(database):
    lease = executor.claim_run("run", "old")
    executor.reserve(lease, "search:one", {"searches": 1, "usd": 0.01})
    with database.begin() as s:
        s.get(Run, "run").lease_expires_at = now() - timedelta(seconds=1)
    executor.execute_run("run")
    with database() as s:
        run = s.get(Run, "run")
        assert run.checkpoint["actions"]["search:one"]["state"] == "OUTCOME_UNKNOWN"
        assert run.usage["searches"] >= 1
        assert any(e.type == "OUTCOME_UNKNOWN" for e in s.scalars(select(RunEvent)).all())


def test_zero_document_budget_stops_without_fetch(database):
    with database.begin() as s:
        run = s.get(Run, "run")
        run.budget = dict(run.budget, documents=0)
    executor.execute_run("run")
    with database() as s:
        assert s.get(Run, "run").state == "PARTIAL"
        assert not s.scalars(select(Source)).all()


def test_reported_usage_reconciliation_is_idempotent(database):
    lease = executor.claim_run("run", "old")
    executor.reserve(lease, "model:test", {"tokens": 1000})
    executor.leases.settle(database, lease, "model:test", {"tokens": 100}, actual={"tokens": 100})
    executor.leases.settle(database, lease, "model:test", {"tokens": 100}, actual={"tokens": 100})
    with database() as s:
        assert s.get(Run, "run").usage["tokens"] == 100


def test_runtime_ceiling_applies_even_with_oversized_run_budget(database, monkeypatch):
    monkeypatch.setenv("MAX_RUN_SECONDS", "0")
    executor.execute_run("run")
    with database() as s:
        assert s.get(Run, "run").state == "PARTIAL"
        assert not s.scalars(select(Source)).all()


def test_api_initialized_empty_results_still_uses_pinned_scope(database):
    with database.begin() as s:
        run = s.get(Run, "run")
        run.results = {
            "claims": [],
            "projects": [],
            "evidence": [],
            "sources": [],
            "ledger": {"stages": [], "funding": [], "metrics": [], "derived": [], "gaps": []},
            "notes": [],
            "conclusion": "",
            "lineage": [],
        }
    executor.execute_run("run")
    with database() as s:
        run = s.get(Run, "run")
        assert len(run.results["claims"]) == 1
        assert len(run.results["evidence"]) == 1


def test_cancel_during_fetch_preserves_acquired_record(database, monkeypatch):
    from product_core.investigation.acquisition import AcquiredDocument

    class Search:
        def search(self, *args, **kwargs):
            return {"results": [{"url": "https://example.org/record"}]}

    monkeypatch.setenv("SERPAPI_API_KEY", "test-only")
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    monkeypatch.setattr(executor, "SerpApiSearch", lambda _: Search())

    def fetched(url):
        with database.begin() as s:
            s.get(Run, "run").state = "CANCEL_REQUESTED"
        return AcquiredDocument(
            "Public record",
            "Hospital A operational.",
            b"raw",
            "text/plain",
            {"extraction_version": "test-v1"},
        )

    monkeypatch.setattr(executor, "acquire", fetched)
    with database.begin() as s:
        run = s.get(Run, "run")
        run.mode = "live"
        run.plan = dict(run.plan, queries=[{"query": "Hospital A", "engine": "google"}])
    executor.execute_run("run")
    with database() as s:
        run = s.get(Run, "run")
        assert run.state == "CANCELLED"
        assert len(run.results["sources"]) == 1
        assert run.usage["documents"] == 1


def test_budget_reservations_are_serialized_across_workers(database):
    from concurrent.futures import ThreadPoolExecutor

    with database.begin() as s:
        run = s.get(Run, "run")
        run.budget = dict(run.budget, searches=1)
    lease = executor.claim_run("run", "owner")

    def attempt(key):
        try:
            executor.reserve(lease, key, {"searches": 1})
            return True
        except executor.BudgetExceeded:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["one", "two"]))
    assert results.count(True) == 1
    with database() as s:
        assert s.get(Run, "run").usage["searches"] == 1


@pytest.mark.parametrize("search_budget", [0, 2])
def test_manual_source_requires_opposing_discovery_when_budget_available(
    database, monkeypatch, search_budget
):
    from product_core.investigation.acquisition import AcquiredDocument
    from product_core.investigation.model import ModelResult
    from product_core.investigation.storage import store_document

    quote = "Hospital A operational with 200 beds in District A during 2026-09."
    doc = AcquiredDocument(
        "Uploaded record", quote, quote.encode(), "text/plain", {"extraction_version": "test-v1"}
    )
    stored = store_document("w", "case", doc)
    with database.begin() as s:
        s.add(
            Source(
                id="manual",
                workspace_id="w",
                case_id="case",
                url="upload://record",
                title=doc.title,
                status="AVAILABLE",
                metadata_json=stored.pop("metadata"),
                **stored,
            )
        )
        run = s.get(Run, "run")
        run.mode = "live"
        run.plan = dict(run.plan, sources=[{"id": "manual"}])
        run.budget = dict(run.budget, searches=search_budget, rounds=1)
        fact = dict(run.plan["claims"][0], quote=quote, relation="SUPPORTS")

    class Model:
        def extract(self, *args):
            return ModelResult(
                [fact],
                100,
                {
                    "provider": "groq",
                    "model": "test",
                    "prompt_hash": "abc",
                    "input_hash": "def",
                    "prompt_tokens": 80,
                    "completion_tokens": 20,
                },
            )

    class Search:
        def search(self, query, engine, **kwargs):
            return {"results": [], "engine": engine, "query": query}

    monkeypatch.setenv("SERPAPI_API_KEY", "test-only")
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    monkeypatch.setattr(executor, "StructuredModel", lambda *args: Model())
    monkeypatch.setattr(executor, "SerpApiSearch", lambda _: Search())
    monkeypatch.setattr(executor, "acquire", lambda _: pytest.fail("manual record must not refetch"))
    executor.execute_run("run")
    with database() as s:
        run = s.get(Run, "run")
        assert run.error == ("OPPOSING_COVERAGE_NOT_CHECKED" if search_budget == 0 else None)
        assert run.results["evidence"][0]["relation"] == "SUPPORTS"
        assert run.results["evidence"][0]["metadata"]["model"] == "test"
        assert run.usage.get("searches", 0) == search_budget
        assert run.state == ("PARTIAL" if search_budget == 0 else "COMPLETED")
        model_action = next(a for k, a in run.checkpoint["actions"].items() if k.startswith("extract:"))
        assert model_action["reconciled"]["usd"] == pytest.approx(0.000064)


def test_provider_timeouts_surface_partial_with_actionable_safe_error(database, monkeypatch):
    class Search:
        def search(self, *args, **kwargs):
            raise ValueError("SEARCH_PROVIDER_NETWORK_ERROR")

    monkeypatch.setenv("SERPAPI_API_KEY", "test-only")
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    monkeypatch.setattr(executor, "SerpApiSearch", lambda _: Search())
    with database.begin() as s:
        run = s.get(Run, "run")
        run.mode = "live"
        run.plan = dict(run.plan, queries=[{"query": "Hospital A", "engine": "google"}])
    executor.execute_run("run")
    with database() as s:
        run = s.get(Run, "run")
        assert run.state == "PARTIAL"
        assert run.error == "PROVIDER_ACTIONS_INCOMPLETE"
        assert any(
            a.get("outcome", {}).get("error") == "SEARCH_PROVIDER_NETWORK_ERROR"
            for a in run.checkpoint["actions"].values()
        )
        assert any(
            e.type == "PROVIDER_ERROR" and "network" in e.payload["advice"].lower()
            for e in s.scalars(select(RunEvent)).all()
        )


def test_invalid_credentials_are_failed_attempts_not_unknown_charges(database, monkeypatch):
    class Search:
        def search(self, *args, **kwargs):
            raise ValueError("SEARCH_PROVIDER_HTTP_401")

    monkeypatch.setenv("SERPAPI_API_KEY", "test-only")
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    monkeypatch.setattr(executor, "SerpApiSearch", lambda _: Search())
    with database.begin() as s:
        run = s.get(Run, "run")
        run.mode = "live"
        run.plan = dict(run.plan, queries=[{"query": "Hospital A", "engine": "google"}])
    executor.execute_run("run")
    with database() as s:
        run = s.get(Run, "run")
        errors = [a for a in run.checkpoint["actions"].values() if a.get("outcome", {}).get("error")]
        assert errors
        assert all(a["state"] == "FAILED" for a in errors)
        assert run.usage["searches"] >= 1
        assert run.usage["usd"] == 0


def test_live_document_budget_inspects_buried_primary_and_opposing(database, monkeypatch):
    from product_core.investigation.acquisition import AcquiredDocument
    from product_core.investigation.model import ModelResult

    official = "https://health.gov.in/hospital-a-operational"
    opposing = "https://journal.example/hospital-a-closed"
    fetched = []

    class Search:
        def search(self, query, engine, **kwargs):
            rows = (
                [{"url": opposing, "title": "Hospital A closed District A"}]
                if engine == "google_news"
                else [{"url": f"https://guides.example/{i}", "title": "Hospital A guide"} for i in range(14)]
                + [{"url": official, "title": "Hospital A operational District A"}]
            )
            return {"results": rows, "engine": engine, "query": query}

    class Model:
        def extract(self, *args):
            return ModelResult([], 100, {})

    def acquire(url):
        fetched.append(url)
        return AcquiredDocument("Record", "No comparable evidence.", b"record", "text/plain", {})

    monkeypatch.setenv("SERPAPI_API_KEY", "test-only")
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    monkeypatch.setattr(executor, "SerpApiSearch", lambda _: Search())
    monkeypatch.setattr(executor, "StructuredModel", lambda *args: Model())
    monkeypatch.setattr(executor, "acquire", acquire)
    with database.begin() as s:
        run = s.get(Run, "run")
        run.mode = "live"
        run.budget = dict(run.budget, documents=2, rounds=1)
    executor.execute_run("run")
    assert fetched == [official, opposing]
    with database() as s:
        run = s.get(Run, "run")
        assert run.usage["documents"] == 2
        assert run.usage["searches"] == 2
        assert run.results["evidence"] == []
        event = next(e for e in s.scalars(select(RunEvent)).all() if e.type == "DISCOVERY_SELECTION")
        assert event.payload["discovery_only"] is True
        assert event.payload["selected"][0]["original_host_signal"] is True
        assert "snippet" not in str(event.payload)
        batches = [a["outcome"] for k, a in run.checkpoint["actions"].items() if k.startswith("search:")]
        assert max(len(batch["results"]) for batch in batches) == 15


def test_tracking_alias_in_later_round_reuses_acquired_source(database, monkeypatch):
    from product_core.investigation.acquisition import AcquiredDocument
    from product_core.investigation.model import ModelResult

    fetched = []

    class Search:
        def search(self, query, engine, **kwargs):
            url = "https://records.example/hospital-a?id=1"
            if "original" in query:
                url += "&utm_source=search#section"
            return {"results": [] if engine == "google_news" else [{"url": url, "title": "Hospital A"}]}

    class Model:
        def extract(self, *args):
            return ModelResult([], 100, {})

    def acquire(url):
        fetched.append(url)
        return AcquiredDocument("Record", "No comparable evidence.", b"record", "text/plain", {})

    monkeypatch.setenv("SERPAPI_API_KEY", "test-only")
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    monkeypatch.setattr(executor, "SerpApiSearch", lambda _: Search())
    monkeypatch.setattr(executor, "StructuredModel", lambda *args: Model())
    monkeypatch.setattr(executor, "acquire", acquire)
    with database.begin() as s:
        run = s.get(Run, "run")
        run.mode = "live"
        run.budget = dict(run.budget, documents=3, rounds=2)
    executor.execute_run("run")
    assert fetched == ["https://records.example/hospital-a?id=1"]
    with database() as s:
        assert s.get(Run, "run").usage["documents"] == 1
        assert len(s.get(Run, "run").results["sources"]) == 1
