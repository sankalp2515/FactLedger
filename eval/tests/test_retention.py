import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from product_core.db import Base
from product_core.models import Case, Source, Workspace
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

spec = importlib.util.spec_from_file_location(
    "cleanup", Path(__file__).parents[2] / "scripts/cleanup_retention.py"
)
cleanup_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup_module)


def test_retention_dryrun_apply_and_bounded_paths(tmp_path, monkeypatch):
    import pytest

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(engine)
    root = tmp_path / "artifacts"
    root.mkdir()
    raw = root / "raw"
    raw.write_bytes(b"synthetic")
    now = datetime.now(UTC)
    with session_factory.begin() as session:
        session.add(Workspace(id="w", name="Synthetic"))
        session.flush()
        session.add(
            Case(
                id="c",
                workspace_id="w",
                title="Private title",
                original_claim="Private claim",
                deleted_at=now - timedelta(days=8),
            )
        )
        session.flush()
        session.add(
            Source(
                id="s",
                workspace_id="w",
                case_id="c",
                url="https://example.test",
                title="Synthetic",
                status="ACQUIRED",
                artifact_path="raw",
                text_path="",
                created_at=now - timedelta(days=91),
            )
        )
    monkeypatch.setattr(cleanup_module, "SessionLocal", session_factory)
    monkeypatch.setattr(cleanup_module, "get_settings", lambda: SimpleNamespace(artifact_dir=str(root)))
    assert cleanup_module.cleanup(False, now)["deleted_cases_purged"] == 1
    assert raw.exists()
    with session_factory() as session:
        assert session.get(Case, "c").original_claim == "Private claim"
    with pytest.raises(ValueError):
        cleanup_module.bounded_unlink("../outside", root.resolve(), True)
    cleanup_module.cleanup(True, now)
    assert not raw.exists()
    with session_factory() as session:
        assert session.get(Case, "c").state == "PURGED"
        assert session.get(Case, "c").original_claim == ""
        assert session.scalars(select(Source)).all() == []


def test_raw_expiry_keeps_file_referenced_by_recent_source(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(engine)
    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "shared").write_bytes(b"synthetic")
    now = datetime.now(UTC)
    with session_factory.begin() as session:
        session.add(Workspace(id="w", name="Synthetic"))
        session.flush()
        session.add(Case(id="c", workspace_id="w", title="Active", original_claim="Synthetic"))
        session.flush()
        for identity, days in [("old", 91), ("recent", 1)]:
            session.add(
                Source(
                    id=identity,
                    workspace_id="w",
                    case_id="c",
                    url="https://example.test",
                    title="Synthetic",
                    status="ACQUIRED",
                    artifact_path="shared",
                    created_at=now - timedelta(days=days),
                )
            )
    monkeypatch.setattr(cleanup_module, "SessionLocal", session_factory)
    monkeypatch.setattr(cleanup_module, "get_settings", lambda: SimpleNamespace(artifact_dir=str(root)))
    cleanup_module.cleanup(True, now)
    assert (root / "shared").exists()
    with session_factory() as session:
        assert session.get(Source, "old").status == "EXPIRED"
        assert session.get(Source, "recent").artifact_path == "shared"
