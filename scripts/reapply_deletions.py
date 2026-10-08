"""Reapply a separately preserved deletion ledger after restoring older backups."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from product_core.db import SessionLocal
from product_core.models import Case, Run
from sqlalchemy import select


def reapply(path: Path) -> int:
    entries = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    count = 0
    with SessionLocal.begin() as session:
        for item in entries:
            case = session.scalar(
                select(Case).where(Case.id == item["case_id"], Case.workspace_id == item["workspace_id"])
            )
            if case is None:
                continue
            if "restored_at" in item:
                datetime.fromisoformat(item["restored_at"])
                if case.state != "PURGED":
                    case.deleted_at = None
                count += 1
                continue
            case.deleted_at = datetime.fromisoformat(item["deleted_at"])
            for run in session.scalars(
                select(Run).where(Run.case_id == case.id, Run.workspace_id == case.workspace_id)
            ):
                if run.state not in {"COMPLETED", "FAILED", "CANCELLED"}:
                    run.state = "CANCELLED"
                    run.lease_owner = None
                    run.lease_expires_at = None
                    run.lease_generation += 1
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args()
    print(f"Reapplied {reapply(args.ledger)} tombstones; application remains offline until verification.")
