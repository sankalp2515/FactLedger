import pytest
from product_core.db import Base
from product_core.investigation import executor
from product_core.models import Case, Revision, Run, Workspace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def database(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///" + str(tmp_path / "worker.db"))
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(executor, "SessionLocal", sessions)
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path / "artifacts"))
    c = {
        "id": "claim",
        "subject": "Hospital A",
        "geography": "District A",
        "period": "2026-09",
        "stage": "OPERATIONAL",
        "measure": "CAPACITY",
        "value": "200",
        "unit": "beds",
        "attribution": "Synthetic public authority",
    }
    with sessions.begin() as s:
        s.add(Workspace(id="w", name="W"))
        s.flush()
        s.add(Case(id="case", workspace_id="w", title="Case", original_claim="Hospital claim"))
        s.flush()
        s.add(Revision(id="revision", workspace_id="w", case_id="case", number=1, payload={"claims": [c]}))
        s.add(
            Run(
                id="run",
                workspace_id="w",
                case_id="case",
                base_revision=1,
                mode="fixture",
                plan={"claims": [c], "queries": []},
                budget={
                    "searches": 12,
                    "documents": 30,
                    "rounds": 3,
                    "tokens": 60000,
                    "seconds": 600,
                    "usd": 2,
                },
                results={},
                checkpoint={},
                usage={},
            )
        )
    return sessions
