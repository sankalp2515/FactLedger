# [Product Name] — evidence investigation workspace

A local-first newsroom workspace for checking public-project claims against preserved sources. Researchers confirm claim scope, inspect search plans and evidence anchors, review gaps, and submit immutable revisions for editorial review. Automated findings describe collected evidence; they do not certify ground reality.

The implemented release, measured checks, live-provider proof and remaining release gates are recorded in [implementation status](docs/implementation-status.md). See the [API/development guide](docs/api-guide.md) and [contribution workflow](CONTRIBUTING.md).

## Local setup (PowerShell)

Requires Docker Desktop with Linux containers, Python 3.12 and Node 22/pnpm 11 for development. Existing `.env` is preserved.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env locally: add provider keys and a random SESSION_SECRET. Never print or commit it.
docker compose -f infra/compose.yml up --build -d
Invoke-RestMethod http://127.0.0.1:8008/health/live
Invoke-RestMethod http://127.0.0.1:8008/health/ready
```

Open http://127.0.0.1:8008 (override with APP_PORT in .env). API and PostgreSQL bind loopback. The multi-stage image builds the typed React client, installs Python wheels, and runs API/worker as UID 10001. PostgreSQL 16 is authoritative; API and worker share a private local artifact volume including the independent deletion ledger. The worker polls durable runs; no Redis or MinIO account is needed. Development identities are for local use. Fixture investigations are synthetic and explicitly labelled. Live runs require SerpApi plus the selected model provider and outbound public HTTPS access; credentials stay on the server.

For editable development:

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -e '.[dev]'
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m uvicorn product_core.main:app --host 127.0.0.1 --port 8000
# In separate PowerShell terminals:
.venv/Scripts/python -m product_core.worker
pnpm --dir apps/web install --frozen-lockfile
pnpm --dir apps/web dev --host 127.0.0.1
```

```powershell
.venv/Scripts/python -m pytest tests -q
.venv/Scripts/python -m pytest eval/tests -q
.venv/Scripts/python -m ruff check apps/api tests scripts eval migrations
pnpm --dir apps/web exec tsc --noEmit
pnpm --dir apps/web lint
pnpm --dir apps/web test
pnpm --dir apps/web build
```

Verification status is recorded in [local operations](docs/runbooks/local-operations.md), not inferred from these commands. Hosted deployment needs OIDC, TLS, a private database, provider budget configuration and the [production checklist](docs/runbooks/production.md). [Backup and recovery](docs/runbooks/backup-restore.md) covers tombstone replay and retention. Never use `docker compose down -v` when you intend to retain cases.

The [evaluation protocol](eval/README.md) distinguishes synthetic UC-01–10 regression data from independent adjudication. [Submission readiness](docs/submission-readiness.md) keeps engineering evidence, customer validation and public-release authority separate. The product name and public license remain undecided. No public repository, demo publication or contest submission is implied by local setup.
