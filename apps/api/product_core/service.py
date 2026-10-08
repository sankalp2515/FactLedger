"""Transactional application commands. Never merge research into changed scope silently."""

import html
import json
import os
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256

from sqlalchemy import func, or_, select

from .auth import Actor, DomainError, require_role
from .config import artifact_root, get_settings
from .db import SessionLocal, set_workspace
from .models import (
    Audit,
    Case,
    Evidence,
    Export,
    Idempotency,
    Membership,
    Plan,
    ReviewRequest,
    Revision,
    Run,
    RunEvent,
    Workspace,
    now,
    uid,
)

ACTIVE = {"QUEUED", "RUNNING", "PAUSE_REQUESTED", "PAUSED", "CANCEL_REQUESTED"}


@contextmanager
def transaction(actor: Actor):
    with SessionLocal.begin() as db:
        set_workspace(db, actor.workspace_id)
        yield db


def case_for(db, actor, case_id, include_deleted=False):
    case = db.scalar(
        select(Case).where(Case.id == case_id, Case.workspace_id == actor.workspace_id).with_for_update()
    )
    if not case or (case.deleted_at and not include_deleted):
        raise DomainError("NOT_FOUND", "Case is unavailable.", 404)
    return case


def expected(case, revision):
    if case.revision != revision:
        raise DomainError("REVISION_CONFLICT", "This case changed. Reload and reapply your edits.")


def snapshot(db, case, number=None):
    revision = db.scalar(
        select(Revision).where(
            Revision.case_id == case.id,
            Revision.workspace_id == case.workspace_id,
            Revision.number == (number or case.revision),
        )
    )
    if revision is None:
        raise DomainError("NOT_FOUND", "Revision is unavailable.", 404)
    return deepcopy(revision.payload)


def empty_payload():
    return {
        "claims": [],
        "projects": [],
        "evidence": [],
        "sources": [],
        "ledger": {"stages": [], "funding": [], "metrics": [], "derived": [], "gaps": []},
        "notes": [],
        "conclusion": "",
        "lineage": [],
    }


def serialize(row):
    result = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    for key, value in result.items():
        if hasattr(value, "isoformat"):
            result[key] = value.isoformat()
    if "metadata_json" in result:
        result["metadata"] = result.pop("metadata_json")
    result.pop("artifact_path", None)
    result.pop("text_path", None)
    return result


def audit(db, actor, case, action):
    db.add(
        Audit(
            workspace_id=actor.workspace_id,
            actor_id=actor.id,
            case_id=case.id,
            action=action,
            revision=case.revision,
        )
    )


def persist_revision(db, actor, case, payload, action, initial=False):
    if not initial:
        case.revision += 1
        case.state = "DRAFT"
        for review in db.scalars(
            select(ReviewRequest).where(
                ReviewRequest.case_id == case.id,
                ReviewRequest.workspace_id == actor.workspace_id,
                ReviewRequest.status == "OPEN",
            )
        ):
            review.status = "SUPERSEDED"
    case.updated_at = now()
    payload = deepcopy(payload)
    payload["_case"] = {"title": case.title, "tags": case.tags, "assignee_id": case.assignee_id}
    db.add(Revision(workspace_id=actor.workspace_id, case_id=case.id, number=case.revision, payload=payload))
    audit(db, actor, case, action)
    db.flush()


def detail(db, case, revision=None):
    payload = snapshot(db, case, revision)
    result = serialize(case)
    if revision:
        result["revision"] = revision
        result.update(payload.get("_case", {}))
    result["payload"] = payload
    run = db.scalar(
        select(Run)
        .where(Run.case_id == case.id, Run.workspace_id == case.workspace_id)
        .order_by(Run.created_at.desc())
        .limit(1)
    )
    result["latest_run"] = run_detail(db, run) if run else None
    result["review_requests"] = [
        serialize(r)
        for r in db.scalars(
            select(ReviewRequest)
            .where(ReviewRequest.case_id == case.id)
            .order_by(ReviewRequest.created_at.desc())
        )
    ]
    if revision and revision != case.revision:
        matching = [r for r in result["review_requests"] if r["revision"] == revision]
        result["state"] = matching[0]["status"] if matching else "DRAFT"
        result["latest_run"] = None
    return result


def run_detail(db, run):
    result = serialize(run)
    result["events"] = [
        serialize(e)
        for e in db.scalars(select(RunEvent).where(RunEvent.run_id == run.id).order_by(RunEvent.seq))
    ]
    return result


