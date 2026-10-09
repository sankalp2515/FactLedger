"""Durable adaptive investigation. No case-head writes or editorial approvals."""

import json
import re
import threading
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from product_core.config import Settings
from product_core.db import SessionLocal, set_workspace
from product_core.domain.evidence import analyze, finding, ledger
from product_core.domain.lineage import source_families
from product_core.models import Evidence, Revision, Run, Source
from product_core.observability import logger

from . import leases
from .accounting import model_cost
from .acquisition import acquire
from .fixtures import fixture_for_claim
from .model import SYSTEM, StructuredModel, prepare_input
from .search import SerpApiSearch, plan_queries
from .selection import canonical_url, select_discovery
from .storage import store_document

Fenced = leases.Fenced
BudgetExceeded = leases.BudgetExceeded
StopRequested = leases.StopRequested


def _safe_provider_error(exc):
    message = str(exc) if isinstance(exc, ValueError) else ""
    return (
        message
        if re.fullmatch(r"(SEARCH|MODEL)_[A-Z0-9_]{1,80}", message)
        else "PROVIDER_NETWORK_OR_RESPONSE_ERROR"
    )


def claim_run(run_id, owner, workspace_id=None):
    return leases.claim_run(SessionLocal, run_id, owner, workspace_id=workspace_id)


def update_run(lease, operation):
    return leases.update_run(SessionLocal, lease, operation)


def reserve(lease, key, amount):
    return leases.reserve(SessionLocal, lease, key, amount)


def _snapshot(lease):
    with SessionLocal() as session:
        set_workspace(session, lease.workspace_id)
        run = session.get(Run, lease.run_id)
        if not run:
            raise Fenced("RUN_REMOVED")
        return deepcopy(
            {
                "id": run.id,
                "workspace_id": run.workspace_id,
                "case_id": run.case_id,
                "state": run.state,
                "plan": run.plan,
                "mode": run.mode,
                "budget": run.budget,
                "usage": run.usage,
                "results": run.results,
                "checkpoint": run.checkpoint,
                "base_revision": run.base_revision,
            }
        )


def _key(node, value):
    return node + ":" + sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:32]


def _finish(lease, state, reason=None):
    def operation(session, run):
        run.state = state
        run.lease_owner = None
        run.lease_expires_at = None
        checkpoint = deepcopy(run.checkpoint)
        checkpoint.pop("last_tick", None)
        run.checkpoint = checkpoint
        if reason:
            run.error = reason
        leases.event(session, run, state, {"reason": reason})

    update_run(lease, operation)


def _stop(lease):
    snapshot = _snapshot(lease)
    if snapshot["state"] == "CANCEL_REQUESTED":
        _finish(lease, "CANCELLED")
        return True
    if snapshot["state"] == "PAUSE_REQUESTED":
        _finish(lease, "PAUSED")
        return True
    return bool(snapshot["state"] in leases.TERMINAL or snapshot["state"] == "PAUSED")


def _action(lease, key, amount, call):
    existing = reserve(lease, key, amount)
    if existing is None:
        raise StopRequested("CANCELLED")
    if existing["state"] == "COMPLETED":
        return existing.get("outcome")
    if existing["state"] not in {"NEW", "ACKNOWLEDGED"}:
        return None
    try:
        result = call()
    except (Fenced, StopRequested):
        raise
    except Exception as exc:  # noqa: BLE001 -- Adapter failures become bounded safe durable outcomes.
        code = _safe_provider_error(exc)
        rejected = code.endswith(("_HTTP_400", "_HTTP_401", "_HTTP_403", "_HTTP_422"))
        advice = (
            "Check the server provider credentials and request configuration."
            if rejected
            else "Check provider availability, network access or rate limits; existing reservations and records are retained."
        )
        leases.settle(
            SessionLocal,
            lease,
            key,
            {"error": code},
            unknown=not rejected,
            failed=rejected,
            actual={name: 0 for name in ("tokens", "usd") if name in amount} if rejected else None,
        )
        update_run(
            lease,
            lambda session, run: leases.event(
                session, run, "PROVIDER_ERROR", {"action": key, "error": code, "advice": advice}
            ),
        )
        if rejected:
            raise ValueError(code) from None
        return None
    leases.settle(SessionLocal, lease, key, result)
    return result


