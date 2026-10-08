from fastapi.testclient import TestClient
from product_core.investigation.executor import execute_run
from product_core.main import app


def test_api_created_fixture_run_executes_then_explicitly_integrates():
    with TestClient(app) as client:
        client.post("/v1/auth/dev", json={"user_id": "researcher"})
        session = client.get("/v1/session").json()
        client.headers["X-CSRF-Token"] = session["csrf_token"]
        case = client.post(
            "/v1/cases", json={"title": "Worker integration", "original_claim": "Hospital A is operational."}
        ).json()
        cid = case["id"]
        scoped = client.post(
            f"/v1/cases/{cid}/scope",
            json={
                "expected_revision": 1,
                "claims": [
                    {
                        "text": "Hospital A is operational.",
                        "subject": "Hospital A",
                        "geography": "District A",
                        "period": "2026-09",
                        "stage": "OPERATIONAL",
                        "measure": "CAPACITY",
                        "value": "200",
                        "unit": "beds",
                        "attribution": "Synthetic public authority",
                    }
                ],
            },
        )
        assert scoped.status_code == 200
        plan = client.post(f"/v1/cases/{cid}/plans", json={"expected_revision": 2}).json()
        response = client.post(
            f"/v1/cases/{cid}/runs",
            json={"expected_revision": 2, "plan_id": plan["id"], "mode": "fixture"},
            headers={"Idempotency-Key": "integration-" + cid},
        )
        assert response.status_code == 202
        run_id = response.json()["id"]
        execute_run(run_id)
        run = client.get(f"/v1/runs/{run_id}").json()
        assert run["state"] == "COMPLETED"
        assert len(run["results"]["evidence"]) == 1
        assert run["results"]["evidence"][0]["relation"] == "CONTEXT"
        assert client.get(f"/v1/cases/{cid}").json()["revision"] == 2
        integrated = client.post(f"/v1/runs/{run_id}/integrate", json={"expected_revision": 2})
        assert integrated.status_code == 200
        assert integrated.json()["revision"] == 3
        assert integrated.json()["payload"]["sources"][0]["metadata"]["synthetic"] is True
        assert client.get(f"/v1/cases/{cid}?revision=2").json()["payload"]["evidence"] == []
