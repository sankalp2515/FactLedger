import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

from product_core.db import Base
from product_core.models import Case, Run, Workspace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

spec = importlib.util.spec_from_file_location(
    "reapply", Path(__file__).parents[2] / "scripts/reapply_deletions.py"
)
reapply_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reapply_module)


def test_restore_ledger_order_keeps_runs_cancelled_and_never_unpurges(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    stamp = datetime.now(UTC).isoformat()
    with factory.begin() as session:
        session.add(Workspace(id="w", name="Synthetic"))
        session.flush()
        session.add_all(
            [
                Case(id="c", workspace_id="w", title="Synthetic", original_claim="Synthetic"),
                Case(
                    id="p",
                    workspace_id="w",
                    title="[purged]",
                    original_claim="",
                    state="PURGED",
                    deleted_at=datetime.now(UTC),
                ),
            ]
        )
        session.flush()
        session.add(
            Run(
                id="r",
                workspace_id="w",
                case_id="c",
                base_revision=1,
                state="RUNNING",
                mode="fixture",
                plan={},
                budget={},
                lease_owner="old",
                lease_generation=3,
            )
        )
    monkeypatch.setattr(reapply_module, "SessionLocal", factory)
    ledger = tmp_path / "ledger.jsonl"
    entries = [
        {"workspace_id": "wrong", "case_id": "c", "deleted_at": stamp},
        {"workspace_id": "w", "case_id": "c", "deleted_at": stamp},
        {"workspace_id": "w", "case_id": "c", "restored_at": stamp},
        {"workspace_id": "w", "case_id": "p", "restored_at": stamp},
    ]
    ledger.write_text("\n".join(json.dumps(entry) for entry in entries))
    assert reapply_module.reapply(ledger) == 3
    with factory() as session:
        assert session.get(Case, "c").deleted_at is None
        assert session.get(Case, "p").deleted_at is not None
        run = session.get(Run, "r")
        assert run.state == "CANCELLED"
        assert run.lease_generation == 4
        assert run.lease_owner is None
    reapply_module.reapply(ledger)
    with factory() as session:
        assert session.get(Run, "r").lease_generation == 4
