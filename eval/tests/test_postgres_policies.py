"""Run with PostgreSQL DATABASE_URL after alembic upgrade head."""

import os
from uuid import uuid4

import pytest
from product_core.models import Case, Workspace
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL", "").startswith("postgresql"), reason="PostgreSQL integration only"
)
def test_nonowner_role_fails_closed_and_scopes_rows():
    engine = create_engine(os.environ["DATABASE_URL"])
    first, second = str(uuid4()), str(uuid4())
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(
                Workspace.__table__.insert(),
                [{"id": first, "name": "RLS A"}, {"id": second, "name": "RLS B"}],
            )
            connection.execute(
                Case.__table__.insert(),
                [
                    {"id": str(uuid4()), "workspace_id": first, "title": "A", "original_claim": "Synthetic"},
                    {"id": str(uuid4()), "workspace_id": second, "title": "B", "original_claim": "Synthetic"},
                ],
            )
            connection.execute(text("SET LOCAL ROLE evidence_app"))
            assert connection.execute(select(Case.id)).all() == []
            connection.execute(text("SELECT set_config('app.workspace_id', :scope, true)"), {"scope": first})
            assert [row.workspace_id for row in connection.execute(select(Case.workspace_id))] == [first]
            savepoint = connection.begin_nested()
            with pytest.raises(DBAPIError):
                connection.execute(
                    Case.__table__.insert(),
                    {
                        "id": str(uuid4()),
                        "workspace_id": second,
                        "title": "Forbidden",
                        "original_claim": "Synthetic",
                    },
                )
            savepoint.rollback()
            connection.execute(text("SELECT set_config('app.workspace_id', :scope, true)"), {"scope": second})
            assert [row.workspace_id for row in connection.execute(select(Case.workspace_id))] == [second]
        finally:
            transaction.rollback()
    engine.dispose()


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL", "").startswith("postgresql"), reason="PostgreSQL integration only"
)
def test_nonowner_worker_dispatch_claim_preserves_tenant_isolation(monkeypatch):
    from product_core import worker
    from product_core.investigation import leases
    from product_core.models import Run
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(os.environ["DATABASE_URL"])
    workspace_id, case_id, run_id = (str(uuid4()) for _ in range(3))
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(Workspace.__table__.insert(), {"id": workspace_id, "name": "Worker RLS"})
            connection.execute(
                Case.__table__.insert(),
                {
                    "id": case_id,
                    "workspace_id": workspace_id,
                    "title": "Worker claim",
                    "original_claim": "Synthetic",
                },
            )
            connection.execute(
                Run.__table__.insert(),
                {
                    "id": run_id,
                    "workspace_id": workspace_id,
                    "case_id": case_id,
                    "base_revision": 1,
                    "mode": "fixture",
                    "plan": {},
                    "budget": {},
                },
            )
            connection.execute(text("SET LOCAL ROLE evidence_app"))
            assert connection.execute(select(Run.id)).all() == []
            due = connection.execute(text("SELECT run_id, workspace_id FROM public.factledger_due_runs()"))
            dispatched = due.all()
            assert len(dispatched) <= 10
            assert (run_id, workspace_id) in dispatched
            function = connection.execute(
                text("""
                SELECT prosecdef, proconfig,
                    NOT EXISTS (SELECT 1 FROM pg_catalog.aclexplode(proacl) AS acl
                                WHERE acl.grantee = 0 AND acl.privilege_type = 'EXECUTE') AS private
                FROM pg_catalog.pg_proc
                WHERE oid = 'public.factledger_due_runs()'::regprocedure
            """)
            ).one()
            assert function.prosecdef and function.private
            assert function.proconfig == ["search_path=pg_catalog"]
            sessions = sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
            claimed = []

            def execute_dispatched(dispatched_id, workspace_id=None):
                if dispatched_id == run_id:
                    claimed.append(
                        leases.claim_run(
                            sessions, dispatched_id, "worker-regression", workspace_id=workspace_id
                        )
                    )

            monkeypatch.setattr(worker, "SessionLocal", sessions)
            monkeypatch.setattr(worker, "execute_run", execute_dispatched)
            assert worker.poll_once() == len(dispatched)
            assert len(claimed) == 1
            lease = claimed[0]
            assert lease is not None
            assert lease.workspace_id == workspace_id
            connection.execute(
                text("SELECT set_config('app.workspace_id', :scope, true)"), {"scope": workspace_id}
            )
            assert connection.execute(select(Run.id)).scalars().all() == [run_id]
            connection.execute(
                text("SELECT set_config('app.workspace_id', :scope, true)"), {"scope": str(uuid4())}
            )
            assert connection.execute(select(Run.id)).all() == []
            assert leases.claim_run(sessions, run_id, "foreign-worker", workspace_id=str(uuid4())) is None
        finally:
            transaction.rollback()
    engine.dispose()
