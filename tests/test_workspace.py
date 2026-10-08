from fastapi.testclient import TestClient
from product_core.main import app


def login(client, user="researcher"):
    client.post("/v1/auth/dev", json={"user_id": user})
    session = client.get("/v1/session").json()
    client.headers["X-CSRF-Token"] = session["csrf_token"]
    return session


def create(client):
    return client.post(
        "/v1/cases",
        json={"title": "Hospital service check", "original_claim": "The 200-bed hospital is operational."},
    ).json()


def test_scope_revision_conflict_and_read_preservation():
    with TestClient(app) as client:
        login(client)
        case = create(client)
        cid = case["id"]
        r = client.post(
            f"/v1/cases/{cid}/scope",
            json={
                "expected_revision": 1,
                "claims": [
                    {
                        "text": "Hospital operational",
                        "subject": "Hospital A",
                        "geography": "District A",
                        "period": "2026-09",
                        "stage": "OPERATIONAL",
                    }
                ],
            },
        )
        assert r.status_code == 200
        assert r.json()["revision"] == 2
        conflict = client.patch(f"/v1/cases/{cid}", json={"expected_revision": 1, "title": "overwrite"})
        assert conflict.status_code == 409
        assert client.get(f"/v1/cases/{cid}?revision=1").json()["title"] == "Hospital service check"


def test_csrf_and_editor_authority():
    with TestClient(app) as client:
        login(client)
        case = create(client)
        client.headers.pop("X-CSRF-Token")
        assert client.post("/v1/cases", json={"title": "Bad", "original_claim": "Bad"}).status_code == 403
        login(client)
        request = client.post(
            f"/v1/cases/{case['id']}/review-requests",
            json={
                "expected_revision": 1,
                "conclusion": "Insufficient evidence; operation is not established.",
                "citations": [],
            },
        )
        assert request.status_code == 200
        rid = request.json()["id"]
        assert (
            client.post(
                f"/v1/review-requests/{rid}/decisions",
                json={"expected_revision": 1, "decision": "APPROVE", "reason": "Checked"},
            ).status_code
            == 403
        )
        login(client, "editor")
        assert (
            client.post(
                f"/v1/review-requests/{rid}/decisions",
                json={
                    "expected_revision": 1,
                    "decision": "APPROVE",
                    "reason": "Reviewed uncertainty and scope",
                },
            ).status_code
            == 200
        )


def test_edit_supersedes_review_and_exports_immutable():
    with TestClient(app) as client:
        login(client)
        case = create(client)
        cid = case["id"]
        rid = client.post(
            f"/v1/cases/{cid}/review-requests",
            json={"expected_revision": 1, "conclusion": "Unknown.", "citations": []},
        ).json()["id"]
        export = client.post(f"/v1/cases/{cid}/exports", json={"revision": 1, "format": "html"}).json()
        original = client.get(export["download_url"]).content
        client.patch(f"/v1/cases/{cid}", json={"expected_revision": 1, "title": "Changed title"})
        login(client, "editor")
        assert (
            client.post(
                f"/v1/review-requests/{rid}/decisions",
                json={"expected_revision": 1, "decision": "APPROVE", "reason": "Checked"},
            ).status_code
            == 409
        )
        assert client.get(export["download_url"]).content == original


def test_run_idempotency_and_deletion_access_revocation():
    with TestClient(app) as client:
        login(client)
        case = create(client)
        cid = case["id"]
        case = client.post(
            f"/v1/cases/{cid}/scope",
            json={
                "expected_revision": 1,
                "claims": [
                    {
                        "text": "Hospital operational",
                        "subject": "Hospital",
                        "geography": "District A",
                        "period": "2026",
                        "stage": "OPERATIONAL",
                    }
                ],
            },
        ).json()
        plan = client.post(f"/v1/cases/{cid}/plans", json={"expected_revision": 2}).json()
        body = {"expected_revision": 2, "plan_id": plan["id"], "mode": "fixture"}
        headers = {"Idempotency-Key": "stable-run-request"}
        a = client.post(f"/v1/cases/{cid}/runs", json=body, headers=headers)
        b = client.post(f"/v1/cases/{cid}/runs", json=body, headers=headers)
        assert a.status_code == 202
        assert a.json()["id"] == b.json()["id"]
        export = client.post(f"/v1/cases/{cid}/exports", json={"revision": 2, "format": "json"}).json()
        assert client.delete(f"/v1/cases/{cid}?expected_revision=2").status_code == 200
        assert client.get(export["download_url"]).status_code == 404
        assert client.get(f"/v1/cases/{cid}").status_code == 404


def test_last_owner_and_role_permissions():
    with TestClient(app) as client:
        login(client, "owner")
        workspace = client.get("/v1/session").json()["workspace"]["id"]
        assert (
            client.patch(f"/v1/workspaces/{workspace}/members/owner", json={"role": "researcher"}).status_code
            == 409
        )
        login(client)
        assert (
            client.post(
                f"/v1/workspaces/{workspace}/members", json={"user_id": "editor", "role": "owner"}
            ).status_code
            == 403
        )


