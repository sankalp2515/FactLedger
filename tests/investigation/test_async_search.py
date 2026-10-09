from datetime import timedelta

import httpx
import pytest
from product_core.investigation import executor
from product_core.investigation.search import SerpApiSearch, parse_results
from product_core.models import Run, now


def test_news_cluster_preserves_highlight_and_nested_publisher_records():
    payload = {
        "news_results": [
            {
                "title": "Coverage cluster",
                "highlight": {
                    "link": "https://example.org/primary",
                    "title": "Original",
                    "iso_date": "2026-10-08T08:00:00Z",
                    "source": {"name": "Publisher A"},
                },
                "stories": [
                    {
                        "link": "https://example.org/opposing",
                        "title": "Follow-up",
                        "source": {"name": "Publisher B"},
                    }
                ],
            }
        ]
    }
    rows = parse_results(payload, "google_news", "scoped question")
    assert [r["url"] for r in rows] == ["https://example.org/primary", "https://example.org/opposing"]
    assert rows[0]["publication_date"] == "2026-10-08T08:00:00Z"
    assert rows[1]["publisher"] == "Publisher B"
    assert all(r["discovery_only"] for r in rows)


def test_async_processing_archive_yields_provenance_without_secret():
    search_id = "a" * 24
    states = iter(["Processing", "Success"])
    acknowledgments = []

    def respond(request):
        if request.url.path == "/search.json":
            return httpx.Response(200, json={"search_metadata": {"id": search_id, "status": "Processing"}})
        status = next(states)
        return httpx.Response(
            200,
            json={
                "search_metadata": {"id": search_id, "status": status},
                "organic_results": [{"title": "Public record", "link": "https://example.org/record"}],
            },
        )

    search = SerpApiSearch("test-secret", transport=httpx.MockTransport(respond), poll_interval=0)
    batch = search.search("Hospital A", on_submitted=acknowledgments.append)
    assert batch["provider_search_id"] == search_id
    assert batch["results"][0]["url"] == "https://example.org/record"
    assert acknowledgments == [search_id]
    assert "test-secret" not in str(batch)


def test_existing_search_id_fetches_archive_without_new_submission():
    def respond(request):
        if request.url.path == "/search.json":
            pytest.fail("charged submission replayed")
        return httpx.Response(
            200, json={"search_metadata": {"id": "b" * 24, "status": "Success"}, "organic_results": []}
        )

    search = SerpApiSearch("test-secret", transport=httpx.MockTransport(respond), poll_interval=0)
    batch = search.search("Hospital A", provider_search_id="b" * 24)
    assert batch["provider_search_id"] == "b" * 24


def test_successful_news_search_with_no_results_is_completed_empty_discovery():
    def respond(request):
        return httpx.Response(
            200,
            json={
                "search_metadata": {"id": "b" * 24, "status": "Success"},
                "error": "Google News hasn't returned any results for this query.",
            },
        )

    search = SerpApiSearch("test-secret", transport=httpx.MockTransport(respond), poll_interval=0)
    batch = search.search("scoped opposing question", engine="google_news", provider_search_id="b" * 24)
    assert batch["results"] == []
    assert batch["provider_search_id"] == "b" * 24


def test_other_success_error_is_not_misclassified_as_empty_discovery():
    def respond(request):
        return httpx.Response(
            200,
            json={
                "search_metadata": {"id": "b" * 24, "status": "Success"},
                "error": "Account limit exceeded",
            },
        )

    search = SerpApiSearch("test-secret", transport=httpx.MockTransport(respond), poll_interval=0)
    with pytest.raises(ValueError, match="SEARCH_PROVIDER_REJECTED_REQUEST"):
        search.search("question", engine="google_news", provider_search_id="b" * 24)


def test_worker_crash_after_ack_recovers_archive_without_new_charge(database, monkeypatch):
    search_id = "c" * 24
    crashed = False
    submitted = False

    def respond(request):
        nonlocal crashed, submitted
        if request.url.path == "/search.json":
            if submitted:
                pytest.fail("provider submission charged twice")
            submitted = True
            return httpx.Response(200, json={"search_metadata": {"id": search_id, "status": "Processing"}})
        if not crashed:
            crashed = True
            raise SystemExit("simulated process death after durable ACK")
        return httpx.Response(
            200, json={"search_metadata": {"id": search_id, "status": "Success"}, "organic_results": []}
        )

    adapter = SerpApiSearch("test-only", transport=httpx.MockTransport(respond), poll_interval=0)
    monkeypatch.setattr(executor, "SerpApiSearch", lambda _: adapter)
    monkeypatch.setenv("SERPAPI_API_KEY", "test-only")
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    with database.begin() as s:
        run = s.get(Run, "run")
        run.mode = "live"
        run.plan = dict(
            run.plan,
            queries=[{"query": "Hospital A delay problems", "engine": "google", "purpose": "OPPOSING"}],
        )
        run.budget = dict(run.budget, rounds=1)
    with pytest.raises(SystemExit):
        executor.execute_run("run")
    with database.begin() as s:
        run = s.get(Run, "run")
        assert any(a.get("provider_search_id") == search_id for a in run.checkpoint["actions"].values())
        run.lease_expires_at = now() - timedelta(seconds=1)
    executor.execute_run("run")
    with database() as s:
        run = s.get(Run, "run")
        assert run.state == "COMPLETED"
        assert run.usage["searches"] == 1