def _recover(lease):
    def operation(session, run):
        checkpoint = deepcopy(run.checkpoint or {})
        for key, action in checkpoint.get("actions", {}).items():
            if action.get("provider_search_id") and action["state"] in {"RESERVED", "OUTCOME_UNKNOWN"}:
                action["state"] = "ACKNOWLEDGED"
                leases.event(
                    session,
                    run,
                    "SEARCH_ARCHIVE_RECOVERY",
                    {"action": key, "provider_search_id": action["provider_search_id"]},
                )
                continue
            if action["state"] == "RESERVED":
                action["state"] = "OUTCOME_UNKNOWN"
                leases.event(
                    session,
                    run,
                    "OUTCOME_UNKNOWN",
                    {"action": key, "reason": "Previous worker stopped after reservation; no blind replay."},
                )
        run.checkpoint = checkpoint

    update_run(lease, operation)


def _acknowledge_search(lease, key, provider_search_id):
    if not re.fullmatch("[a-fA-F0-9]{24}", provider_search_id):
        raise ValueError("SEARCH_PROVIDER_INVALID_ID")

    def operation(session, run):
        checkpoint = deepcopy(run.checkpoint)
        action = checkpoint["actions"][key]
        action.update(state="ACKNOWLEDGED", provider_search_id=provider_search_id)
        run.checkpoint = checkpoint
        leases.event(
            session, run, "SEARCH_ACKNOWLEDGED", {"action": key, "provider_search_id": provider_search_id}
        )

    update_run(lease, operation)


def _initialize(lease):
    def operation(session, run):
        claims = (run.plan or {}).get("claims")
        revision = session.scalar(
            select(Revision).where(
                Revision.case_id == run.case_id,
                Revision.workspace_id == run.workspace_id,
                Revision.number == run.base_revision,
            )
        )
        if claims is None:
            claims = (revision.payload or {}).get("claims", []) if revision else []
        if not claims or len(claims) > 3:
            raise ValueError("CONFIRMED_SCOPE_REQUIRED")
        results = deepcopy(run.results or {})
        if results.get("claims") and results["claims"] != claims:
            raise ValueError("PINNED_SCOPE_MISMATCH")
        results["claims"] = claims
        for field, default in {
            "claims": claims,
            "projects": (revision.payload or {}).get("projects", []) if revision else [],
            "evidence": [],
            "sources": [],
            "ledger": {"stages": [], "funding": [], "metrics": [], "derived": [], "gaps": []},
            "notes": [],
            "conclusion": "",
            "lineage": [],
        }.items():
            results.setdefault(field, default)
        results["mode"] = run.mode
        results["synthetic"] = run.mode == "fixture"
        existing_ids = {source["id"] for source in results["sources"]}
        for reference in (run.plan or {}).get("sources", []):
            source = session.get(Source, reference["id"])
            if not source or source.workspace_id != run.workspace_id or source.case_id != run.case_id:
                raise ValueError("MANUAL_SOURCE_SCOPE_MISMATCH")
            if source.id not in existing_ids:
                results["sources"].append(
                    {
                        "id": source.id,
                        "url": source.url,
                        "title": source.title,
                        "status": "ACQUIRED"
                        if source.status in {"AVAILABLE", "ACQUIRED"}
                        and not source.metadata_json.get("scanned")
                        else source.status,
                        "metadata": source.metadata_json,
                        "content_hash": source.content_hash,
                        "extraction_hash": source.extraction_hash,
                        "manual": True,
                    }
                )
        run.results = results

    update_run(lease, operation)


def _persist_source(lease, url, document, status="ACQUIRED", error=None):
    snapshot = _snapshot(lease)
    settings = Settings()
    stored = (
        store_document(snapshot["workspace_id"], snapshot["case_id"], document, root=settings.artifact_dir)
        if document
        else {
            "content_hash": "",
            "extraction_hash": "",
            "artifact_path": "",
            "text_path": "",
            "metadata": {"error": error},
        }
    )

    def operation(session, run):
        results = deepcopy(run.results)
        # URL is an invocation identity only within this run; new runs preserve new versions.
        existing = next((s for s in results["sources"] if s["url"] == url), None)
        if existing:
            return existing
        source_id = str(uuid4())
        metadata = stored["metadata"]
        session.add(
            Source(
                id=source_id,
                workspace_id=run.workspace_id,
                case_id=run.case_id,
                run_id=run.id,
                url=url,
                title=document.title if document else "Unavailable source",
                status=status,
                content_hash=stored["content_hash"],
                extraction_hash=stored["extraction_hash"],
                artifact_path=stored["artifact_path"],
                text_path=stored["text_path"],
                metadata_json=metadata,
            )
        )
        shape = {
            "id": source_id,
            "url": url,
            "title": document.title if document else "Unavailable source",
            "status": status,
            "metadata": metadata,
            "content_hash": stored["content_hash"],
            "extraction_hash": stored["extraction_hash"],
        }
        results["sources"].append(shape)
        run.results = results
        leases.event(
            session,
            run,
            "SOURCE_ACQUIRED" if document else "SOURCE_UNAVAILABLE",
            {"source_id": source_id, "status": status},
        )
        return shape

    return update_run(lease, operation)


