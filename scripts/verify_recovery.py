"""Verify deletion before/after an isolated recovery drill; no source content printed."""

import argparse
from hashlib import sha256
from pathlib import Path

import httpx
from product_core.config import get_settings
from product_core.db import SessionLocal
from product_core.models import Case, Export, Source
from sqlalchemy import select


def verify(case_id, delete_now=False):
    with SessionLocal() as session:
        exports = list(session.scalars(select(Export).where(Export.case_id == case_id)))
        sources = list(session.scalars(select(Source).where(Source.case_id == case_id)))
        case = session.get(Case, case_id)
        assert case is not None
        revision = case.revision
        for export in exports:
            assert sha256(export.content.encode()).hexdigest() == export.content_hash
        root = Path(get_settings().artifact_dir).resolve()
        for source in sources:
            for relative, expected_hash in (
                (source.artifact_path, source.content_hash),
                (source.text_path, source.extraction_hash),
            ):
                if relative:
                    path = (root / relative).resolve()
                    assert path.is_relative_to(root)
                    assert sha256(path.read_bytes()).hexdigest() == expected_hash
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as client:
        assert client.post("/v1/auth/dev", json={"user_id": "researcher"}).status_code == 200
        client.headers["X-CSRF-Token"] = client.get("/v1/session").json()["csrf_token"]
        if delete_now:
            assert client.get(f"/v1/cases/{case_id}").status_code == 200
            for export in exports:
                result = client.get(f"/v1/exports/{export.id}/download")
                assert result.status_code == 200
                assert sha256(result.content).hexdigest() == export.content_hash
            for source in sources:
                result = client.get(f"/v1/sources/{source.id}/download")
                assert result.status_code == 200
                assert sha256(result.content).hexdigest() == source.content_hash
            assert client.delete(f"/v1/cases/{case_id}?expected_revision={revision}").status_code == 200
        assert client.get(f"/v1/cases/{case_id}").status_code == 404
        for export in exports:
            assert client.get(f"/v1/exports/{export.id}/download").status_code == 404
        for source in sources:
            assert client.get(f"/v1/sources/{source.id}/download").status_code == 404
    with SessionLocal() as session:
        assert session.get(Case, case_id).deleted_at is not None
    print(
        f"Deletion denied case, {len(sources)} source and {len(exports)} export downloads; tombstone verified."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--delete-now", action="store_true")
    args = parser.parse_args()
    verify(args.case_id, args.delete_now)
