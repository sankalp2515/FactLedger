"""Literal citations and deterministic scope/quantity guards.

Semantic mappings are proposals; valid quotation is never treated as proof by itself.
"""

import calendar
import re
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

RELATIONS = {"SUPPORTS", "CONTRADICTS", "CONTEXT", "INCOMPARABLE", "INSUFFICIENT"}
FUNDING = {"ALLOCATED", "SANCTIONED", "RELEASED", "EXPENDED"}
METRICS = {
    "CAPACITY",
    "LENGTH",
    "CONNECTIONS",
    "SERVICE_FREQUENCY",
    "ENROLLMENT",
    "TRAINING_COMPLETIONS",
    "PLACED",
    "OCCUPIED",
    "HANDOVER",
    "REGISTERED",
    "APPROVED_BENEFICIARIES",
    "PAID_BENEFICIARIES",
    "GENERATION",
    "EMPLOYED",
    "ATTENDANCE",
    "STAFFING",
    "COMPLETION_PERCENTAGE",
}
MULTIPLIERS = {
    "lakh": Decimal(100000),
    "crore": Decimal(10000000),
    "million": Decimal(1000000),
    "billion": Decimal(1000000000),
}
SCOPE = ("subject", "geography", "period", "denominator", "attribution")
STAGE_CUES = {
    "OPERATIONAL": (
        "operational",
        "operating",
        "open to traffic",
        "serving patients",
        "commissioned",
        "in operation",
    ),
    "INAUGURATED": ("inaugurat",),
    "APPROVED": ("approved", "sanctioned"),
    "PHYSICALLY_COMPLETED": ("completed", "completion"),
    "UNDER_CONSTRUCTION": ("under construction", "construction ongoing"),
    "ANNOUNCED": ("announced", "announcement"),
    "PROCURED": ("procured", "procurement"),
}


def period_end(value):
    """Explicit ISO calendar or Indian fiscal period bounds; never infer 'now'."""
    if not isinstance(value, str):
        return None
    value = value.strip().replace("–", "-")
    try:
        fiscal = re.fullmatch(r"FY\s*(\d{4})\s*-\s*(\d{2}|\d{4})", value, re.IGNORECASE)
        if fiscal:
            first = int(fiscal[1])
            last = int(fiscal[2])
            if last < 100:
                last = (first // 100) * 100 + last
            return date(last, 3, 31) if last == first + 1 else None
        if re.fullmatch(r"\d{4}", value):
            return date(int(value), 12, 31)
        if re.fullmatch(r"\d{4}-\d{2}", value):
            year, month = map(int, value.split("-"))
            return date(year, month, calendar.monthrange(year, month)[1])
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value)
    except ValueError:
        return None
    return None


def compare_quantities(left: dict, right: dict) -> dict:
    reasons = []
    for field in ("currency", "measure", "period", "geography", "denominator", "attribution"):
        if left.get(field) is not None and left.get(field) != right.get(field):
            reasons.append(field)
    lu = str(left.get("unit", "")).lower()
    ru = str(right.get("unit", "")).lower()
    monetary = bool(left.get("currency") and right.get("currency"))
    if lu != ru and not (monetary and lu in MULTIPLIERS and ru in MULTIPLIERS):
        reasons.append("unit")
    try:
        lv = Decimal(str(left["value"]))
        rv = Decimal(str(right["value"]))
        if not lv.is_finite() or not rv.is_finite():
            raise InvalidOperation
    except (KeyError, InvalidOperation, ValueError):
        return {"comparable": False, "reasons": ["invalid_value"]}
    lv *= MULTIPLIERS.get(lu, Decimal(1)) if monetary else Decimal(1)
    rv *= MULTIPLIERS.get(ru, Decimal(1)) if monetary else Decimal(1)
    return {
        "comparable": not reasons,
        "equal": lv == rv if not reasons else None,
        "left_normalized": str(lv),
        "right_normalized": str(rv),
        "reasons": reasons,
        "operation": "unit_normalization",
        "operands": [left, right],
    }