def _persist_evidence(lease, claim, source, candidates, proposal_metadata=None):
    with SessionLocal() as session:
        set_workspace(session, lease.workspace_id)
        row = session.get(Source, source["id"])
        text_path = row.text_path
    text = (Path(Settings().artifact_dir) / text_path).read_text(encoding="utf-8")
    validated = analyze(
        claim,
        {
            "id": source["id"],
            "text": text,
            "metadata": source["metadata"],
            "extraction_hash": source["extraction_hash"],
            "candidates": candidates,
        },
    )
    for e in validated:
        e["metadata"].update(
            {
                key: value
                for key, value in (proposal_metadata or {}).items()
                if key
                in {
                    "provider",
                    "model",
                    "prompt_hash",
                    "input_hash",
                    "characters_selected",
                    "characters_total",
                    "usage_reported",
                }
            }
        )

    def operation(session, run):
        results = deepcopy(run.results)
        existing = {(e["claim_id"], e["source_id"], e["quote"]) for e in results["evidence"]}
        for e in validated:
            if (e["claim_id"], e["source_id"], e["quote"]) in existing:
                continue
            session.add(
                Evidence(
                    id=e["id"],
                    workspace_id=run.workspace_id,
                    case_id=run.case_id,
                    run_id=run.id,
                    claim_id=e["claim_id"],
                    source_id=e["source_id"],
                    relation=e["relation"],
                    quote=e["quote"],
                    anchor=e["anchor"],
                    comparison=e["comparison"],
                    rationale=e["rationale"],
                    metadata_json=e["metadata"],
                )
            )
            results["evidence"].append(e)
        results["ledger"] = ledger(results["evidence"])
        results["lineage"] = source_families(results["sources"])
        run.results = results
        leases.event(
            session,
            run,
            "EVIDENCE_VALIDATED",
            {
                "claim_id": claim["id"],
                "source_id": source["id"],
                "accepted": len(validated),
                "proposed": len(candidates),
            },
        )

    update_run(lease, operation)


def _compose(lease):
    def operation(session, run):
        results = deepcopy(run.results)
        gaps = results["ledger"]["gaps"]
        findings = []
        for claim in results["claims"]:
            relevant = [e for e in results["evidence"] if e["claim_id"] == claim["id"]]
            cg = [g for g in gaps if g["claim_id"] == claim["id"]]
            if run.mode == "live":
                opposition_checked = any(
                    action.get("state") == "COMPLETED"
                    and action.get("outcome", {}).get("purpose") == "OPPOSING"
                    and action.get("outcome", {}).get("claim_id") == claim["id"]
                    for action in (run.checkpoint or {}).get("actions", {}).values()
                )
                gap = next((g for g in cg if g["type"] == "OPPOSING_COVERAGE"), None)
                if gap is None:
                    gap = {
                        "claim_id": claim["id"],
                        "type": "OPPOSING_COVERAGE",
                        "reason": "Opposing discovery must be inspected before decisive completion.",
                        "next_evidence_needed": "A scoped opposing search and inspection of any resulting records.",
                    }
                    gaps.append(gap)
                    cg.append(gap)
                gap.update(material=not opposition_checked, resolved=opposition_checked)
            if not any(e["relation"] in {"SUPPORTS", "CONTRADICTS"} for e in relevant):
                gap = {
                    "claim_id": claim["id"],
                    "type": "MISSING_COMPARABLE_EVIDENCE",
                    "reason": "No comparable decisive evidence was collected.",
                    "next_evidence_needed": "Dated primary record matching confirmed scope, measure, denominator and attribution.",
                    "material": True,
                }
                if not any(g["type"] == gap["type"] and g["claim_id"] == claim["id"] for g in gaps):
                    gaps.append(gap)
                    cg.append(gap)
            findings.append(dict(claim_id=claim["id"], **finding(relevant, cg)))
        results["findings"] = findings
        gaps = [g for item in findings for g in item["gaps"]]
        results["ledger"]["gaps"] = gaps
        results["draft"] = {
            "factual_sentences": [
                {"text": e["quote"], "evidence_ids": [e["id"]]} for e in results["evidence"]
            ],
            "interpretation": "Automated proposal for editorial review.",
            "limitations": [
                "Synthetic fixture data."
                if run.mode == "fixture"
                else "Search coverage and semantic interpretation remain limited."
            ],
            "unanswered_questions": [g["next_evidence_needed"] for g in gaps if not g.get("resolved")],
        }
        results["conclusion"] = (
            "Collected evidence: "
            + ", ".join(f["finding"].replace("_", " ").lower() for f in findings)
            + ". Human editorial conclusion required."
        )
        run.results = results
        leases.event(
            session,
            run,
            "DRAFT_READY",
            {"findings": [{"claim_id": f["claim_id"], "finding": f["finding"]} for f in findings]},
        )

    update_run(lease, operation)