def test_uploaded_pdf_has_immutable_source_reader_and_authenticated_download():
    import io

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    pdf = io.BytesIO()
    writer.write(pdf)
    with TestClient(app) as client:
        login(client)
        case = create(client)
        result = client.post(
            f"/v1/cases/{case['id']}/uploads",
            data={"expected_revision": "1"},
            files={"file": ("source.pdf", pdf.getvalue(), "application/pdf")},
        )
        assert result.status_code == 200
        source = result.json()["payload"]["sources"][0]
        assert "User upload" in source["metadata"]["provenance"]
        assert client.get(f"/v1/sources/{source['id']}/download").content == pdf.getvalue()
        client.delete(f"/v1/cases/{case['id']}?expected_revision=2")
        assert client.get(f"/v1/sources/{source['id']}/download").status_code == 404


def test_daily_workspace_admission_includes_requested_budget(monkeypatch):
    from product_core.config import get_settings

    monkeypatch.setattr(get_settings(), "workspace_daily_usd", 0.1)
    with TestClient(app) as client:
        login(client)
        case = create(client)
        cid = case["id"]
        client.post(
            f"/v1/cases/{cid}/scope",
            json={
                "expected_revision": 1,
                "claims": [
                    {
                        "text": "Hospital operational",
                        "subject": "Hospital",
                        "geography": "District A",
                        "period": "2026",
                        "stage": "OPERATIONAL",
                    }
                ],
            },
        )
        plan = client.post(f"/v1/cases/{cid}/plans", json={"expected_revision": 2}).json()
        result = client.post(
            f"/v1/cases/{cid}/runs", json={"expected_revision": 2, "plan_id": plan["id"], "mode": "live"}
        )
        assert result.status_code == 429
        assert result.json()["code"] == "BUDGET_EXCEEDED"


def test_decided_review_cannot_change_conclusion_at_same_revision():
    with TestClient(app) as client:
        login(client)
        case = create(client)
        url = f"/v1/cases/{case['id']}/review-requests"
        body = {"expected_revision": 1, "conclusion": "Unknown: no operational record.", "citations": []}
        review = client.post(url, json=body).json()
        draft = client.post(f"/v1/cases/{case['id']}/exports", json={"revision": 1, "format": "json"}).json()
        assert client.get(draft["download_url"]).json()["conclusion"] == body["conclusion"]
        login(client, "editor")
        assert (
            client.post(
                f"/v1/review-requests/{review['id']}/decisions",
                json={"expected_revision": 1, "decision": "APPROVE", "reason": "Uncertainty checked"},
            ).status_code
            == 200
        )
        login(client)
        body["conclusion"] = "Operational, without further records."
        assert client.post(url, json=body).status_code == 409
        client.patch(f"/v1/cases/{case['id']}", json={"expected_revision": 1, "title": "New draft"})
        historical = client.get(f"/v1/cases/{case['id']}?revision=1").json()
        assert historical["state"] == "APPROVED"


def test_deterministic_scope_gaps_cannot_be_overridden():
    import pytest
    from product_core import service
    from product_core.auth import Actor, DomainError, seed_development
    from product_core.db import init_db
    from product_core.models import Evidence, Source

    init_db()
    seed_development()
    identity = Actor("researcher", "local-newsroom", "researcher", "Researcher")
    case = service.create_case(identity, {"title": "Guard", "original_claim": "Operational"})
    with service.transaction(identity) as db:
        current = service.case_for(db, identity, case["id"])
        payload = service.snapshot(db, current)
        item = {
            "id": "guarded-evidence",
            "quote": "The hospital was inaugurated.",
            "anchor": {"start": 0, "end": 29},
            "relation": "INCOMPARABLE",
            "comparison": {"gaps": ["STAGE_MISMATCH"], "quantity": {"comparable": True}},
        }
        payload["evidence"].append(item)
        # Snapshot and relational evidence ownership are both required by the command.
        source = Source(
            workspace_id=identity.workspace_id,
            case_id=current.id,
            url="https://example.org",
            title="Test record",
            status="EXTRACTED",
        )
        db.add(source)
        db.flush()
        db.add(
            Evidence(
                id=item["id"],
                workspace_id=identity.workspace_id,
                case_id=current.id,
                claim_id="claim",
                source_id=source.id,
                relation=item["relation"],
                quote=item["quote"],
                anchor={"start": 0, "end": 35},
                comparison=item["comparison"],
            )
        )
        service.persist_revision(db, identity, current, payload, "test.fixture")
    with pytest.raises(DomainError) as rejected:
        service.override_evidence(
            identity,
            item["id"],
            {
                "expected_revision": 2,
                "relation": "SUPPORTS",
                "reason": "Human thinks opening means operation",
            },
        )
    assert rejected.value.code == "INVALID_SCOPE"
    with service.transaction(identity) as db:
        current = service.case_for(db, identity, case["id"])
        payload = service.snapshot(db, current)
        payload["evidence"][0]["comparison"] = {"gaps": [], "quantity": None}
        service.persist_revision(db, identity, current, payload, "test.stage-only")
    assert (
        service.override_evidence(
            identity,
            item["id"],
            {
                "expected_revision": 3,
                "relation": "CONTEXT",
                "reason": "Stage-only record retained as context",
            },
        )["revision"]
        == 4
    )

    assert (
        service.override_evidence(
            identity,
            item["id"],
            {
                "expected_revision": 4,
                "relation": "SUPPORTS",
                "reason": "Comparable stage-only evidence reclassified",
            },
        )["revision"]
        == 5
    )


def test_malformed_integrate_command_is_validation_error():
    with TestClient(app, raise_server_exceptions=False) as client:
        login(client)
        result = client.post("/v1/runs/not-a-run/integrate", json={"expected_revision": "bad"})
        assert result.status_code == 422
        assert result.json()["code"] == "INVALID_SCOPE"