def event(db, run, type_, payload):
    seq = (db.scalar(select(func.max(RunEvent.seq)).where(RunEvent.run_id == run.id)) or 0) + 1
    db.add(
        RunEvent(
            workspace_id=run.workspace_id,
            case_id=run.case_id,
            run_id=run.id,
            seq=seq,
            type=type_,
            payload=payload,
        )
    )


def create_case(actor, data):
    with transaction(actor) as db:
        case = Case(workspace_id=actor.workspace_id, **data)
        db.add(case)
        db.flush()
        persist_revision(db, actor, case, empty_payload(), "case.created", initial=True)
        return detail(db, case)


def scope_case(actor, case_id, data):
    with transaction(actor) as db:
        case = case_for(db, actor, case_id)
        expected(case, data["expected_revision"])
        payload = snapshot(db, case)
        payload["claims"] = [{**claim, "id": uid(), "version": case.revision + 1} for claim in data["claims"]]
        payload["projects"] = [
            {
                "id": uid(),
                "canonical_name": c["subject"],
                "geography": c["geography"],
                "identity_status": "CONFIRMED",
            }
            for c in payload["claims"]
        ]
        payload["evidence"] = []
        payload["ledger"] = empty_payload()["ledger"]
        payload["conclusion"] = ""
        persist_revision(db, actor, case, payload, "scope.confirmed")
        return detail(db, case)


def patch_case(actor, case_id, data):
    with transaction(actor) as db:
        case = case_for(db, actor, case_id)
        expected(case, data.pop("expected_revision"))
        if (
            "assignee_id" in data
            and data["assignee_id"]
            and not db.get(Membership, (actor.workspace_id, data["assignee_id"]))
        ):
            raise DomainError("INVALID_SCOPE", "Assignee must belong to this workspace.", 422)
        payload = snapshot(db, case)
        for key, value in data.items():
            setattr(case, key, value)
        persist_revision(db, actor, case, payload, "case.updated")
        return detail(db, case)


def make_plan(actor, case_id, revision):
    with transaction(actor) as db:
        case = case_for(db, actor, case_id)
        expected(case, revision)
        payload = snapshot(db, case)
        if not payload["claims"]:
            raise DomainError("INVALID_SCOPE", "Confirm at least one scoped claim before planning.", 422)
        queries = []
        for claim in payload["claims"]:
            base = f"{claim['subject']} {claim['geography']} {claim['period']}"
            queries.extend(
                [
                    {
                        "query": base + " official status report",
                        "engine": "google",
                        "purpose": "PRIMARY_RECORD",
                        "claim_id": claim["id"],
                    },
                    {
                        "query": base + " delays incomplete not operational audit",
                        "engine": "google_news",
                        "purpose": "OPPOSING",
                        "claim_id": claim["id"],
                    },
                ]
            )
        plan = Plan(
            workspace_id=actor.workspace_id,
            case_id=case.id,
            revision=revision,
            payload={
                "claims": payload["claims"],
                "sources": payload["sources"],
                "queries": queries,
                "scope_hash": digest(payload["claims"]),
                "budget": {
                    "searches": 12,
                    "documents": 30,
                    "rounds": 3,
                    "tokens": 60000,
                    "seconds": 600,
                    "usd": 2,
                },
            },
        )
        db.add(plan)
        db.flush()
        return {"id": plan.id, **plan.payload}


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def start_run(actor, case_id, data, key):
    with transaction(actor) as db:
        case = case_for(db, actor, case_id)
        operation = f"run:{case_id}"
        prior = db.get(Idempotency, (actor.workspace_id, operation, key)) if key else None
        if prior:
            if prior.request_hash != digest(data):
                raise DomainError("IDEMPOTENCY_CONFLICT", "This key was already used with different inputs.")
            return run_detail(db, db.get(Run, prior.response["id"]))
        expected(case, data["expected_revision"])
        plan = db.scalar(
            select(Plan).where(
                Plan.id == data["plan_id"], Plan.workspace_id == actor.workspace_id, Plan.case_id == case.id
            )
        )
        if not plan or plan.payload["scope_hash"] != digest(snapshot(db, case)["claims"]):
            raise DomainError("SCOPE_CHANGED", "The plan no longer matches this case scope.")
        if db.scalar(select(Run.id).where(Run.case_id == case.id, Run.state.in_(ACTIVE))):
            raise DomainError(
                "RUN_ALREADY_ACTIVE", "Finish or cancel the current run before starting another."
            )
        # Admission is serialized across cases, not only within one case.
        db.scalar(select(Workspace).where(Workspace.id == actor.workspace_id).with_for_update())
        if data["mode"] == "live":
            day_start = now().replace(hour=0, minute=0, second=0, microsecond=0)
            charged = 0.0
            for previous in db.execute(
                select(Run.state, Run.budget, Run.usage, Run.created_at).where(
                    Run.workspace_id == actor.workspace_id,
                    Run.mode == "live",
                    or_(Run.state.in_(ACTIVE), Run.created_at >= day_start),
                )
            ):
                if previous.state in ACTIVE:
                    charged += float(previous.budget.get("usd", 0))
                elif previous.created_at.replace(tzinfo=day_start.tzinfo) >= day_start:
                    charged += float(previous.usage.get("usd", 0))
            if charged + float(data["budget"]["usd"]) > get_settings().workspace_daily_usd:
                raise DomainError(
                    "BUDGET_EXCEEDED",
                    "The requested budget exceeds this workspace's remaining daily allowance. Reduce the run budget or wait until tomorrow (UTC).",
                    429,
                )
        workspace = db.scalar(
            select(func.count())
            .select_from(Run)
            .where(Run.workspace_id == actor.workspace_id, Run.state.in_(ACTIVE))
        )
        if workspace >= 2:
            raise DomainError("RATE_LIMITED", "This workspace already has two active investigations.", 429)
        run = Run(
            workspace_id=actor.workspace_id,
            case_id=case.id,
            base_revision=case.revision,
            mode=data["mode"],
            plan={**plan.payload, "actor_id": actor.id},
            budget=data["budget"],
            usage={
                "searches": 0,
                "documents": 0,
                "rounds": 0,
                "tokens": 0,
                "seconds": 0,
                "usd": 0,
                "cost_estimated": True,
            },
            results=empty_payload(),
        )
        db.add(run)
        db.flush()
        case.state = "INVESTIGATING"
        event(db, run, "run.created", {"message": "Investigation queued", "mode": run.mode})
        if key:
            db.add(
                Idempotency(
                    workspace_id=actor.workspace_id,
                    operation=operation,
                    key=key,
                    request_hash=digest(data),
                    response={"id": run.id},
                )
            )
        audit(db, actor, case, "run.created")
        db.flush()
        return run_detail(db, run)


