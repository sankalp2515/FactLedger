# Local operations

The Compose stack uses PostgreSQL 16, a Python API and a separate durable polling worker. API/worker share `/data/artifacts`; `/data/deletion-ledger.jsonl` is outside source artifacts. Server image UID/GID is 10001. Default published ports bind 127.0.0.1. `.env` is read server-side and must not be printed using `docker compose config`, container inspect environment dumps, debug pages or logs.

## Run and inspect

From the repository root: `docker compose up --build -d`. Docker Compose 2.24+ reads the root include, builds the frontend into the server image, waits for database readiness, runs Alembic to head, and starts API/worker after migration success. Optional `.env` permits fixture mode without keys. `/health/live` checks process liveness; `/health/ready` checks dependencies and configuration. `docker compose ps` shows container status. `docker compose logs --tail 100 api worker` shows content-free JSON request/job outcomes. Logs rotate at 10 MB × 3 per service, not a guaranteed 30-day archive; durable audit/run events are separate PostgreSQL records. Do not share query/source content or credentials in diagnostics. See the [manual and cost guide](../manual-testing.md).

Stop with `docker compose -f infra/compose.yml stop`; resume with `start`. Rebuild after code changes with `up --build -d`. A worker restart must reclaim only expired leases and preserve generation fencing; inspect run events/checkpoints for recovery, never manually reset budgets or mark unknown provider calls successful. Pause/cancel use the product commands. Cancelled external requests can still incur provider charges.

## Verification record

On 8 October 2026, Compose configuration, nonroot multi-stage image build, PostgreSQL migration/metadata check, API liveness/readiness and a full HTTP fixture researcher/editor workflow passed. The workflow exercised a worker-completed run, idempotent start, integration, literal source anchor, stale revision rejection, independent editor approval, frozen export after correction, and case/source/export deletion denial. Ten operations/evaluation tests pass against the real PostgreSQL stack, including RLS, retention and manually provisioned OIDC identity membership. The scoring implementation began with a missing-module RED check before implementation.

An isolated restore drill on a separate project passed: restore an older case/artifact/export snapshot, reapply an independently later deletion ledger, verify unchanged private raw/text/export hashes and all authenticated downloads denied, and verify UID10001 can append the restored ledger. Only synthetic data was used. Live SerpApi/model quality, production OIDC login and independent expert/customer evaluation remain separate gates. The primary Compose API binds 127.0.0.1:8008 because another application already occupied 8000; that application was preserved. Editable Python/Vite development uses 8000 by default.

## Retention

Default policy: raw sources 90 days, content-free logs 30 days, deleted-case recoverable grace 7 days, backups expire within 30 days. Minimal approved excerpts remain until case deletion. Retention is an operator policy and must be enabled explicitly using the retention script; elapsed time alone does not remove artifacts. Backups can contain previously deleted content until expiry, so access controls and independent deletion-ledger replay apply to every restore. No automatic public publication occurs.

Retention command: `docker compose -f infra/compose.yml run --rm worker python /app/scripts/cleanup_retention.py` reports work without deleting. Add `--apply` to execute the documented policy. Run under a privileged maintenance identity for production, offline if recovery is in progress. Do not delete the independent ledger as part of artifact retention.

## Observed operations checks (8 October 2026)

`docker compose -f infra/compose.yml config --quiet` succeeded and PostgreSQL 16 became healthy on 127.0.0.1:5432. Alembic upgrade to initial schema plus tenant policies and `alembic check` succeeded with no model drift. Policies were exercised under a non-owner role with missing scope, two workspaces and forbidden cross-workspace write. Backup/restore PowerShell scripts passed parser validation and the actual isolated restore drill. Fresh-stack migration/API/worker/UI startup succeeded. Use `python scripts/smoke_fixture.py --base-url http://127.0.0.1:8008` to repeat the synthetic API journey; it creates and deletes its own synthetic case. Rebuild after final source changes to package the current code.