def validate_candidate(claim: dict, document: dict, candidate: dict) -> dict | None:
    text = document.get("text", "")
    quote = candidate.get("quote", "")
    if not isinstance(quote, str) or not quote or len(quote) > 4000:
        return None
    supplied = candidate.get("anchor") or {}
    start = supplied.get("start", text.find(quote))
    end = supplied.get("end", start + len(quote))
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or text[start:end] != quote:
        return None
    relation = candidate.get("relation", "CONTEXT")
    if relation not in RELATIONS:
        relation = "INSUFFICIENT"
    observed = {
        key: candidate.get(key)
        for key in (*SCOPE, "stage", "measure", "value", "unit", "currency", "event_date", "methodology")
        if candidate.get(key) is not None
    }
    mismatches = [key for key in SCOPE if claim.get(key) is not None and observed.get(key) != claim.get(key)]
    gaps = []
    if mismatches:
        relation = "INCOMPARABLE"
        gaps = mismatches
    elif claim.get("stage") and observed.get("stage") != claim["stage"]:
        relation = "CONTEXT"
        gaps = ["stage"]
    elif claim.get("measure") and observed.get("measure") != claim["measure"]:
        relation = "CONTEXT"
        gaps = ["measure"]
    quantity = None
    if claim.get("value") is not None and observed.get("value") is not None:
        quantity = compare_quantities(claim, observed)
        if not quantity["comparable"]:
            relation = "INCOMPARABLE"
            gaps += quantity["reasons"]
        elif relation == "SUPPORTS" and not quantity["equal"]:
            relation = "CONTRADICTS"
    elif claim.get("value") is not None and relation in {"SUPPORTS", "CONTRADICTS"}:
        relation = "INSUFFICIENT"
        gaps.append("quantity")
    if relation in {"SUPPORTS", "CONTRADICTS"}:
        if (
            observed.get("measure")
            and observed["measure"] not in FUNDING | METRICS
            and not claim.get("definition_confirmed")
        ):
            relation = "INSUFFICIENT"
            gaps.append("measure_definition")
        cues = STAGE_CUES.get(observed.get("stage"))
        if cues and not any(cue in quote.lower() for cue in cues):
            relation = "CONTEXT"
            gaps.append("stage_not_literal")
        if observed.get("value") is not None:
            try:
                number = Decimal(str(observed["value"]))
                quoted = [
                    Decimal(n.replace(",", ""))
                    for n in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w.])", quote)
                ]
                if number not in quoted:
                    relation = "INSUFFICIENT"
                    gaps.append("quantity_not_literal")
            except InvalidOperation:
                relation = "INSUFFICIENT"
                gaps.append("invalid_quantity")
    if relation in {"SUPPORTS", "CONTRADICTS"}:
        reference_end = period_end(claim.get("period"))
        if claim.get("period") and reference_end is None:
            relation = "INSUFFICIENT"
            gaps.append("unknown_reference_period")
        event = observed.get("event_date")
        if event:
            try:
                event_date = date.fromisoformat(str(event))
            except ValueError:
                relation = "INSUFFICIENT"
                gaps.append("unknown_event_date")
            else:
                if reference_end and event_date > reference_end:
                    relation = "INCOMPARABLE"
                    gaps.append("event_after_reference_period")
        if relation in {"SUPPORTS", "CONTRADICTS"} and observed.get("stage") == "OPERATIONAL":
            negation = r"\b(?:not(?:\s+yet)?|never|no longer)\s+(?:fully\s+)?(?:operational|operating|commissioned|open to traffic|in operation)\b"
            negated = bool(re.search(negation, quote, re.IGNORECASE))
            claim_negated = bool(re.search(negation, str(claim.get("text", "")), re.IGNORECASE))
            if negated:
                relation = "SUPPORTS" if claim_negated else "CONTRADICTS"
            elif claim_negated:
                relation = "CONTRADICTS"
    page = None
    for p in document.get("metadata", {}).get("pages", []):
        if p["start"] <= start and end <= p["end"]:
            page = p["page"]
            break
    if document.get("metadata", {}).get("pages") and page is None:
        return None
    if supplied.get("page") and supplied["page"] != page:
        return None
    anchor = {"start": start, "end": end}
    if page is not None:
        anchor["page"] = page
    return {
        "id": str(uuid.uuid4()),
        "claim_id": claim["id"],
        "source_id": document["id"],
        "relation": relation,
        "quote": quote,
        "anchor": anchor,
        "comparison": {
            "claim": {k: claim.get(k) for k in (*SCOPE, "stage", "measure", "value", "unit", "currency")},
            "observed": observed,
            "quantity": quantity,
            "gaps": gaps,
        },
        "rationale": str(
            candidate.get(
                "rationale", "Scope and literal quotation checked; semantic interpretation requires review."
            )
        )[:1000],
        "metadata": {
            "validation_version": "1",
            "semantic_proposal": True,
            "extraction_hash": document.get("extraction_hash"),
        },
    }