def _analyze_source(lease, source, claims, mode, settings, model=None):
    for claim in claims:
        if _stop(lease):
            raise StopRequested("STOPPED")
        action_key = _key("extract", {"source_id": source["id"], "claim": claim})
        if mode == "fixture":
            outcome = _action(
                lease, action_key, {}, lambda: {"candidates": source["metadata"].get("facts", [])}
            )
        else:
            with SessionLocal() as session:
                set_workspace(session, lease.workspace_id)
                path = session.get(Source, source["id"]).text_path
            text = (Path(settings.artifact_dir) / path).read_text(encoding="utf-8")
            document = {"id": source["id"], "text": text}
            input_tokens = len(prepare_input(claim, document)[0].encode()) + len(SYSTEM.encode()) + 200
            reserved_tokens = input_tokens + 2500
            pricing = _snapshot(lease)["plan"].get("pricing") or {
                "llm_input_usd_per_million": settings.llm_input_usd_per_million,
                "llm_output_usd_per_million": settings.llm_output_usd_per_million,
            }
            reserved_usd = (
                input_tokens * pricing["llm_input_usd_per_million"]
                + 2500 * pricing["llm_output_usd_per_million"]
            ) / 1_000_000

            def extract(claim=claim, document=document):
                result = model.extract(claim, document)
                return {"candidates": result.candidates, "tokens": result.tokens, "metadata": result.metadata}

            outcome = _action(lease, action_key, {"tokens": reserved_tokens, "usd": reserved_usd}, extract)
            if outcome and (
                outcome.get("tokens") or model_cost(outcome.get("metadata", {}), pricing) is not None
            ):
                actual = {"tokens": outcome["tokens"]}
                estimated_usd = model_cost(outcome.get("metadata", {}), pricing)
                if estimated_usd is not None:
                    actual["usd"] = estimated_usd
                leases.settle(SessionLocal, lease, action_key, outcome, actual=actual)
        if outcome and outcome.get("candidates"):
            _persist_evidence(lease, claim, source, outcome["candidates"], outcome.get("metadata"))


def _finish_investigation(lease):
    snapshot = _snapshot(lease)
    actions = snapshot["checkpoint"].get("actions", {}).values()
    incomplete = any(action["state"] in {"OUTCOME_UNKNOWN", "FAILED"} for action in actions)
    missing_opposition = any(
        g["type"] == "OPPOSING_COVERAGE" and not g.get("resolved")
        for g in snapshot["results"]["ledger"]["gaps"]
    )
    _finish(
        lease,
        "PARTIAL" if incomplete or missing_opposition else "COMPLETED",
        "PROVIDER_ACTIONS_INCOMPLETE"
        if incomplete
        else "OPPOSING_COVERAGE_NOT_CHECKED"
        if missing_opposition
        else None,
    )


