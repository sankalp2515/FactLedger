"""Real PostgreSQL lock ordering; synthetic rows are cleaned after committed interleavings."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from product_core import service
from product_core.auth import Actor, DomainError
from product_core.investigation import leases
from product_core.models import (
    Audit,
    Case,
    ReviewRequest,
    Revision,
    Run,
    RunEvent,
    Source,
    User,
    Workspace,
    now,
)
from sqlalchemy import create_engine, delete, event, select, text
from sqlalchemy.orm import sessionmaker


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL", "").startswith("postgresql"), reason="PostgreSQL integration only"
)
def test_run_command_waits_for_case_deletion_without_deadlocking(tmp_path, monkeypatch):
    engine = create_engine(os.environ["DATABASE_URL"])
    sessions = sessionmaker(engine, expire_on_commit=False)
    workspace_id, case_id, run_id = (str(uuid4()) for _ in range(3))
    actor = Actor("concurrency-researcher", workspace_id, "researcher", "Synthetic researcher")
    with sessions.begin() as db:
        db.add(Workspace(id=workspace_id, name="Synthetic concurrency regression"))
        db.flush()
        db.add(Case(id=case_id, workspace_id=workspace_id, title="Lock order", original_claim="Synthetic"))
        db.flush()
        db.add(
            Run(
                id=run_id,
                workspace_id=workspace_id,
                case_id=case_id,
                base_revision=1,
                mode="fixture",
                plan={},
                budget={},
                state="QUEUED",
                # Keep any running development worker away from this committed fixture.
                lease_expires_at=now() + timedelta(minutes=10),
            )
        )

    monkeypatch.setattr(service, "SessionLocal", sessions)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    monkeypatch.setattr(service, "artifact_root", lambda: artifacts)
    deletion_holds_case = threading.Event()
    command_requests_case = threading.Event()
    worker = threading.local()

    @event.listens_for(sessions, "after_begin")
    def runtime_role(session, transaction, connection):
        connection.execute(text("SET LOCAL ROLE evidence_app"))
        connection.execute(text("SET LOCAL lock_timeout = '8s'"))

    @event.listens_for(engine, "before_cursor_execute")
    def before_query(connection, cursor, statement, parameters, context, executemany):
        if (
            getattr(worker, "role", None) == "command"
            and "FROM cases" in statement
            and ("FOR UPDATE" in statement or "FOR NO KEY UPDATE" in statement)
        ):
            command_requests_case.set()

    @event.listens_for(engine, "after_cursor_execute")
    def after_query(connection, cursor, statement, parameters, context, executemany):
        if (
            getattr(worker, "role", None) == "delete"
            and "FROM cases" in statement
            and ("FOR UPDATE" in statement or "FOR NO KEY UPDATE" in statement)
        ):
            deletion_holds_case.set()
            assert command_requests_case.wait(5), "Run command did not attempt its case lock."

    def deleting():
        worker.role = "delete"
        return service.delete_case(actor, case_id, 1)

    def commanding():
        worker.role = "command"
        try:
            return service.control_run(actor, run_id, "cancel")
        except DomainError as exc:
            return exc

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            deletion = pool.submit(deleting)
            assert deletion_holds_case.wait(5), "Deletion did not acquire its case lock."
            command = pool.submit(commanding)
            assert deletion.result(timeout=12)["deleted"] is True
            result = command.result(timeout=12)
            assert isinstance(result, DomainError) and result.status == 404
        # Use the maintenance identity for the postcondition and cleanup.
        with engine.connect() as connection:
            assert connection.execute(select(Run.state).where(Run.id == run_id)).scalar_one() == "CANCELLED"
            assert (
                connection.execute(select(Case.deleted_at).where(Case.id == case_id)).scalar_one() is not None
            )
    finally:
        event.remove(sessions, "after_begin", runtime_role)
        with engine.begin() as connection:
            for table in (Audit, RunEvent, Run, Case):
                connection.execute(delete(table).where(table.workspace_id == workspace_id))
            connection.execute(delete(Workspace).where(Workspace.id == workspace_id))
        engine.dispose()


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL", "").startswith("postgresql"), reason="PostgreSQL integration only"
)
def test_review_decision_waits_for_new_revision_without_deadlocking(monkeypatch):
    engine = create_engine(os.environ["DATABASE_URL"])
    sessions = sessionmaker(engine, expire_on_commit=False)
    workspace_id, case_id, review_id, author_id, editor_id = (str(uuid4()) for _ in range(5))
    author = Actor(author_id, workspace_id, "researcher", "Synthetic author")
    editor = Actor(editor_id, workspace_id, "editor", "Synthetic editor")
    with sessions.begin() as db:
        db.add_all(
            [
                Workspace(id=workspace_id, name="Synthetic review concurrency regression"),
                User(id=author_id, name="Synthetic author"),
                User(id=editor_id, name="Synthetic editor"),
            ]
        )
        db.flush()
        db.add(Case(id=case_id, workspace_id=workspace_id, title="Review locks", original_claim="Synthetic"))
        db.flush()
        payload = service.empty_payload()
        db.add_all(
            [
                Revision(workspace_id=workspace_id, case_id=case_id, number=1, payload=payload),
                ReviewRequest(
                    id=review_id,
                    workspace_id=workspace_id,
                    case_id=case_id,
                    revision=1,
                    submitted_by=author_id,
                    conclusion="Synthetic conclusion",
                    citations=[],
                    snapshot=payload,
                ),
            ]
        )
    monkeypatch.setattr(service, "SessionLocal", sessions)
    revision_holds_case = threading.Event()
    reviewer_requests_case = threading.Event()
    worker = threading.local()

    @event.listens_for(sessions, "after_begin")
    def runtime_role(session, transaction, connection):
        connection.execute(text("SET LOCAL ROLE evidence_app"))
        connection.execute(text("SET LOCAL lock_timeout = '8s'"))

    @event.listens_for(engine, "before_cursor_execute")
    def before_query(connection, cursor, statement, parameters, context, executemany):
        if (
            getattr(worker, "role", None) == "reviewer"
            and "FROM cases" in statement
            and ("FOR UPDATE" in statement or "FOR NO KEY UPDATE" in statement)
        ):
            reviewer_requests_case.set()

    @event.listens_for(engine, "after_cursor_execute")
    def after_query(connection, cursor, statement, parameters, context, executemany):
        if (
            getattr(worker, "role", None) == "revision"
            and "FROM cases" in statement
            and ("FOR UPDATE" in statement or "FOR NO KEY UPDATE" in statement)
        ):
            revision_holds_case.set()
            assert reviewer_requests_case.wait(5), "Reviewer did not request the case lock."

    def revising():
        worker.role = "revision"
        return service.add_note(
            author,
            case_id,
            {
                "expected_revision": 1,
                "text": "Synthetic concurrency note",
                "attribution": "Concurrency test",
                "evidence_ids": [],
            },
        )

    def deciding():
        worker.role = "reviewer"
        try:
            return service.decide_review(
                editor,
                review_id,
                {
                    "expected_revision": 1,
                    "decision": "APPROVE",
                    "reason": "Synthetic review",
                },
            )
        except DomainError as exc:
            return exc

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            revision = pool.submit(revising)
            assert revision_holds_case.wait(5), "Revision did not acquire its case lock."
            decision = pool.submit(deciding)
            assert revision.result(timeout=12)["revision"] == 2
            result = decision.result(timeout=12)
            assert isinstance(result, DomainError) and result.code == "REVIEW_SUPERSEDED"
        with engine.connect() as connection:
            assert (
                connection.execute(
                    select(ReviewRequest.status).where(ReviewRequest.id == review_id)
                ).scalar_one()
                == "SUPERSEDED"
            )
            assert connection.execute(select(Case.revision).where(Case.id == case_id)).scalar_one() == 2
    finally:
        event.remove(sessions, "after_begin", runtime_role)
        with engine.begin() as connection:
            for table in (Audit, ReviewRequest, Revision, Case):
                connection.execute(delete(table).where(table.workspace_id == workspace_id))
            connection.execute(delete(Workspace).where(Workspace.id == workspace_id))
            connection.execute(delete(User).where(User.id.in_([author_id, editor_id])))
        engine.dispose()


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL", "").startswith("postgresql"), reason="PostgreSQL integration only"
)
def test_worker_source_and_event_inserts_complete_while_api_locks_case(monkeypatch):
    engine = create_engine(os.environ["DATABASE_URL"])
    sessions = sessionmaker(engine, expire_on_commit=False)
    workspace_id, case_id, run_id, source_id = (str(uuid4()) for _ in range(4))
    actor = Actor("concurrency-researcher", workspace_id, "researcher", "Synthetic researcher")
    with sessions.begin() as db:
        db.add(Workspace(id=workspace_id, name="Synthetic FK concurrency regression"))
        db.flush()
        db.add(
            Case(id=case_id, workspace_id=workspace_id, title="Worker FK locks", original_claim="Synthetic")
        )
        db.flush()
        db.add(
            Run(
                id=run_id,
                workspace_id=workspace_id,
                case_id=case_id,
                base_revision=1,
                mode="fixture",
                plan={},
                budget={},
                state="QUEUED",
                lease_expires_at=now() + timedelta(minutes=10),
            )
        )
    monkeypatch.setattr(service, "SessionLocal", sessions)
    worker = threading.local()
    worker_holds_run = threading.Event()
    api_holds_case = threading.Event()

    @event.listens_for(sessions, "after_begin")
    def runtime_role(session, transaction, connection):
        connection.execute(text("SET LOCAL ROLE evidence_app"))
        connection.execute(text("SET LOCAL lock_timeout = '8s'"))

    lease = leases.claim_run(sessions, run_id, "fk-regression-worker", workspace_id=workspace_id)
    assert lease is not None

    @event.listens_for(engine, "after_cursor_execute")
    def synchronize_locks(connection, cursor, statement, parameters, context, executemany):
        if (
            getattr(worker, "role", None) == "worker"
            and "FROM runs" in statement
            and "FOR UPDATE" in statement
        ):
            worker_holds_run.set()
            assert api_holds_case.wait(5), "API did not lock its case."
        if (
            getattr(worker, "role", None) == "api"
            and "FROM cases" in statement
            and ("FOR UPDATE" in statement or "FOR NO KEY UPDATE" in statement)
        ):
            api_holds_case.set()

    def preserving_source():
        worker.role = "worker"

        def write_source_and_event(db, run):
            db.add(
                Source(
                    id=source_id,
                    workspace_id=workspace_id,
                    case_id=case_id,
                    run_id=run_id,
                    url="fixture://concurrency",
                    title="Synthetic preserved source",
                    status="AVAILABLE",
                )
            )
            leases.event(db, run, "SOURCE_ACQUIRED", {"source_id": source_id})
            return source_id

        return leases.update_run(sessions, lease, write_source_and_event)

    def reading_run():
        worker.role = "api"
        with service.transaction(actor) as db:
            return service.run_detail(db, service.run_for(db, actor, run_id))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            preservation = pool.submit(preserving_source)
            assert worker_holds_run.wait(5), "Worker did not acquire its run lock."
            reading = pool.submit(reading_run)
            assert preservation.result(timeout=12) == source_id
            result = reading.result(timeout=12)
            assert result["id"] == run_id
            assert any(item["type"] == "SOURCE_ACQUIRED" for item in result["events"])
        with engine.connect() as connection:
            assert (
                connection.execute(select(Source.id).where(Source.id == source_id)).scalar_one() == source_id
            )
    finally:
        event.remove(sessions, "after_begin", runtime_role)
        with engine.begin() as connection:
            for table in (Source, RunEvent, Run, Case):
                connection.execute(delete(table).where(table.workspace_id == workspace_id))
            connection.execute(delete(Workspace).where(Workspace.id == workspace_id))
        engine.dispose()
