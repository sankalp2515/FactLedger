"""Opt-in paid, local-only real-record journey. Keeps its case for manual inspection."""

import argparse
import json
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from smoke_fixture import check, login

CLAIM = "The Union Cabinet approved PM-Surya Ghar: Muft Bijli Yojana in February 2024."
SOURCE = "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2010130&lang=2&reg=48"


SCENARIOS = {
    "approval": {"text": CLAIM, "period": "2024-02", "stage": "APPROVED"},
    "delivery-target": {
        "text": "PM-Surya Ghar delivered rooftop solar installations to 10 million households in India in February 2024.",
        "period": "2024-02",
        "stage": "OPERATIONAL",
        "measure": "CONNECTIONS",
        "value": "10000000",
        "unit": "households",
    },
    "earlier-period": {
        "text": "The Union Cabinet approved PM-Surya Ghar: Muft Bijli Yojana in February 2023.",
        "period": "2023-02",
        "stage": "APPROVED",
    },
}


def smoke(base_url, max_usd, output, search_only=False, scenario="approval"):
    scoped = SCENARIOS[scenario]
    claim_text = scoped["text"]
    if urlparse(base_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("This development-role smoke test only supports localhost.")
    with httpx.Client(base_url=base_url, timeout=45) as client:
        check(client.get("/health/ready"))
        login(client, "researcher")
        case = check(
            client.post(
                "/v1/cases",
                json={
                    "title": f"Live search QA: {scenario} / PM-Surya Ghar",
                    "original_claim": claim_text,
                },
            )
        )
        cid = case["id"]
        case = check(
            client.post(
                f"/v1/cases/{cid}/scope",
                json={
                    "expected_revision": case["revision"],
                    "claims": [
                        {
                            **scoped,
                            "subject": "PM-Surya Ghar: Muft Bijli Yojana",
                            "geography": "India",
                        }
                    ],
                },
            )
        )
        # Optional manual attachment is never presented as search-discovered evidence.
        manual_source_attached = False
        if not search_only:
            response = client.post(
                f"/v1/cases/{cid}/sources", json={"expected_revision": case["revision"], "url": SOURCE}
            )
            manual_source_attached = response.status_code == 200
            if manual_source_attached:
                case = check(response)
            elif response.status_code != 422:
                check(response)
        revision = case["revision"]
        plan = check(client.post(f"/v1/cases/{cid}/plans", json={"expected_revision": revision}))
        budget = {
            "searches": 2,
            "documents": 6 if search_only else 4,
            "rounds": 1,
            "tokens": 60000,
            "seconds": 180,
            "usd": max_usd,
        }
        body = {"expected_revision": revision, "plan_id": plan["id"], "mode": "live", "budget": budget}
        headers = {"Idempotency-Key": str(uuid4())}
        run = check(client.post(f"/v1/cases/{cid}/runs", json=body, headers=headers), 202)
        assert check(client.post(f"/v1/cases/{cid}/runs", json=body, headers=headers), 202)["id"] == run["id"]
        deadline = time.monotonic() + 210
        while (
            run["state"] in {"QUEUED", "RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"}
            and time.monotonic() < deadline
        ):
            time.sleep(1)
            run = check(client.get(f"/v1/runs/{run['id']}"))
        assert run["state"] in {"COMPLETED", "PARTIAL"}, (
            f"Run stopped in {run['state']}; case {cid} retained."
        )
        case = check(client.post(f"/v1/runs/{run['id']}/integrate", json={"expected_revision": revision}))
        evidence = case["payload"]["evidence"]
        downloads = 0
        for item in evidence:
            source = check(client.get(f"/v1/sources/{item['source_id']}"))
            anchor = item["anchor"]
            assert source["text"][anchor["start"] : anchor["end"]] == item["quote"]
        for source in case["payload"]["sources"]:
            if source.get("content_hash"):
                response = client.get(f"/v1/sources/{source['id']}/download")
                assert response.status_code == 200
                assert sha256(response.content).hexdigest() == source["content_hash"]
                downloads += 1
        # A qualified limitation is valid even when a bounded run collects no decisive evidence.
        conclusion = (
            "This local QA review describes collected records only. Approval, targets, dates and beneficiary delivery must be distinguished. "
            + case["payload"]["conclusion"]
            + " Unresolved gaps and bounded search coverage remain part of this pack."
        )
        request = check(
            client.post(
                f"/v1/cases/{cid}/review-requests",
                json={
                    "expected_revision": case["revision"],
                    "conclusion": conclusion,
                    "citations": [item["id"] for item in evidence],
                },
            )
        )
        decision = {
            "expected_revision": case["revision"],
            "decision": "APPROVE",
            "reason": "AI-operated local QA role simulation: literal anchors, preserved hashes, scope and limitations checked; not an independent human adjudication.",
        }
        assert client.post(f"/v1/review-requests/{request['id']}/decisions", json=decision).status_code == 403
        login(client, "editor")
        check(client.post(f"/v1/review-requests/{request['id']}/decisions", json=decision))
        export = check(
            client.post(f"/v1/cases/{cid}/exports", json={"revision": case["revision"], "format": "json"})
        )
        pack_response = client.get(export["download_url"])
        assert pack_response.status_code == 200
        assert sha256(pack_response.content).hexdigest() == export["sha256"]
        pack = pack_response.json()
        manifest = pack.pop("manifest")
        assert (
            sha256(json.dumps(pack, sort_keys=True, default=str).encode()).hexdigest()
            == manifest["payload_sha256"]
        )
        assert manifest["source_hashes"] == {s["id"]: s.get("content_hash", "") for s in pack["sources"]}
        costs = run["costs"]
        assert abs(sum(row["usd"] for row in costs["providers"].values()) - costs["total_usd"]) < 0.000001
        report = {
            "provider_errors": [
                e["payload"].get("error") for e in run["events"] if e["type"] == "PROVIDER_ERROR"
            ],
            "tested_at": datetime.now(UTC).isoformat(),
            "case_id": cid,
            "run_id": run["id"],
            "case_url": f"{base_url}/cases/{cid}",
            "claim": claim_text,
            "scenario": scenario,
            "search_only": search_only,
            "quality_expectation": "SUPPORTED_BY_COLLECTED_EVIDENCE"
            if scenario == "approval"
            else "No supported delivery or earlier-period finding",
            "quality_expectation_met": (
                any(
                    f["finding"] == "SUPPORTED_BY_COLLECTED_EVIDENCE"
                    for f in run["results"].get("findings", [])
                )
                if scenario == "approval"
                else all(
                    f["finding"] != "SUPPORTED_BY_COLLECTED_EVIDENCE"
                    for f in run["results"].get("findings", [])
                )
            ),
            "acquired_sources": [
                {
                    "url": source.get("url"),
                    "status": source.get("status"),
                    "manual": source.get("manual", False),
                    "sha256": source.get("content_hash"),
                }
                for source in case["payload"]["sources"]
            ],
            "mode": "live",
            "manual_source_attached": manual_source_attached,
            "state": run["state"],
            "error": run.get("error"),
            "budget": budget,
            "usage": run["usage"],
            "costs": costs,
            "findings": run["results"].get("findings", []),
            "literal_anchors_checked": len(evidence),
            "source_download_hashes_checked": downloads,
            "idempotency_checked": True,
            "self_approval_denied": True,
            "review_and_export_checked": True,
            "export_manifest_checked": True,
            "reviewer_simulation": "Both local development roles operated by the AI test runner; not independent human review.",
            "export_sha256": sha256(pack_response.content).hexdigest(),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        output.with_suffix(".pack.json").write_bytes(pack_response.content)
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", required=True, help="Explicitly permit real provider calls"
    )
    parser.add_argument(
        "--search-only", action="store_true", help="Use SerpApi discovery without manually attaching a source"
    )
    parser.add_argument("--scenario", choices=SCENARIOS, default="approval")
    parser.add_argument("--base-url", default="http://127.0.0.1:8008")
    parser.add_argument("--max-usd", type=float, default=0.25)
    parser.add_argument("--output", type=Path, default=Path(".execution/live-walkthrough-report.json"))
    args = parser.parse_args()
    if not 0 < args.max_usd <= 2:
        parser.error("--max-usd must be greater than 0 and at most 2 (configured-rate estimate)")
    print(
        json.dumps(smoke(args.base_url, args.max_usd, args.output, args.search_only, args.scenario), indent=2)
    )