def run_for(db, actor, run_id):
    run = db.scalar(
        select(Run).where(Run.id == run_id, Run.workspace_id == actor.workspace_id).with_for_update()
    )
    if not run:
        raise DomainError("NOT_FOUND", "Investigation is unavailable.", 404)
    case_for(db, actor, run.case_id)
    return run


def control_run(actor, run_id, action):
    with transaction(actor) as db:
        run = run_for(db, actor, run_id)
        if action == "pause":
            if run.state in {"PAUSED", "PAUSE_REQUESTED"}:
                return run_detail(db, run)
            if run.state not in {"RUNNING", "QUEUED"}:
                raise DomainError("INVALID_STATE", "Only an active run can be paused.")
            run.state = "PAUSED" if run.state == "QUEUED" else "PAUSE_REQUESTED"
        elif action == "resume":
            if run.state == "QUEUED":
                return run_detail(db, run)
            if run.state != "PAUSED":
                raise DomainError("INVALID_STATE", "Only a paused investigation can resume.")
            run.state = "QUEUED"
        elif action == "cancel":
            if run.state in {"CANCELLED", "COMPLETED", "PARTIAL", "FAILED"}:
                return run_detail(db, run)
            run.state = "CANCELLED" if run.state in {"QUEUED", "PAUSED"} else "CANCEL_REQUESTED"
        run.updated_at = now()
        event(db, run, f"run.{action}_requested", {"state": run.state})
        db.flush()
        return run_detail(db, run)


