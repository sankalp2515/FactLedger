"""Deterministic discovery ordering. These signals never establish evidence or truth."""

import re
import unicodedata
from collections import Counter
from hashlib import sha256
from urllib.parse import unquote, unquote_plus, urlsplit, urlunsplit

STOP_WORDS = {"the", "a", "an", "of", "and", "in", "for", "to", "is", "was", "by"}
STAGE_CUES = {
    "ANNOUNCED": {"announced", "announcement", "proposal", "withdrawn"},
    "APPROVED": {"approved", "approval", "sanction", "sanctioned", "rejected", "cancelled"},
    "PROCURED": {"procured", "procurement", "tender", "contract", "cancelled"},
    "UNDER_CONSTRUCTION": {"construction", "progress", "stalled", "incomplete"},
    "PHYSICALLY_COMPLETED": {"completed", "completion", "incomplete", "unfinished"},
    "INAUGURATED": {"inaugurated", "inauguration", "ceremony", "postponed", "cancelled"},
    "OPERATIONAL": {"operational", "operating", "opened", "closed", "nonfunctional"},
}
MEASURE_CUES = {
    "ALLOCATED": {"allocation", "allocated", "budget", "withheld"},
    "SANCTIONED": {"sanction", "sanctioned", "withdrawn", "cancelled"},
    "RELEASED": {"released", "release", "disbursement", "unreleased", "withheld"},
    "EXPENDED": {"spent", "expended", "expenditure", "unspent", "underutilisation"},
    "PAID_BENEFICIARIES": {"paid", "payment", "unpaid", "arrears"},
}


def _tokens(value):
    value = unicodedata.normalize("NFKC", str(value)).casefold()
    return set(re.findall(r"[^\W_]+", value, re.UNICODE)) - STOP_WORDS


def canonical_url(url):
    """Remove tracking/fragment duplicates only; preserve meaningful query parameters."""
    try:
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            return None
        if parts.port not in {None, 443}:
            return None
        host = parts.netloc.casefold()
        if parts.port == 443:
            host = host.rsplit(":", 1)[0]
        query = []
        for pair in parts.query.split("&"):
            key = unquote_plus(pair.split("=", 1)[0]).casefold()
            if not key.startswith("utm_") and key not in {"gclid", "fbclid"}:
                query.append(pair)
        return urlunsplit(("https", host, parts.path or "/", "&".join(query), ""))
    except (ValueError, TypeError):
        return None


def select_discovery(claims, batches, excluded_urls=()):
    """Interleave claim/purpose lanes and prefer diverse, scoped records within each lane.

    Keep raw checkpoint batches intact. No snippets are read or returned, and the original
    URL goes through the normal acquisition security checks rather than fetching a rewrite.
    """
    claim_map = {claim["id"]: claim for claim in claims}
    lanes = {}
    excluded = {canonical_url(url) for url in excluded_urls}
    order = 0
    for batch in batches:
        claim_id = batch.get("claim_id")
        claim = claim_map.get(claim_id, claims[0] if len(claims) == 1 else {})
        purpose = batch.get("purpose", "PRIMARY_RECORD")
        lane = lanes.setdefault((claim_id, purpose), [])
        subject = _tokens(claim.get("subject") or claim.get("text", ""))
        geography = _tokens(claim.get("geography", ""))
        for rank, row in enumerate(batch.get("results", [])[:20], 1):
            url = row.get("url", "")
            canonical = canonical_url(url)
            if canonical is None or canonical in excluded:
                continue
            host = urlsplit(canonical).hostname
            tokens = _tokens(str(row.get("title", ""))[:400] + " " + unquote(urlsplit(canonical).path))
            overlap = len(subject & tokens) / len(subject) if subject else 0
            geographic = bool(geography & tokens)
            cues = STAGE_CUES.get(claim.get("stage"), set())
            if claim.get("stage") in {None, "", "UNKNOWN"}:
                cues = MEASURE_CUES.get(claim.get("measure"), set())
            stage = bool(cues & tokens)
            official = overlap >= 0.5 and (
                host.endswith((".gov.in", ".nic.in", ".gov")) or host in {"gov.in", "nic.in"}
            )
            score = round(overlap * 12 + geographic * 3 + stage * 2 + official * 4, 3)
            selection = {
                "claim_id": claim_id,
                "purpose": purpose,
                "engine": batch.get("engine", "google"),
                "provider_rank": rank,
                "url_hash": sha256(url.encode()).hexdigest(),
                "domain": host,
                "subject_overlap": round(overlap, 3),
                "geography_cue": geographic,
                "stage_cue": stage,
                "original_host_signal": bool(official),
                "score": score,
            }
            lane.append({"url": url, "canonical": canonical, "selection": selection, "order": order})
            order += 1
    # Primary records get the first opportunity, opposing records the next; subsequent
    # cycles give every claim/purpose another opportunity before a lane can dominate.
    purpose_order = {"PRIMARY_RECORD": 0, "STATUS": 0, "OPPOSING": 1, "DEFINITION": 2}
    claim_order = {claim["id"]: index for index, claim in enumerate(claims)}
    keys = sorted(lanes, key=lambda key: (claim_order.get(key[0], 99), purpose_order.get(key[1], 3)))
    seen = set(excluded)
    domains = Counter()
    selected = []
    while any(lanes.values()):
        for key in keys:
            lane = [row for row in lanes[key] if row["canonical"] not in seen]
            lanes[key] = lane
            if not lane:
                continue
            row = max(
                lane,
                key=lambda r: (r["selection"]["score"] - 6 * domains[r["selection"]["domain"]], -r["order"]),
            )
            lane.remove(row)
            seen.add(row["canonical"])
            domains[row["selection"]["domain"]] += 1
            selected.append({"url": row["url"], "selection": row["selection"]})
    return selected
