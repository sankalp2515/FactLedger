"""Small measured local PostgreSQL admission/read smoke; no paid providers.

This is a concurrency regression, not a production capacity claim.
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from statistics import quantiles

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8008")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        session = client.get("/v1/session").json()
        if session.get("mode") != "development":
            raise SystemExit("This synthetic load smoke requires local development mode.")
        client.headers["X-CSRF-Token"] = session["csrf_token"]
        cases = []
        timings = []
        try:
            for number in range(5):
                response = client.post(
                    "/v1/cases",
                    json={"title": f"Concurrency smoke {number}", "original_claim": "Hospital A operational"},
                )
                response.raise_for_status()
                cid = response.json()["id"]
                cases.append(cid)
                client.post(
                    f"/v1/cases/{cid}/scope",
                    json={
                        "expected_revision": 1,
                        "claims": [
                            {
                                "text": "Hospital A operational",
                                "subject": "Hospital A",
                                "geography": "District A",
                                "period": "2026-09",
                                "stage": "OPERATIONAL",
                            }
                        ],
                    },
                ).raise_for_status()
            plans = [
                client.post(f"/v1/cases/{cid}/plans", json={"expected_revision": 2}).json() for cid in cases
            ]

            def start(pair):
                cid, plan = pair
                tick = time.perf_counter()
                response = client.post(
                    f"/v1/cases/{cid}/runs",
                    json={"expected_revision": 2, "plan_id": plan["id"], "mode": "fixture"},
                )
                timings.append((time.perf_counter() - tick) * 1000)
                assert response.status_code in {202, 429}, response.status_code
                return response.status_code

            with ThreadPoolExecutor(max_workers=5) as pool:
                statuses = list(pool.map(start, zip(cases, plans, strict=True)))

                def read(_):
                    tick = time.perf_counter()
                    client.get(f"/v1/cases/{cases[0]}").raise_for_status()
                    timings.append((time.perf_counter() - tick) * 1000)

                list(pool.map(read, range(25)))
            print(
                json.dumps(
                    {
                        "requests": len(timings),
                        "concurrency": 5,
                        "start_statuses": statuses,
                        "p50_ms": round(quantiles(timings, n=100)[49], 1),
                        "p95_ms": round(quantiles(timings, n=100)[94], 1),
                        "max_ms": round(max(timings), 1),
                        "scope": "local synthetic admission/read smoke",
                    }
                )
            )
        finally:
            for cid in cases:
                client.delete(f"/v1/cases/{cid}?expected_revision=2").raise_for_status()


if __name__ == "__main__":
    main()