def integrate(actor, run_id, revision):
    with transaction(actor) as db:
        run = run_for(db, actor, run_id)
        case = case_for(db, actor, run.case_id)
        expected(case, revision)
        if run.state not in {"COMPLETED", "PARTIAL", "CANCELLED", "FAILED"}:
            raise DomainError("INVALID_STATE", "Finish or cancel the run before integrating results.")
        payload = snapshot(db, case)
        if digest(payload["claims"]) != run.plan["scope_hash"]:
            raise DomainError(
                "SCOPE_CHANGED", "These results belong to an earlier claim scope. Start a new scoped run."
            )
        if run.checkpoint.get("integrated_revision"):
            return detail(db, case)
        result = run.results or {}
        for key in ["evidence", "sources", "lineage"]:
            existing_ids = {item.get("id") for item in payload[key]}
            payload[key].extend(item for item in result.get(key, []) if item.get("id") not in existing_ids)
        for key in payload["ledger"]:
            payload["ledger"][key].extend(result.get("ledger", {}).get(key, []))
        payload["findings"] = result.get("findings", [])
        payload["draft"] = result.get("draft", "")
        payload["run_ids"] = [*payload.get("run_ids", []), run.id]
        persist_revision(db, actor, case, payload, "run.integrated")
        case.state = "READY_FOR_REVIEW"
        run.checkpoint = {**run.checkpoint, "integrated_revision": case.revision}
        return detail(db, case)


def add_note(actor, case_id, data):
    with transaction(actor) as db:
        case = case_for(db, actor, case_id)
        expected(case, data.pop("expected_revision"))
        payload = snapshot(db, case)
        check_citations(payload, data.get("evidence_ids", []))
        payload["notes"].append({"id": uid(), "actor_id": actor.id, "created_at": now().isoformat(), **data})
        persist_revision(db, actor, case, payload, "note.added")
        return detail(db, case)


def check_citations(payload, ids):
    available = {item["id"] for item in payload["evidence"]}
    if any(eid not in available for eid in ids):
        raise DomainError("INVALID_SCOPE", "A citation does not belong to this revision.", 422)


def override_evidence(actor, evidence_id, data):
    with transaction(actor) as db:
        evidence = db.scalar(
            select(Evidence).where(Evidence.id == evidence_id, Evidence.workspace_id == actor.workspace_id)
        )
        if not evidence:
            raise DomainError("NOT_FOUND", "Evidence is unavailable.", 404)
        case = case_for(db, actor, evidence.case_id)
        expected(case, data["expected_revision"])
        payload = snapshot(db, case)
        item = next((e for e in payload["evidence"] if e["id"] == evidence_id), None)
        if not item:
            raise DomainError("SCOPE_CHANGED", "Evidence is not active in this revision.")
        if data["relation"] in {"SUPPORTS", "CONTRADICTS"} and (
            not item.get("quote")
            or item.get("comparison", {}).get("gaps")
            or (item.get("comparison", {}).get("quantity") or {}).get("comparable") is False
            or not item.get("anchor")
        ):
            raise DomainError(
                "INVALID_SCOPE", "Decisive relations require anchored, comparable evidence.", 422
            )
        item["previous_relation"] = item["relation"]
        item["relation"] = data["relation"]
        item["override"] = {"actor_id": actor.id, "reason": data["reason"], "time": now().isoformat()}
        payload.pop("findings", None)
        persist_revision(db, actor, case, payload, "evidence.corrected")
        return detail(db, case)


def submit_review(actor, case_id, data):
    with transaction(actor) as db:
        case = case_for(db, actor, case_id)
        expected(case, data["expected_revision"])
        payload = snapshot(db, case)
        check_citations(payload, data["citations"])
        if db.scalar(
            select(ReviewRequest.id).where(
                ReviewRequest.case_id == case.id, ReviewRequest.revision == case.revision
            )
        ):
            raise DomainError(
                "INVALID_STATE",
                "This revision already has a review. Make a new draft revision before resubmitting a changed conclusion.",
            )
        payload["conclusion"] = data["conclusion"]
        request = ReviewRequest(
            workspace_id=actor.workspace_id,
            case_id=case.id,
            revision=case.revision,
            submitted_by=actor.id,
            conclusion=data["conclusion"],
            citations=data["citations"],
            snapshot=payload,
        )
        db.add(request)
        case.state = "IN_REVIEW"
        audit(db, actor, case, "review.submitted")
        db.flush()
        return serialize(request)


def review_for(db, actor, review_id):
    review = db.scalar(
        select(ReviewRequest)
        .where(ReviewRequest.id == review_id, ReviewRequest.workspace_id == actor.workspace_id)
        .with_for_update()
    )
    if not review:
        raise DomainError("NOT_FOUND", "Review is unavailable.", 404)
    case = case_for(db, actor, review.case_id)
    return review, case


