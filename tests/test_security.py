"""HTTP authorization/session regressions, alongside adapter SSRF and PostgreSQL RLS suites."""

import pytest
from fastapi.testclient import TestClient
from product_core import main, service
from product_core.auth import Actor
from product_core.config import Settings, get_settings
from product_core.models import Export, Membership, Source, Workspace
from pydantic import ValidationError


def identity(client):
    session = client.get("/v1/session").json()
    client.headers["X-CSRF-Token"] = session["csrf_token"]


def test_foreign_case_source_and_export_are_indistinguishable_404():
    with TestClient(main.app) as client:
        identity(client)
        local = Actor("researcher", "local-newsroom", "researcher", "Researcher")
        with service.transaction(local) as db:
            db.add(Workspace(id="foreign-workspace", name="Foreign newsroom"))
        foreign = Actor("researcher", "foreign-workspace", "researcher", "Researcher")
        case = service.create_case(foreign, {"title": "Private", "original_claim": "Private"})
        with service.transaction(foreign) as db:
            source = Source(
                workspace_id=foreign.workspace_id,
                case_id=case["id"],
                title="Private",
                url="https://example.org",
                status="AVAILABLE",
            )
            export = Export(
                workspace_id=foreign.workspace_id,
                case_id=case["id"],
                revision=1,
                format="json",
                content="private",
                content_hash="0" * 64,
            )
            db.add_all([source, export])
            db.flush()
            paths = [
                f"/v1/cases/{case['id']}",
                f"/v1/sources/{source.id}",
                f"/v1/sources/{source.id}/download",
                f"/v1/exports/{export.id}/download",
            ]
        for path in paths:
            assert client.get(path).status_code == 404


def test_foreign_origin_rejected_even_with_valid_csrf():
    with TestClient(main.app) as client:
        identity(client)
        assert (
            client.post(
                "/v1/cases",
                json={"title": "Blocked", "original_claim": "Blocked"},
                headers={"Origin": "https://attacker.example"},
            ).status_code
            == 403
        )


def test_membership_revocation_invalidates_existing_session():
    with TestClient(main.app) as client:
        identity(client)
        local = Actor("researcher", "local-newsroom", "researcher", "Researcher")
        with service.transaction(local) as db:
            db.delete(db.get(Membership, (local.workspace_id, local.id)))
        try:
            assert client.get("/v1/cases").status_code == 401
        finally:
            with service.transaction(local) as db:
                db.add(Membership(workspace_id=local.workspace_id, user_id=local.id, role="researcher"))


def test_production_rejects_local_identity(monkeypatch):
    with TestClient(main.app) as client:
        monkeypatch.setattr(get_settings(), "mode", "production")
        assert client.post("/v1/auth/dev", json={"user_id": "owner"}).status_code == 401


def test_wrong_oidc_issuer_cannot_create_session(monkeypatch):
    class Provider:
        async def authorize_access_token(self, request):
            return {"userinfo": {"iss": "https://wrong.example", "sub": "attacker"}}

    with TestClient(main.app) as client:
        monkeypatch.setattr(main, "oauth_client", lambda: Provider())
        monkeypatch.setattr(get_settings(), "mode", "production")
        monkeypatch.setattr(get_settings(), "oidc_issuer", "https://expected.example")
        assert client.get("/v1/auth/callback").status_code == 401
        assert client.get("/v1/session").status_code == 401


def test_production_configuration_fails_closed():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            mode="production",
            session_secret="local-only-development",
            database_url="sqlite:///not-production.db",
            oidc_issuer="",
            oidc_client_id="",
            public_url="http://localhost",
        )


def test_html_export_escapes_untrusted_title_and_conclusion():
    with TestClient(main.app) as client:
        identity(client)
        case = client.post(
            "/v1/cases",
            json={"title": '<img src=x onerror="alert(1)">', "original_claim": "Untrusted record"},
        ).json()
        client.post(
            f"/v1/cases/{case['id']}/review-requests",
            json={"expected_revision": 1, "conclusion": "<script>alert(1)</script>", "citations": []},
        )
        export = client.post(f"/v1/cases/{case['id']}/exports", json={"revision": 1, "format": "html"}).json()
        html = client.get(export["download_url"]).text
        assert "<script>" not in html and "<img" not in html
        assert "&lt;script&gt;" in html
