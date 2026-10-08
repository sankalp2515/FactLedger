# API and development workflow

The running contract is `GET /openapi.json`. Typed FastAPI schemas are the authoritative field/validation reference. APIs use REST under `/v1`; immutable resources and explicit commands suit the revision/review workflow without a GraphQL server. The browser uses same-origin cookie sessions and sends `X-CSRF-Token` from `GET /v1/session` on mutations. Production sign-in begins at `/v1/auth/login`; only local development exposes `/v1/auth/dev`.

| Workflow | Routes |
|---|---|
| Cases | GET/POST `/v1/cases`; GET/PATCH/DELETE `/v1/cases/{id}`; POST restore |
| Scope and plans | POST `/v1/cases/{id}/scope`; POST `/v1/cases/{id}/plans` |
| Research | POST `/v1/cases/{id}/runs`; GET `/v1/runs/{id}`; POST pause/resume/cancel/integrate; GET events (SSE) |
| Sources | POST case sources or multipart uploads; GET `/v1/sources/{id}` and authenticated download |
| Corrections | PATCH `/v1/evidence/{id}/relation` and `/v1/lineage/{id}`; POST case ledger-overrides/notes |
| Review | POST case review-requests; GET `/v1/review-requests` and `{id}`; POST `{id}/decisions` |
| History/export | GET case revisions/diff; POST case exports; GET `/v1/exports/{id}/download` |
| Membership | GET/POST workspace members; PATCH member (`role: removed` revokes access); owner authorization |

Case mutations carry `expected_revision`; stale updates return409. Starting research sends `plan_id`, `mode: fixture|live`, optional bounded `budget`, and `Idempotency-Key`. Retrying the same key/inputs returns the original run; different inputs return409. Results remain run-owned until integration at the expected case revision. `Last-Event-ID` replays durable ordered SSE events. Case listing uses bounded cursor pagination. Revisions bind claim scope, notes, sources and analysis; stored read-only claim metadata must not be submitted as input.

Maximum run envelope:12 searches,30 document attempts,3 rounds,60000 tokens,600 seconds,$2 configured estimate. Workspace admission allows two active investigations and checks the UTC daily allowance. Quote offsets refer to preserved extraction text, with physical PDF page metadata where available. A model proposal never grants editorial authority. Unresolved deterministic gaps cannot be upgraded to decisive relations through a human override.

Review submission freezes the revision and human conclusion/citations. Each revision has one review submission; editing the case advances its revision before resubmission. A different editor/owner decides. Exports preserve the selected revision and approved status only when that revision's review was approved. JSON/Markdown/HTML are supported; content hashes establish byte identity, not authenticity.

Errors have `{code,message,request_id,details}`. Common codes: AUTH_REQUIRED401, FORBIDDEN403, NOT_FOUND404, REVISION_CONFLICT/REVIEW_SUPERSEDED/INVALID_STATE409, INVALID_SCOPE422, RATE_LIMITED/BUDGET_EXCEEDED/STORAGE_LIMIT_EXCEEDED429. Provider failures and exhausted bounds can produce PARTIAL with preserved useful records. Unknown invocation outcomes retain conservative budget reservations. Never reset them merely to retry a paid action.

## Environment and setup

Use the root README and `.env.example`; preserve existing `.env`. SerpApi plus the selected Groq/NVIDIA provider enable live runs. `LLM_PROVIDER`, `LLM_MODEL`, provider accounting rates, workspace daily/storage limits, and maximum run duration are server configuration. Cost estimates depend on configured rates. Production also needs PostgreSQL, private SESSION_SECRET, exact OIDC issuer/client/workspace, HTTPS PUBLIC_URL and ALLOWED_HOSTS. See the production runbook for maintenance-only identity provisioning and bounded tenant-scoped worker dispatch. No credentials belong in frontend configuration or screenshots.

Use feature-sized changes and meaningful regressions for authorization, immutability, comparison, budgets and worker recovery. Run backend and PostgreSQL evaluation suites in separate processes, frontend typecheck/lint/tests/build, Ruff and migration drift checks. CI performs these without publishing. Database changes require an Alembic migration and an actual PostgreSQL check. Domain comparisons do not perform network I/O; infrastructure adapters cannot make editorial decisions. Use synthetic fixture mode for reproducible tests and label it visibly.

Troubleshooting: inspect `/health/live` and `/health/ready`; ensure the separate worker is running for queued jobs; use visible run events for acquisition/provider failures; verify the selected model is available to the account; use bounded PDF ranges and recognize scanned PDFs have no OCR. If8000 is occupied, Compose defaults to8008 and preserves other applications. For changes/recovery, follow the operations and backup/restore runbooks instead of deleting volumes or resetting job checkpoints.