def execute_run(run_id: str, workspace_id: str | None = None) -> None:
    lease = claim_run(run_id, "worker-" + str(uuid4()), workspace_id=workspace_id)
    if lease is None:
        return
    stopped = threading.Event()

    def heartbeat():
        while not stopped.wait(15):
            try:
                update_run(lease, lambda session, run: None)
            except Exception:  # noqa: BLE001 -- Losing heartbeat authority stops renewals.
                return

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        if _stop(lease):
            return
        _recover(lease)
        _initialize(lease)
        snapshot = _snapshot(lease)
        settings = Settings()

        def enforce_ceiling(session, run):
            run.budget = dict(
                run.budget, seconds=min(float(run.budget.get("seconds", 600)), settings.max_run_seconds)
            )

        update_run(lease, enforce_ceiling)
        model = None
        if snapshot["mode"] == "live":
            provider = snapshot["plan"].get("pricing", {}).get("llm_provider", settings.llm_provider)
            model_name = snapshot["plan"].get("pricing", {}).get("llm_model", settings.llm_model)
            key = settings.groq_api_key if provider == "groq" else settings.nvidia_api_key
            if not settings.serpapi_api_key.get_secret_value() or not key.get_secret_value():
                raise ValueError("LIVE_PROVIDERS_NOT_CONFIGURED")
            search = SerpApiSearch(settings.serpapi_api_key.get_secret_value())
            model = StructuredModel(provider, key.get_secret_value(), model_name)
        for source in snapshot["results"]["sources"]:
            if source.get("manual") and source["status"] == "ACQUIRED":
                _action(
                    lease,
                    _key("manual_read", source["id"]),
                    {"documents": 1},
                    lambda source=source: {"source_id": source["id"]},
                )
                _analyze_source(
                    lease, source, snapshot["results"]["claims"], snapshot["mode"], settings, model
                )
        if snapshot["results"]["sources"]:
            _compose(lease)
            findings = _snapshot(lease)["results"].get("findings", [])
            if findings and all(f["finding"] != "INSUFFICIENT_EVIDENCE" for f in findings):
                _finish_investigation(lease)
                return
            if snapshot["mode"] == "live" and float(snapshot["usage"].get("searches", 0)) >= float(
                snapshot["budget"].get("searches", 0)
            ):
                _finish_investigation(lease)
                return
        for round_number in range(1, min(3, int(snapshot["budget"].get("rounds", 3))) + 1):
            if _stop(lease):
                return
            round_key = f"round:{round_number}"
            _action(
                lease, round_key, {"rounds": 1}, lambda round_number=round_number: {"round": round_number}
            )
            snapshot = _snapshot(lease)
            claims = snapshot["results"]["claims"]
            urls = []
            if snapshot["mode"] == "fixture":
                for claim in claims:
                    document = fixture_for_claim(claim)
                    urls.append((f"fixture://{document.metadata['fixture_case']}", document))
            else:
                discovery_batches = []
                queries = (
                    snapshot["plan"].get("queries")
                    if round_number == 1
                    else plan_queries(claims, snapshot["results"]["ledger"]["gaps"], round_number)
                )
                queries = queries or plan_queries(claims, round_number=round_number)
                queries = [
                    {"query": q, "engine": "google", "purpose": "PRIMARY_RECORD"}
                    if isinstance(q, str)
                    else dict(q)
                    for q in queries
                ]
                for q in queries:
                    if not q.get("claim_id") and len(claims) == 1:
                        q["claim_id"] = claims[0]["id"]
                for opposing in plan_queries(claims):
                    if opposing["purpose"] == "OPPOSING" and not any(
                        q.get("purpose") == "OPPOSING" and q.get("claim_id") == opposing["claim_id"]
                        for q in queries
                    ):
                        queries.append(opposing)
                for query in queries:
                    if _stop(lease):
                        return
                    if isinstance(query, str):
                        query = {"query": query, "engine": "google", "purpose": "PRIMARY_RECORD"}
                    action_key = _key(
                        "search", {"query": query["query"], "engine": query.get("engine", "google")}
                    )
                    search_snapshot = _snapshot(lease)
                    search_id = (
                        search_snapshot["checkpoint"]
                        .get("actions", {})
                        .get(action_key, {})
                        .get("provider_search_id")
                    )
                    remaining = float(search_snapshot["budget"]["seconds"]) - float(
                        search_snapshot["usage"].get("seconds", 0)
                    )

                    def discover(q=query, key=action_key, search_id=search_id, remaining=remaining):
                        batch = search.search(
                            q["query"],
                            q.get("engine", "google"),
                            on_submitted=lambda identity: _acknowledge_search(lease, key, identity),
                            provider_search_id=search_id,
                            timeout=min(55, max(0.1, remaining)),
                        )
                        return {
                            **batch,
                            "purpose": q.get("purpose", "PRIMARY_RECORD"),
                            "claim_id": q.get("claim_id"),
                        }

                    batch = _action(
                        lease,
                        action_key,
                        {
                            "searches": 1,
                            "usd": snapshot["plan"]
                            .get("pricing", {})
                            .get("serpapi_search_usd", settings.serpapi_search_usd),
                        },
                        discover,
                    )
                    if batch and batch.get("results"):
                        discovery_batches.append(batch)
                selected = select_discovery(claims, discovery_batches)
                urls.extend((row["url"], None) for row in selected)
                update_run(
                    lease,
                    lambda session, run, round_number=round_number, selected=selected: leases.event(
                        session,
                        run,
                        "DISCOVERY_SELECTION",
                        {
                            "round": round_number,
                            "discovery_only": True,
                            "reason": "Scope cues, original host signal, purpose interleaving and domain diversity; not evidence.",
                            "selected": [row["selection"] for row in selected],
                        },
                    ),
                )
            snapshot = _snapshot(lease)
            seen = set()
            for url, fixture in urls:
                if url in seen:
                    continue
                seen.add(url)
                if _stop(lease):
                    return
                canonical = canonical_url(url) if fixture is None else None
                existing = next(
                    (
                        s
                        for s in _snapshot(lease)["results"]["sources"]
                        if s["url"] == url or (canonical is not None and canonical_url(s["url"]) == canonical)
                    ),
                    None,
                )
                if existing and existing["status"] != "ACQUIRED":
                    continue
                source = existing
                if source is None:
                    action_key = _key("acquire", url)
                    reservation = reserve(lease, action_key, {"documents": 1})
                    if reservation is None:
                        return
                    if reservation["state"] not in {"NEW", "COMPLETED"}:
                        continue
                    try:
                        document = fixture or acquire(url)
                        source = _persist_source(
                            lease,
                            url,
                            document,
                            status="SCANNED" if document.metadata.get("scanned") else "ACQUIRED",
                        )
                        leases.settle(SessionLocal, lease, action_key, {"source_id": source["id"]})
                    except (Fenced, StopRequested):
                        raise
                    except Exception as exc:  # noqa: BLE001 -- Preserve inaccessible sources without losing run.
                        source = _persist_source(
                            lease, url, None, status="UNAVAILABLE", error=type(exc).__name__
                        )
                        leases.settle(
                            SessionLocal,
                            lease,
                            action_key,
                            {"source_id": source["id"], "error": type(exc).__name__},
                        )
                        continue
                if source["status"] != "ACQUIRED":
                    continue
                _analyze_source(lease, source, claims, snapshot["mode"], settings, model)
            _compose(lease)
            snapshot = _snapshot(lease)
            if snapshot["mode"] == "fixture" or all(
                f["finding"] != "INSUFFICIENT_EVIDENCE" for f in snapshot["results"]["findings"]
            ):
                break
        if _stop(lease):
            return
        _compose(lease)
        _finish_investigation(lease)
    except BudgetExceeded as exc:
        try:
            _compose(lease)
            _finish(lease, "PARTIAL", "BUDGET_EXHAUSTED:" + str(exc))
        except Fenced:
            pass
    except StopRequested:
        try:
            _stop(lease)
        except Fenced:
            pass
    except Fenced:
        pass
    except Exception as exc:  # noqa: BLE001 -- Durable job boundary records failure before exit.
        try:
            snapshot = _snapshot(lease)
            _finish(
                lease,
                "PARTIAL" if snapshot["results"].get("sources") else "FAILED",
                type(exc).__name__ + ":" + str(exc)[:100]
                if isinstance(exc, ValueError)
                else type(exc).__name__,
            )
        except Fenced:
            pass
    finally:
        stopped.set()
        thread.join(timeout=1)
        try:
            final = _snapshot(lease)
            logger.info(
                "run.finished",
                extra={"run_id": run_id, "workspace_id": lease.workspace_id, "state": final["state"]},
            )
        except Exception:  # noqa: BLE001 -- Final diagnostic must not replace the durable job outcome.
            logger.warning("run.final_state_unavailable", extra={"run_id": run_id})
