"""SerpApi discovery with allowlisted provenance; snippets are never evidence."""

import re
import time
from datetime import UTC, date, datetime
from urllib.parse import urlsplit

import httpx

ENGINES = {"google", "google_news", "google_scholar"}
EMPTY_MESSAGES = {
    "google": "Google hasn't returned any results for this query.",
    "google_news": "Google News hasn't returned any results for this query.",
    "google_scholar": "Google Scholar hasn't returned any results for this query.",
}
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
    if engine == "google_news":
        # News groups may contain publisher links only inside highlight/stories.
        flattened = []
        for group in rows[:20]:
            if not isinstance(group, dict):
                continue
            flattened.append(group)
            if isinstance(group.get("highlight"), dict):
                flattened.append(group["highlight"])
            flattened.extend(s for s in group.get("stories", [])[:20] if isinstance(s, dict))
        rows = flattened
    results = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = row.get("link", "")
        try:
            parts = urlsplit(url)
        except ValueError:
            continue
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            continue
        if url in seen:
            continue
        seen.add(url)
        source = row.get("source")
        source = source.get("name") if isinstance(source, dict) else source
        results.append(
            {
                "url": url,
                "title": str(row.get("title", ""))[:400],
                "snippet": str(row.get("snippet", ""))[:2000],
                "rank": len(results) + 1,
                "engine": engine,
                "query": query,
                "publication_date": row.get("iso_date") or row.get("date"),
                "date_provenance": "provider_unverified",
                "publisher": source,
                "discovery_only": True,
            }
        )
        if len(results) == 20:
            break
    return results


def plan_queries(claims: list[dict], gaps: list[dict] | None = None, round_number=1) -> list[dict]:
    result = []
    for claim in claims[:3]:
        subject = str(claim.get("subject") or claim.get("text", ""))[:300]
        period = str(claim.get("period", ""))
        if re.fullmatch(r"\d{4}-\d{2}", period):
            try:
                period = date.fromisoformat(period + "-01").strftime("%B %Y")
            except ValueError:
                pass
        context = " ".join(str(v) for v in (claim.get("geography"), period) if v)
        stage = claim.get("stage")
        target = str(stage if stage and stage != "UNKNOWN" else claim.get("measure") or "status")
        target = target.lower().replace("_", " ")
        # The confirmed assertion can name the responsible actor or decision body.
        # Retain that context without guessing an actor from the subject or source host.
        assertion = str(claim.get("text") or "")[:500].strip()
        primary_subject = assertion or subject
        if assertion and subject.casefold() not in assertion.casefold():
            primary_subject = f"{subject} {assertion}"
        institution_scope = str(claim.get("geography", "")).strip().casefold() == "india" and bool(
            re.search(
                r"\b(?:(?:union|state|central)\s+cabinet|ministry\s+of|parliament|government\s+of)\b",
                assertion,
                re.IGNORECASE,
            )
        )
        if round_number == 1:
            primary_query = _concise_query(f"{primary_subject} {context} {target} official report")
            if institution_scope:
                primary_query += " (site:gov.in OR site:nic.in)"
            templates = [
                ("google", "PRIMARY_RECORD", primary_query),
                ("google_news", "OPPOSING", f"{subject} {context} {target} {_opposing_terms(claim)}"),
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
            gap_terms = {
                "opposing_coverage": _opposing_terms(claim),
                "missing_comparable_evidence": "dated original primary record",
                "stage_mismatch": "status dated record",
                "denominator_missing": "total eligible population denominator",
                "definition_missing": "definition measurement methodology",
            }
            keyword = " ".join(sorted({gap_terms.get(g, g.replace("_", " ")) for g in missing}))
            keyword = keyword or "original primary record"
            templates = [
                ("google", "STATUS", _concise_query(f"{primary_subject} {context} {target} {keyword}"))
            ]
        for engine, purpose, query in templates:
            result.append(
                {
                    "claim_id": claim["id"],
                    "engine": engine,
                    "purpose": purpose,
                    "query": " ".join(query.split()),
                    "expected_evidence": "Dated original record with exact confirmed scope.",
                    "rationale": (
                        "Discover original records for a named Indian public institution; host restriction is not evidence of truth."
                        if purpose == "PRIMARY_RECORD" and institution_scope
                        else "Target missing stage, scope, definition or opposing evidence."
                    ),
                }
            )
    return result


def _concise_query(query):
    """Keep actor/topic/numeric tokens once, omitting sentence glue from discovery queries."""
    seen = set()
    result = []
    for token in re.findall(r"\d+(?:[.,]\d+)*|[^\W_]+", query, re.UNICODE):
        key = token.casefold()
        if key not in seen and key not in {"the", "a", "an", "of", "for", "in", "during", "and", "to"}:
            result.append(token)
            seen.add(key)
    return " ".join(result)


def _opposing_terms(claim):
    return {
        "ANNOUNCED": "withdrawn cancelled announcement disputed",
        "APPROVED": "rejected cancelled sanction withdrawn",
        "PROCURED": "tender cancelled procurement disputed contract withdrawn",
        "UNDER_CONSTRUCTION": "stalled construction incomplete progress",
        "PHYSICALLY_COMPLETED": "incomplete unfinished completion disputed",
        "INAUGURATED": "inauguration cancelled postponed disputed",
        "OPERATIONAL": "closed nonfunctional not operating",
    }.get(
        claim.get("stage"),
        {
            "ALLOCATED": "allocation withheld reduced funding shortfall",
            "SANCTIONED": "sanction cancelled withdrawn funding shortfall",
            "RELEASED": "funds withheld unreleased disbursement shortfall",
            "EXPENDED": "unspent expenditure disputed underutilisation",
            "PLACED": "unplaced placement disputed verification",
            "EMPLOYED": "unemployment employment disputed verification",
            "PAID_BENEFICIARIES": "unpaid excluded beneficiaries payment shortfall",
            "SERVICE_FREQUENCY": "service cancelled reduced frequency",
        }.get(claim.get("measure"), "disputed contrary record verification"),
    )


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

        def rejected(payload):
            # Successful empty discovery is not an unknown paid outcome or evidence of absence.
            empty = (
                payload.get("search_metadata", {}).get("status") == "Success"
                and payload.get("error") == EMPTY_MESSAGES[engine]
                and not parse_results(payload, engine, query)
            )
            return bool(payload.get("error") and not empty)

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
                    if rejected(payload):
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
        if rejected(payload):
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
