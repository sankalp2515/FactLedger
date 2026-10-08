"""SerpApi discovery with allowlisted provenance; snippets are never evidence."""

import re
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx

ENGINES = {"google", "google_news", "google_scholar"}
FORBIDDEN = {
    "api_key",
    "authorization",
    "access_token",
    "token",
    "json_endpoint",
    "raw_html_file",
    "prettify_html_file",
    "google_url",
    "search_parameters",
}


def sanitize(value):
    if isinstance(value, dict):
        return {
            k: sanitize(v)
            for k, v in value.items()
            if k.lower() not in FORBIDDEN and "secret" not in k.lower()
        }
    if isinstance(value, list):
        return [sanitize(v) for v in value[:100]]
    if isinstance(value, str):
        if "api_key=" in value.lower() or "serpapi.com/search" in value.lower():
            return "[provider locator redacted]"
        return value[:4000]
    return value


def parse_results(payload: dict, engine: str, query: str) -> list[dict]:
    rows = payload.get("news_results" if engine == "google_news" else "organic_results", [])
    results = []
    for index, row in enumerate(rows[:20]):
        url = row.get("link", "")
        try:
            parts = urlsplit(url)
        except ValueError:
            continue
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            continue
        source = row.get("source")
        source = source.get("name") if isinstance(source, dict) else source
        results.append(
            {
                "url": url,
                "title": str(row.get("title", ""))[:400],
                "snippet": str(row.get("snippet", ""))[:2000],
                "rank": index + 1,
                "engine": engine,
                "query": query,
                "publication_date": row.get("date"),
                "date_provenance": "provider_unverified",
                "publisher": source,
                "discovery_only": True,
            }
        )
    return results


def plan_queries(claims: list[dict], gaps: list[dict] | None = None, round_number=1) -> list[dict]:
    result = []
    for claim in claims[:3]:
        subject = str(claim.get("subject") or claim.get("text", ""))[:300]
        context = " ".join(str(claim[k]) for k in ("geography", "period") if claim.get(k))
        target = str(claim.get("stage") or claim.get("measure") or "status").lower().replace("_", " ")
        if round_number == 1:
            templates = [
                ("google", "PRIMARY_RECORD", f"{subject} {context} {target} official report"),
                ("google_news", "OPPOSING", f"{subject} {context} {target} delay problems"),
            ]
            if claim.get("measure") in {
                "PLACED",
                "EMPLOYED",
                "SERVICE_FREQUENCY",
                "PAID_BENEFICIARIES",
            } or claim.get("methodology_required"):
                templates.append(
                    ("google_scholar", "DEFINITION", f"{subject} {target} measurement methodology")
                )
        else:
            missing = [g["type"].lower() for g in (gaps or []) if g.get("claim_id") == claim["id"]]
            keyword = " ".join(sorted(set(missing))) or "original primary record"
            templates = [
                ("google", "STATUS", f"{subject} {context} {target} {keyword} record round {round_number}")
            ]
        for engine, purpose, query in templates:
            result.append(
                {
                    "claim_id": claim["id"],
                    "engine": engine,
                    "purpose": purpose,
                    "query": " ".join(query.split()),
                    "expected_evidence": "Dated original record with exact confirmed scope.",
                    "rationale": "Target missing stage, scope, definition or opposing evidence.",
                }
            )
    return result


class SerpApiSearch:
    def __init__(self, api_key: str, transport=None, poll_interval=1):
        self.api_key = api_key
        self.transport = transport
        self.poll_interval = poll_interval

    def search(
        self, query: str, engine="google", on_submitted=None, provider_search_id=None, timeout=55
    ) -> dict:
        if engine not in ENGINES:
            raise ValueError("SEARCH_ENGINE_NOT_ALLOWED")
        if not self.api_key:
            raise ValueError("SEARCH_NOT_CONFIGURED")
        params = {
            "engine": engine,
            "q": query[:1000],
            "api_key": self.api_key,
            "hl": "en",
            "gl": "in",
            "async_": "true",
        }
        params["async"] = params.pop("async_")
        deadline = time.monotonic() + min(float(timeout), 55)
        with httpx.Client(timeout=20, transport=self.transport, follow_redirects=False) as client:
            try:

                def request(url, parameters):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ValueError("SEARCH_PROVIDER_TIMEOUT")
                    response = client.get(url, params=parameters, timeout=min(20, remaining))
                    if response.status_code != 200:
                        raise ValueError("SEARCH_PROVIDER_HTTP_" + str(response.status_code))
                    if len(response.content) > 2_000_000:
                        raise ValueError("SEARCH_RESPONSE_LIMIT")
                    payload = response.json()
                    if payload.get("error"):
                        raise ValueError("SEARCH_PROVIDER_REJECTED_REQUEST")
                    return payload

                payload = None
                if provider_search_id is None:
                    payload = request("https://serpapi.com/search.json", params)
                    provider_search_id = payload.get("search_metadata", {}).get("id")
                    if not isinstance(provider_search_id, str) or not re.fullmatch(
                        "[a-fA-F0-9]{24}", provider_search_id
                    ):
                        raise ValueError("SEARCH_PROVIDER_INVALID_ID")
                    if on_submitted:
                        on_submitted(provider_search_id)
                elif not re.fullmatch("[a-fA-F0-9]{24}", provider_search_id):
                    raise ValueError("SEARCH_PROVIDER_INVALID_ID")
                for _ in range(60):
                    if payload and payload.get("search_metadata", {}).get("status") == "Success":
                        break
                    if payload and payload.get("search_metadata", {}).get("status") not in {
                        "Queued",
                        "Processing",
                        None,
                    }:
                        raise ValueError("SEARCH_PROVIDER_FAILED")
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ValueError("SEARCH_PROVIDER_TIMEOUT")
                    if self.poll_interval:
                        time.sleep(min(self.poll_interval, remaining))
                    payload = request(
                        f"https://serpapi.com/searches/{provider_search_id}.json", {"api_key": self.api_key}
                    )
                else:
                    raise ValueError("SEARCH_PROVIDER_TIMEOUT")
            except httpx.HTTPError:
                raise ValueError("SEARCH_PROVIDER_NETWORK_ERROR") from None
        if payload.get("error"):
            raise ValueError("SEARCH_PROVIDER_REJECTED_REQUEST")
        safe = sanitize(payload)
        return {
            "engine": engine,
            "query": query,
            "provider_search_id": provider_search_id,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "params": {"hl": "en", "gl": "in", "async_search": True},
            "results": parse_results(safe, engine, query),
            "provenance": safe,
        }
