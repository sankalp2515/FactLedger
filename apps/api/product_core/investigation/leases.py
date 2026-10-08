"""Row-locked fenced run writes and conservative durable reservations."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text

from product_core.db import set_workspace
from product_core.models import Case, Membership, Run, RunEvent, now

TERMINAL = {"COMPLETED", "PARTIAL", "FAILED", "CANCELLED"}


class Fenced(RuntimeError):
    pass


class BudgetExceeded(RuntimeError):
    pass


class StopRequested(RuntimeError):
    pass


@dataclass(frozen=True)
class Lease:
    run_id: str
    owner: str
    generation: int
    workspace_id: str


def aware(value):
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def locked(session, run_id):
    if session.bind.dialect.name == "sqlite":
        session.execute(text("BEGIN IMMEDIATE"))
    return session.scalar(select(Run).where(Run.id == run_id).with_for_update())


def event(session, run, kind, payload):
    seq = (session.scalar(select(func.max(RunEvent.seq)).where(RunEvent.run_id == run.id)) or 0) + 1
    session.add(
        RunEvent(
            workspace_id=run.workspace_id,
            case_id=run.case_id,
            run_id=run.id,
            seq=seq,
            type=kind,
            payload=payload,
        )
    )
    session.flush()


def tick(run):
    checkpoint = deepcopy(run.checkpoint or {})
    usage = deepcopy(run.usage or {})
    last = checkpoint.get("last_tick")
    if last:
        elapsed = max(0, (now() - datetime.fromisoformat(last)).total_seconds())
        usage["seconds"] = round(float(usage.get("seconds", 0)) + min(elapsed, 60), 3)
    checkpoint["last_tick"] = now().isoformat()
    run.checkpoint = checkpoint
    run.usage = usage


def claim_run(sessions, run_id, owner):
    with sessions.begin() as session:
        run = locked(session, run_id)
        if not run or run.state in TERMINAL or run.state == "PAUSED":
            return None
        set_workspace(session, run.workspace_id)
        if run.lease_owner and aware(run.lease_expires_at) > now():
            return None
        if run.state == "RUNNING":
            tick(run)
        case = session.get(Case, run.case_id)
        if not case or case.deleted_at:
            run.state = "CANCELLED"
            return None
        run.lease_owner = owner
        run.lease_generation += 1
        run.lease_expires_at = now() + timedelta(seconds=60)
        checkpoint = deepcopy(run.checkpoint or {})
        checkpoint["last_tick"] = now().isoformat()
        run.checkpoint = checkpoint
        run.state = run.state if run.state in {"PAUSE_REQUESTED", "CANCEL_REQUESTED"} else "RUNNING"
        event(session, run, "LEASE_CLAIMED", {"generation": run.lease_generation})
        return Lease(run_id, owner, run.lease_generation, run.workspace_id)


def update_run(sessions, lease, operation):
    with sessions.begin() as session:
        # Set transaction-local tenant before any scoped query. Claim enumeration
        # requires the documented privileged worker dispatch database role.
        if session.bind.dialect.name == "postgresql":
            set_workspace(session, lease.workspace_id)
        run = locked(session, lease.run_id)
        if (
            not run
            or run.lease_owner != lease.owner
            or run.lease_generation != lease.generation
            or not run.lease_expires_at
            or aware(run.lease_expires_at) <= now()
        ):
            raise Fenced("LEASE_EXPIRED_OR_REPLACED")
        case = session.get(Case, run.case_id)
        actor = (run.plan or {}).get("actor_id")
        revoked = actor and not session.get(Membership, (run.workspace_id, actor))
        if not case or case.deleted_at or revoked:
            run.state = "CANCELLED"
            run.lease_owner = None
            event(session, run, "CANCELLED", {"reason": "CASE_DELETED_OR_ACCESS_REVOKED"})
            return None
        tick(run)
        run.updated_at = now()
        result = operation(session, run)
        if run.state not in TERMINAL and run.state != "PAUSED":
            run.lease_expires_at = now() + timedelta(seconds=60)
        return result


def reserve(sessions, lease, key, amount):
    def operation(session, run):
        if run.state in {"PAUSE_REQUESTED", "CANCEL_REQUESTED", "PAUSED", *TERMINAL}:
            raise StopRequested(run.state)
        checkpoint = deepcopy(run.checkpoint or {})
        actions = checkpoint.setdefault("actions", {})
        if key in actions:
            return deepcopy(actions[key])
        usage = deepcopy(run.usage or {})
        for name in ("searches", "documents", "rounds", "tokens", "seconds", "usd"):
            proposed = Decimal(str(usage.get(name, 0))) + Decimal(str(amount.get(name, 0)))
            if proposed > Decimal(str(run.budget.get(name, 0))):
                raise BudgetExceeded(name)
        for name, value in amount.items():
            if name in {"usd", "seconds"}:
                usage[name] = float(Decimal(str(usage.get(name, 0))) + Decimal(str(value)))
            else:
                usage[name] = int(usage.get(name, 0)) + int(value)
        usage["cost_estimated"] = True
        actions[key] = {
            "state": "RESERVED",
            "amount": amount,
            "generation": lease.generation,
            "started_at": now().isoformat(),
        }
        run.checkpoint = checkpoint
        run.usage = usage
        event(session, run, "ACTION_RESERVED", {"action": key, "amount": amount})
        return {"state": "NEW"}

    return update_run(sessions, lease, operation)


def settle(sessions, lease, key, outcome, actual=None, unknown=False, failed=False):
    def operation(session, run):
        checkpoint = deepcopy(run.checkpoint)
        action = checkpoint["actions"][key]
        action.update(
            state="OUTCOME_UNKNOWN" if unknown else "FAILED" if failed else "COMPLETED",
            outcome=outcome,
            completed_at=now().isoformat(),
        )
        if actual and not unknown:
            usage = deepcopy(run.usage)
            reconciled = action.setdefault("reconciled", {})
            for name, value in actual.items():
                if name in reconciled:
                    continue
                # Provider usage can exceed estimates: record it honestly and stop later dispatch.
                usage[name] = max(
                    0,
                    float(
                        Decimal(str(usage.get(name, 0)))
                        - Decimal(str(action["amount"].get(name, 0)))
                        + Decimal(str(value))
                    ),
                )
                if name not in {"usd", "seconds"}:
                    usage[name] = int(usage[name])
                reconciled[name] = value
            run.usage = usage
        run.checkpoint = checkpoint
        event(session, run, action["state"], {"action": key, "outcome": outcome})

    return update_run(sessions, lease, operation)
