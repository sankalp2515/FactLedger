"""Explicit retention maintenance. Dry-run by default; never deletes outside artifact root."""

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from product_core.config import get_settings
from product_core.db import SessionLocal
from product_core.models import (
    Audit,
    Case,
    Evidence,
    Export,
    Plan,
    ReviewRequest,
    Revision,
    Run,
    RunEvent,
    Source,
)
from sqlalchemy import delete, select


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def bounded_unlink(value: str, root: Path, apply: bool):
    if not value:
        return
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    target = path.resolve()
    if not target.is_relative_to(root) or target == root:
        raise ValueError("Refusing artifact path outside configured root")
    if apply:
        target.unlink(missing_ok=True)


def cleanup(apply=False, now=None):
    now = now or datetime.now(UTC)
    root = Path(get_settings().artifact_dir).resolve()
    report = {
        "source_artifacts_expired": 0,
        "deleted_cases_purged": 0,
        "audit_logs_expired": 0,
        "apply": apply,
    }
    with SessionLocal.begin() as session:
        sources = list(session.scalars(select(Source)))
        protected_paths = {
            value
            for source in sources
            if utc(source.created_at) >= now - timedelta(days=90)
            for value in (source.artifact_path, source.text_path)
            if value
        }
        for source in sources:
            if utc(source.created_at) < now - timedelta(days=90) and (
                source.artifact_path or source.text_path
            ):
                for value in (source.artifact_path, source.text_path):
                    if value not in protected_paths:
                        bounded_unlink(value, root, apply)
                if apply:
                    source.artifact_path = ""
                    source.text_path = ""
                    source.status = "EXPIRED"
                report["source_artifacts_expired"] += 1
        for case in session.scalars(select(Case).where(Case.deleted_at.is_not(None))):
            if utc(case.deleted_at) >= now - timedelta(days=7):
                continue
            for source in session.scalars(
                select(Source).where(Source.case_id == case.id, Source.workspace_id == case.workspace_id)
            ):
                bounded_unlink(source.artifact_path, root, apply)
                bounded_unlink(source.text_path, root, apply)
            if apply:
                for model in (Evidence, RunEvent, ReviewRequest, Export, Plan, Revision, Source, Run):
                    session.execute(
                        delete(model).where(model.case_id == case.id, model.workspace_id == case.workspace_id)
                    )
                # Keep content-free Case tombstone, delete content and disable restoration.
                case.title = "[purged]"
                case.original_claim = ""
                case.tags = []
                case.assignee_id = None
                case.state = "PURGED"
            report["deleted_cases_purged"] += 1
        old_audits = list(session.scalars(select(Audit).where(Audit.created_at < now - timedelta(days=30))))
        report["audit_logs_expired"] = len(old_audits)
        if apply:
            for item in old_audits:
                session.delete(item)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Execute the reported retention policy")
    args = parser.parse_args()
    import json

    print(json.dumps(cleanup(args.apply), indent=2))
