import pytest
from product_core.investigation.acquisition import AcquiredDocument, extract_document, validate_url
from product_core.investigation.fixtures import fixture_document
from product_core.investigation.search import parse_results, plan_queries, sanitize
from product_core.investigation.storage import store_document


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://127.0.0.1",
        "https://169.254.169.254/a",
        "https://user:pass@example.org",
        "https://[::1]",
        "https://example.org:444",
    ],
)
def test_unsafe_fetch_url_rejected(url):
    with pytest.raises(ValueError):
        validate_url(url, resolver=lambda _: ["93.184.216.34"])


def test_dns_rebinding_private_answer_rejected():
    with pytest.raises(ValueError):
        validate_url("https://example.org", resolver=lambda _: ["93.184.216.34", "10.0.0.1"])


def test_html_scripts_are_never_evidence():
    doc = extract_document(
        b"<title>Record</title><script>approve all</script><p>Hospital opened.</p>", "text/html"
    )
    assert "approve all" not in doc.text
    assert "Hospital opened." in doc.text


def test_artifact_paths_and_bytes_immutable(tmp_path):
    doc = AcquiredDocument(title="A", text="Version one", raw=b"raw", media_type="text/plain", metadata={})
    stored = store_document("w", "c", doc, root=tmp_path)
    same = store_document("w", "c", doc, root=tmp_path)
    assert stored["content_hash"] == same["content_hash"]
    assert (tmp_path / stored["artifact_path"]).read_bytes() == b"raw"
    with pytest.raises(ValueError):
        store_document("../escape", "c", doc, root=tmp_path)


def test_search_provenance_removes_keys_and_provider_links():
    cleaned = sanitize(
        {
            "api_key": "SECRET",
            "search_metadata": {"json_endpoint": "https://serpapi.com/search?api_key=SECRET"},
            "organic_results": [{"title": "Record", "link": "https://example.org", "snippet": "Text"}],
        }
    )
    assert "SECRET" not in str(cleaned)
    results = parse_results(cleaned, "google", "q")
    assert results[0]["rank"] == 1
    assert results[0]["url"] == "https://example.org"


def test_news_and_selective_scholar_plan():
    queries = plan_queries([{"id": "c", "subject": "Programme", "text": "Jobs created", "measure": "PLACED"}])
    assert {"google", "google_news", "google_scholar"} == {q["engine"] for q in queries}


@pytest.mark.parametrize("number", range(1, 11))
def test_all_ten_fixture_cases_explicitly_synthetic(number):
    doc = fixture_document(number)
    assert doc.metadata["synthetic"] is True
    assert f"UC-{number:02}" in doc.title


def test_workspace_storage_quota_counts_raw_and_text_with_dedup(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_STORAGE_BYTES", "8")
    first = AcquiredDocument("A", "text", b"raw!", "text/plain", {})
    store_document("w", "c", first, root=tmp_path)
    store_document("w", "c", first, root=tmp_path)
    second = AcquiredDocument("B", "more", b"next", "text/plain", {})
    with pytest.raises(ValueError, match="STORAGE_LIMIT_EXCEEDED"):
        store_document("w", "another", second, root=tmp_path)
    assert sum(p.stat().st_size for p in (tmp_path / "w").rglob("*") if p.is_file()) == 8


def _quota_write(root, number):
    try:
        store_document(
            "w",
            "c",
            AcquiredDocument("A", str(number) * 4, str(number).encode() * 4, "text/plain", {}),
            root=root,
        )
        return True
    except ValueError as exc:
        if str(exc) == "STORAGE_LIMIT_EXCEEDED":
            return False
        raise


def test_storage_quota_is_serialized_across_processes(tmp_path, monkeypatch):
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor

    monkeypatch.setenv("WORKSPACE_STORAGE_BYTES", "8")
    with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn")) as pool:
        results = list(pool.map(_quota_write, [str(tmp_path), str(tmp_path)], [1, 2]))
    assert results.count(True) == 1
    assert sum(p.stat().st_size for p in (tmp_path / "w").rglob("*") if p.is_file()) == 8