def analyze(claim: dict, document: dict) -> list[dict]:
    return [
        v
        for c in document.get("facts", document.get("candidates", []))
        if (v := validate_candidate(claim, document, c))
    ]


def finding(evidence: list[dict], gaps: list[dict]) -> dict:
    support = [e["id"] for e in evidence if e["relation"] == "SUPPORTS"]
    opposing = [e["id"] for e in evidence if e["relation"] == "CONTRADICTS"]
    status = (
        "MIXED_EVIDENCE"
        if support and opposing
        else "SUPPORTED_BY_COLLECTED_EVIDENCE"
        if support
        else "CONTRADICTED_BY_COLLECTED_EVIDENCE"
        if opposing
        else "INSUFFICIENT_EVIDENCE"
    )
    checked = []
    for gap in gaps:
        gap = dict(gap)
        field = gap.get("type", "").lower()
        field = {
            "stage_not_literal": "stage",
            "quantity_not_literal": "value",
            "invalid_quantity": "value",
            "quantity": "value",
        }.get(field, field)
        decisive = [
            e
            for e in evidence
            if e["relation"] in {"SUPPORTS", "CONTRADICTS"} and e.get("claim_id") == gap.get("claim_id")
        ]
        for e in decisive:
            comparison = e.get("comparison", {})
            scoped = comparison.get("claim", {})
            observed = comparison.get("observed", {})
            if (
                field == "missing_comparable_evidence"
                or (field == "value" and (comparison.get("quantity") or {}).get("comparable"))
                or (scoped.get(field) is not None and scoped.get(field) == observed.get(field))
            ):
                gap.update(resolved=True, material=False, resolved_by=e["id"])
                break
        checked.append(gap)
    if any(g.get("material", True) and not g.get("resolved") for g in checked):
        status = "INSUFFICIENT_EVIDENCE"
    return {
        "finding": status,
        "decisive_ids": support,
        "opposing_ids": opposing,
        "gaps": checked,
        "limitations": [
            "Collected records do not certify ground reality.",
            "Semantic mappings require researcher/editor review.",
        ],
    }


def ledger(evidence: list[dict]) -> dict:
    result = {"stages": [], "funding": [], "metrics": [], "derived": [], "gaps": []}
    for e in evidence:
        fact = e["comparison"].get("observed", {})
        base = {
            "id": str(uuid.uuid4()),
            "claim_id": e["claim_id"],
            "source_id": e["source_id"],
            "quote": e["quote"],
            "evidence_ids": [e["id"]],
            "event_date": fact.get("event_date"),
            "period": fact.get("period"),
        }
        if fact.get("stage"):
            result["stages"].append(dict(base, stage=fact["stage"]))
        if fact.get("measure"):
            category = "funding" if fact["measure"] in FUNDING else "metrics"
            result[category].append(
                dict(
                    base,
                    kind=fact["measure"],
                    value=fact.get("value"),
                    unit=fact.get("unit"),
                    currency=fact.get("currency"),
                    denominator=fact.get("denominator"),
                    methodology=fact.get("methodology"),
                    attribution=fact.get("attribution"),
                )
            )
        if e["comparison"].get("quantity"):
            result["derived"].append(
                dict(id=str(uuid.uuid4()), evidence_ids=[e["id"]], **e["comparison"]["quantity"])
            )
        for key in e["comparison"].get("gaps", []):
            result["gaps"].append(
                {
                    "claim_id": e["claim_id"],
                    "type": key.upper(),
                    "reason": f"Observation does not establish matching {key}.",
                    "next_evidence_needed": f"Dated source with confirmed {key}.",
                    "material": True,
                }
            )
    return result
