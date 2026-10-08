"""PostgreSQL polling worker: durable queue needs no Redis to recover."""

import argparse
import signal
import threading
from datetime import UTC, datetime

from sqlalchemy import or_, select, text

from product_core.db import SessionLocal, init_db
from product_core.investigation.executor import execute_run
from product_core.models import Run


def poll_once() -> int:
    with SessionLocal() as session:
        if session.get_bind().dialect.name == "postgresql":
            rows = session.execute(
                text("SELECT run_id, workspace_id FROM public.factledger_due_runs()")
            ).all()
        else:
            rows = session.execute(
                select(Run.id, Run.workspace_id)
                .where(
                    Run.state.in_(["QUEUED", "RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"]),
                    or_(Run.lease_expires_at.is_(None), Run.lease_expires_at < datetime.now(UTC)),
                )
                .order_by(Run.created_at)
                .limit(10)
            ).all()
    for run_id, workspace_id in rows:
        execute_run(run_id, workspace_id=workspace_id)
    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    init_db()
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    while not stop.is_set():
        poll_once()
        if args.once:
            return
        stop.wait(2)


if __name__ == "__main__":
    main()
