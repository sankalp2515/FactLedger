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
