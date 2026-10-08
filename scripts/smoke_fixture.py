"""Exercise an actual local API/worker/DB fixture journey; no provider calls."""

import argparse
import json
import time
from uuid import uuid4

import httpx


def check(response, expected=200):
    if response.status_code != expected:
        raise AssertionError(
            f"{response.request.method} {response.request.url.path}: HTTP {response.status_code}"
        )
    return response.json()


def login(client, user):
    check(client.post("/v1/auth/dev", json={"user_id": user}))
    client.headers["X-CSRF-Token"] = check(client.get("/v1/session"))["csrf_token"]


def smoke(base_url, keep_case=False):
    with httpx.Client(base_url=base_url, timeout=30) as client:
        check(client.get("/health/live"))
        check(client.get("/health/ready"))
        login(client, "researcher")
        case = check(
            client.post(
                "/v1/cases",
                json={
                    "title": "Synthetic operations fixture",
                    "original_claim": "Hospital A is operational in District A during September 2026.",
                },
            )
        )
        cid = case["id"]
        case = check(
            client.post(
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
                        }
                    ],
                },
            )
        )
        assert case["revision"] == 2
        assert (
            client.patch(f"/v1/cases/{cid}", json={"expected_revision": 1, "title": "stale"}).status_code
            == 409
        )
        plan = check(client.post(f"/v1/cases/{cid}/plans", json={"expected_revision": 2}))
        body = {"expected_revision": 2, "plan_id": plan["id"], "mode": "fixture"}
        headers = {"Idempotency-Key": str(uuid4())}
        run = check(client.post(f"/v1/cases/{cid}/runs", json=body, headers=headers), 202)
        assert check(client.post(f"/v1/cases/{cid}/runs", json=body, headers=headers), 202)["id"] == run["id"]
        deadline = time.monotonic() + 60
        while (
            run["state"] in {"QUEUED", "RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"}
            and time.monotonic() < deadline
        ):
            time.sleep(0.25)
            run = check(client.get(f"/v1/runs/{run['id']}"))
        assert run["state"] in {"COMPLETED", "PARTIAL"}, f"Fixture run did not complete: {run['state']}"
        case = check(client.post(f"/v1/runs/{run['id']}/integrate", json={"expected_revision": 2}))
        assert case["revision"] == 3
        evidence = case["payload"]["evidence"]
        for item in evidence:
            source = check(client.get(f"/v1/sources/{item['source_id']}"))
            anchor = item["anchor"]
            assert source["text"][anchor["start"] : anchor["end"]] == item["quote"]
        request = check(
            client.post(
                f"/v1/cases/{cid}/review-requests",
                json={
                    "expected_revision": 3,
                    "conclusion": "Synthetic fixture only; assess collected records and retain delivery-stage gaps.",
                    "citations": [item["id"] for item in evidence],
                },
            )
        )
        assert (
            client.post(
                f"/v1/review-requests/{request['id']}/decisions",
                json={"expected_revision": 3, "decision": "APPROVE", "reason": "Self review must fail"},
            ).status_code
            == 403
        )
        login(client, "editor")
        check(
            client.post(
                f"/v1/review-requests/{request['id']}/decisions",
                json={
                    "expected_revision": 3,
                    "decision": "APPROVE",
                    "reason": "Checked synthetic scope, anchors and explicit limitations",
                },
            )
        )
        export = check(client.post(f"/v1/cases/{cid}/exports", json={"revision": 3, "format": "json"}))
        original = client.get(export["download_url"])
        assert original.status_code == 200
        login(client, "researcher")
        check(
            client.patch(
                f"/v1/cases/{cid}", json={"expected_revision": 3, "title": "Synthetic operations correction"}
            )
        )
        assert client.get(export["download_url"]).content == original.content
        if not keep_case:
            check(client.delete(f"/v1/cases/{cid}?expected_revision=4"))
            assert client.get(f"/v1/cases/{cid}").status_code == 404
            assert client.get(export["download_url"]).status_code == 404
            for source in case["payload"]["sources"]:
                assert client.get(f"/v1/sources/{source['id']}/download").status_code == 404
        return {
            "fixture": True,
            "case_id": cid,
            "run_state": run["state"],
            "evidence_anchors_checked": len(evidence),
            "review_and_export_checked": True,
            "deletion_checked": not keep_case,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8008")
    parser.add_argument("--keep-case", action="store_true")
    args = parser.parse_args()
    print(json.dumps(smoke(args.base_url, args.keep_case), indent=2))