def decide_review(actor, review_id, data):
    require_role(actor, "editor", "owner")
    with transaction(actor) as db:
        review, case = review_for(db, actor, review_id)
        if review.submitted_by == actor.id:
            raise DomainError("FORBIDDEN", "A different editor must review this submission.", 403)
        if (
            review.status != "OPEN"
            or review.revision != case.revision
            or data["expected_revision"] != review.revision
        ):
            if (
                review.decision == data["decision"]
                and review.decided_by == actor.id
                and review.reason == data["reason"]
            ):
                return serialize(review)
            raise DomainError(
                "REVIEW_SUPERSEDED", "This review was decided or superseded by a newer revision."
            )
        review.decision, review.reason, review.decided_by = data["decision"], data["reason"], actor.id
        review.status = "APPROVED" if data["decision"] == "APPROVE" else "RETURNED"
        case.state = review.status
        audit(db, actor, case, "review.decided")
        return serialize(review)


def delete_case(actor, case_id, revision):
    require_role(actor, "owner", "researcher")
    with transaction(actor) as db:
        case = case_for(db, actor, case_id)
        expected(case, revision)
        deleted_at = now()
        ledger = artifact_root().parent / "deletion-ledger.jsonl"
        with ledger.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    {
                        "workspace_id": actor.workspace_id,
                        "case_id": case.id,
                        "deleted_at": deleted_at.isoformat(),
                    }
                )
                + "\n"
            )
            file.flush()
            os.fsync(file.fileno())
        case.deleted_at = deleted_at
        for run in db.scalars(
            select(Run).where(Run.case_id == case.id, Run.state.in_(ACTIVE)).with_for_update()
        ):
            run.state = "CANCELLED"
            run.lease_generation += 1
        audit(db, actor, case, "case.deletion_scheduled")
        return {"deleted": True, "recoverable_until": (deleted_at + timedelta(days=7)).isoformat()}


def export_case(actor, case_id, revision, format_):
    with transaction(actor) as db:
        case = case_for(db, actor, case_id)
        payload = snapshot(db, case, revision)
        review = db.scalar(
            select(ReviewRequest).where(
                ReviewRequest.case_id == case.id,
                ReviewRequest.revision == revision,
            )
        )
        title = payload.get("_case", {}).get("title", case.title)
        pack = {
            "schema_version": 1,
            "product": "[Product Name]",
            "case_id": case.id,
            "revision": revision,
            "title": title,
            "status": "APPROVED" if review and review.status == "APPROVED" else "DRAFT",
            "conclusion": review.conclusion
            if review
            else payload.get("conclusion", "No human conclusion submitted."),
            "review": serialize(review) if review else None,
            "claims": payload["claims"],
            "evidence": payload["evidence"],
            "ledger": payload["ledger"],
            "notes": payload["notes"],
            "sources": payload["sources"],
            "lineage": payload["lineage"],
            "runs": [],
        }
        for run_id in payload.get("run_ids", []):
            run = db.get(Run, run_id)
            if run and run.workspace_id == actor.workspace_id:
                pack["runs"].append(
                    {"id": run.id, "mode": run.mode, "plan": run.plan, "usage": run.usage, "state": run.state}
                )
        pack["manifest"] = {
            "payload_sha256": digest(pack),
            "source_hashes": {s["id"]: s.get("content_hash", "") for s in pack["sources"]},
            "note": "Hashes identify preserved bytes, not source authenticity.",
        }
        content = json.dumps(pack, ensure_ascii=False, indent=2, default=str)
        if format_ in {"md", "html"}:
            markdown = f"# {title}\n\n{pack['status']} · Revision {revision}\n\n## Qualified human conclusion\n\n{pack['conclusion']}\n\n"
            for e in pack["evidence"]:
                markdown += f"## {e['relation']} · {e['id']}\n\n> {e['quote']}\n\nSource: {e['source_id']}\n\n{e.get('rationale', '')}\n\n"
            markdown += (
                "## Reproducibility manifest and complete evidence data\n\n```json\n" + content + "\n```\n"
            )
            content = (
                markdown
                if format_ == "md"
                else '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Evidence pack</title><body><pre style="white-space:pre-wrap;max-width:80ch;margin:3rem auto;font:16px/1.6 system-ui">'
                + html.escape(markdown)
                + "</pre></body></html>"
            )
        export = Export(
            workspace_id=actor.workspace_id,
            case_id=case.id,
            revision=revision,
            format=format_,
            content=content,
            content_hash=sha256(content.encode()).hexdigest(),
        )
        db.add(export)
        db.flush()
        audit(db, actor, case, "pack.exported")
        return {
            "id": export.id,
            "download_url": f"/v1/exports/{export.id}/download",
            "sha256": export.content_hash,
        }
