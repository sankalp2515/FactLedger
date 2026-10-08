# [Product Name] — engineering review and proposed design amendments

8 October 2026 · Pre-implementation review · Proposed for user review

## 1. Intended outcome and current state

Build an English-first evidence investigation workspace for Indian newsroom researchers and editors checking public spending and project-delivery claims. Success means an editor can inspect the confirmed claim, exact source passages, opposing evidence, stage/date/quantity comparisons, and a reproducible case revision. Search discovers records; collected records do not certify ground reality. Human editorial conclusions remain separate from automated findings.

The workspace currently contains documentation and design artifacts only. There is no application, dependency lockfile, database, executed application test suite, deployment, or Git repository. Existing test commands and performance targets are plans, not results.

The product name is undecided. Use **[Product Name]** in new user-facing artifacts, `product_core` for the Python domain package and `product_worker` for its worker. Previous names and name-screening conclusions in older documents are superseded by the user's instruction. Naming is independent of architecture; no domain registration or purchase is needed.

Read this alongside [PRD](PRD.md), [system specification](product-system-spec.md), [agent design](agent-design.md), [use cases](use-cases.md), and [implementation plan](implementation-plan.md). This review proposes amendments; it does not represent an implemented system or an approved scope change.

## 2. Team contributions and architecture decision

| Responsibility | Review contribution |
|---|---|
| Principal architect / systems engineer | Domain boundaries, durable ownership, revision/run consistency, worker fencing |
| Backend / database architect | Explicit commands, immutable versions, tenant-safe relationships, transactions and indexes |
| AI engineer | Constrained graph, literal citations, deterministic quantities, evaluation and abstention |
| Staff full-stack / technical lead | Shared contracts, milestone dependency order, reviewable vertical increments |
| Frontend / UX / product engineer | Evidence-first workbench, scope clarification, editorial handoff, responsive states |
| Security engineer | Artifact revocation, acquisition isolation, authentication, abuse limits and source injection |
| Performance engineer | Bounded extraction, model input selection, pagination and measured workload |
| DevOps / SRE / production debugging | Queue reconstruction, lease recovery, deployment limits, backups and restore |
| QA / test automation / reviewer | Failure-oriented tests, traceability, external validation boundaries and release evidence |

Recommended approach: keep the proposed modular FastAPI API, React client, and separate Python worker. PostgreSQL is authoritative; object storage holds artifacts; Redis is disposable transport/cache. Domain functions depend on typed interfaces, with provider adapters at the edges. Avoid per-agent services, Kubernetes, a second vector database, and a national project registry in the first release.

Alternatives considered:

| Approach | Benefit | Trade-off / decision |
|---|---|---|
| Modular API + durable worker | Clear operational isolation, inspectable state, independent worker capacity | Additional queue/lease complexity is justified by long-running investigations; recommended |
| API + PostgreSQL-polled worker, no Redis | Fewer local services | Valid simplification if queue complexity obstructs delivery; would amend the existing plan, so retain Redis for now |
| Agent microservices + orchestration platform | Independent service releases | Adds distributed contracts and operations before any measured need; defer |

## 3. Findings that need resolved contracts

These are design gaps, not vulnerabilities proven in existing code.

| ID | Risk | Existing reference | Proposed resolution |
|---|---|---|---|
| R-01 | Worker results race with user edits; loading the latest expected revision can invalidate a run with its own writes | Agent design §4; system spec §§9–11 | Pin run inputs; keep progressive results run-owned; integrate through an explicit revision transaction |
| R-02 | Submission/read commands absent; immutable submitted review versus stale approval is ambiguous | System spec §10; plan Task 9 | Separate submission and decision; frozen review reads; approve only the current submitted revision |
| R-03 | Expired workers may continue committing after replacement | System spec §8; plan Task 8 | Monotonic lease generation checked in every worker write transaction |
| R-04 | Raw signed storage links cannot promise immediate access revocation | System spec §§7,10; plan Task 11 | Authenticated API download gateway with access checks on each request; keep bucket private |
| R-05 | Tenant columns and row policies alone do not prevent cross-tenant relationship references | System spec §9; plan Tasks 1–2 | Composite tenant/case/version foreign keys, explicit connection context, non-owner DB roles |
| R-06 | Ten-minute completion target conflicts with acquiring all 30 documents and many model calls | PRD §8; system spec §§3,8 | Deadline stops dispatch; qualify partial results; measure success latency separately from budget stops |
| R-07 | Dollar/token ceilings are estimates unless reservations bound provider request size | Agent design §4; plan Task 3 | Reserve bounded input/output, use dated prices, retain uncertain charges, fail readiness without cost configuration |
| R-08 | Secure URL validation and PDF limits are stated without enforcement contracts | System spec §§8,14; plan Task 5 | Pin validated connection addresses, validate redirects, isolated parser limits and adversarial tests |
| R-09 | UI canvas lacks a complete product design system and frontend read contracts | System spec §§10–11; plan Tasks 7,9 | Define tokens/states and typed read APIs; consolidate UI design before implementation |
| R-10 | Required service/beneficiary/outcome metrics lack an observation contract | PRD §6; use cases UC-04–09; system spec §14 | Add typed MetricObservation with denominator, methodology and evidence anchors |
| R-11 | User reviews a plan before starting, but the graph creates the plan after starting | PRD §7; agent design §2 | Persist a preflight plan; account for preflight model use; accept the plan when starting |

## 4. Case, run and review consistency

### Run-owned research branch

Start a run with `base_revision_id` and immutable selected claim/project versions. Claim comparisons always use those versions. Progressive sources, evidence, observations and drafts belong to that run and are inspectable without changing the case head after each node.

Integrating a completed or partial run into the draft is a compare-and-swap transaction using the current expected case revision. If its claim/project scope remains identical, validated results can be attached in a new revision. If scope changed, preserve results on the original run and return `SCOPE_CHANGED`; never relabel them as current evidence. UI offers inspection and a new scoped run. Do not implement automatic semantic merges in release 1.

Human edits create immutable versions and advance the case head. Research jobs cannot overwrite notes, overrides or conclusions. The first release permits one nonterminal investigation per case; requests to start another return `RUN_ALREADY_ACTIVE`. Workspace concurrency remains configurable. A manual source acquisition uses the same run-owned result/explicit integration rules.

### Review submission and decisions

`POST /v1/cases/{id}/review-requests` submits the current revision with expected revision, a qualified human conclusion and its citations. Store a frozen snapshot. A researcher may submit; an editor/owner may decide. Proposed safe default: the decision actor differs from the submitting actor, including owners. Local demo seeds separate researcher/editor identities.

`POST /v1/review-requests/{id}/decisions` accepts `APPROVE` or `RETURN`, reason, expected submitted revision and an idempotency key. Lock the request and case; only an OPEN request whose revision is still the current case head can receive a decision. An edit supersedes open review requests, preserving their comments/snapshots; approval returns `REVIEW_SUPERSEDED`. An existing approved revision and pack remain historical after later edits. Approval does not silently approve a new head.

`GET /v1/review-requests/{id}` always serves the frozen submitted revision and status. Review and case head are distinct concepts; UI displays both when they differ. One terminal decision per request; repeated identical idempotent decisions return the recorded result. Unresolved conclusions can be approved as qualified conclusions with visible gaps.

Reviewer trade-off: approving an older frozen submission while a newer draft exists is also coherent, but differs from the plan's explicit stale-approval test. The proposed supersession rule preserves that existing acceptance contract and avoids users confusing historical approval with the current draft. Historical approved packs remain intact under either policy.

### Lease fencing and external calls

Claiming/reclaiming a run increments a database `lease_generation`. All action commits, events, usage reconciliation and checkpoints require the matching generation, current lease owner, nonexpired lease and an undeleted case in the same transaction. A stale worker cannot commit or dispatch new work. Renewals never revive an expired generation.

Fence tokens protect database writes, not already-sent provider requests. Persist invocation identity/reservation before network calls. On unknown provider outcome, retain conservative reservation and an `OUTCOME_UNKNOWN` record; do not silently replay or release it. Recovery exposes partial work and remaining budget. Outbox rows remain redispatchable after transport loss until durable job receipt/completion is confirmed; a transport-delivered flag alone is insufficient.

## 5. Database design supplement

Text ER model:

```text
User --< Membership >-- Workspace
Workspace --< Case --< CaseRevision --< RevisionClaim >-- ClaimVersion
Case --< ProjectVersion; CaseRevision --< RevisionProject >-- ProjectVersion
Case --< InvestigationRun --< Invocation / Reservation / RunEvent / Checkpoint
InvestigationRun --< SearchBatch --< SearchResult
Case --< Source --< SourceVersion --< ExtractionVersion --< Anchor
ClaimVersion + ExtractionVersion --< EvidenceVersion
EvidenceVersion --< StageObservation / FundingObservation / MetricObservation / DerivedOperand
CaseRevision --< RevisionEvidence / RevisionObservation / RevisionNote
Case --< LineageVersion; CaseRevision --< RevisionLineage
CaseRevision --< ReviewRequest --0..1 ReviewDecision
CaseRevision + ReviewDecision? --< ExportPack --< ManifestEntry
Workspace --< Outbox / AuditEvent / DeletionRequest
```

Use separate normalized relational rows for memberships, version references, evidence, calculations and reviews. JSONB is suitable for bounded provider metadata, immutable schema-versioned snapshots and small checkpoint payloads; do not hide relationships or searchable permissions in free-form JSON.

| Table group | Keys, constraints and indexes |
|---|---|
| Users/memberships | Stable user identity unique `(issuer, subject)`; unique `(workspace_id,user_id)`; checked role enum; transactional final-owner protection |
| Cases/revisions | PK UUID; unique `(workspace_id,id)`; revision unique `(workspace_id,case_id,number)`; head references an owned revision; index library `(workspace_id,archived,updated_at,id)` |
| Claims/projects | Immutable version IDs and scope hash; composite FK to owning case; selected revision join tables include tenant/case keys |
| Runs/invocations | Composite FK to case and base revision; checked state/budget values; unique action fingerprint; partial unique nonterminal run per case; recovery index `(state,lease_expires_at)` |
| Budgets/events/checkpoints | Nonnegative Decimal costs/counts; locks enforce reservation ceilings; unique `(workspace_id,run_id,seq)`; checkpoints bound to invocation/generation |
| Sources/extractions | Source locator is not content identity; immutable byte and extraction hashes; anchors reference extraction version and physical PDF page; no public global content deduplication |
| Evidence/observations | Composite tenant/case FKs to claim, source and extraction; checked relation/stage/measure enums; numeric values use NUMERIC; indexes by claim version/source version/run |
| Reviews/exports | Request FK to frozen revision; one decision per request; pack FK to frozen revision and optional approval; immutable manifest stores schema version and artifact hashes |
| Outbox/audit/deletion | Job ID unique, due-work index, retry/receipt state; audit records actor/action/version without raw source text; deletion tombstone checked by every job |

On each tenant-bound table include a unique `(workspace_id,case_id,id)` where needed for composite foreign keys; relationships must match both tenant and case. Source/evidence/claim versions from another case cannot be linked simply because their UUID exists. Do not use canonical URL alone as a duplicate-content test; changing documents retain new versions.

Set tenant context transaction-locally for row-level policies; pooled connections must not retain a previous workspace. Workers use scoped transactions as well. Role removal is enforced on the next API/object request; dispatch and commits recheck the initiating membership and case deletion status. Revocation requests cancellation, retains already acquired records, and prevents further authorized work.

Migrations: Alembic, reviewed schema diffs, upgrade tests on fresh and previous schemas. Expand before contract changes, backfill in bounded jobs, constrain only after validation, contract after compatible rollout. Never cascade away an approved revision during an ordinary scope update. Case purge follows the explicit deletion policy, including exports.

MetricObservation: immutable ID, workspace/case/project/claim/extraction version IDs, metric kind, original expression, Decimal value, unit, denominator value/unit, population/geography, reference period, measurement method, attributed actor, evidence IDs and limitations. Initial metric kinds cover capacity, connections, service frequency, enrollment, training completions, placements, housing handover/occupancy, registered/approved/paid beneficiaries and generation. UNKNOWN or unrecognized domain metrics cannot become decisive without confirmed definitions. Observations join revision snapshots and ledger reads/overrides. Capacity is distinct from usage; offers from unique persons; installed connections from reliable service.

Finding derivation proposal: only active validated comparisons for the exact claim version participate. Support with no comparable material opposition yields SUPPORTED_BY_COLLECTED_EVIDENCE; contradiction without support yields CONTRADICTED_BY_COLLECTED_EVIDENCE; both yield MIXED_EVIDENCE; neither yields INSUFFICIENT_EVIDENCE. Material unresolved scope, denominator, attribution or coverage gaps downgrade a proposed decisive finding to insufficient unless the finding is explicitly limited to an independently verified narrower atomic claim. The researcher confirms such a narrower scope. Source counts never vote. A literal anchor proves quotation identity, not semantic entailment; semantic judgments remain model/human proposals assessed by labeled evaluations. Every finding carries decisive/opposing IDs and a checklist of missing checks.

## 6. API, identity and frontend contracts

Use REST `/v1` and generated OpenAPI TypeScript types. Commands with optimistic revisions express domain actions more clearly than arbitrary GraphQL mutations. Internal additive fields do not need a new API version; incompatible public contracts do.

Read APIs needed before the workbench: workspace/current membership, paginated cases, a case revision, confirmed claims, run status/budgets, run-owned results, evidence with comparison details, extraction excerpts around validated anchors, source versions, lineage, notes, revision history/diffs, review queue/request, and export status/download. Bind every resource to an authorized workspace/case; server-derived identity is authoritative.

Use opaque cursor pagination ordered by `(updated_at,id)` for the case library and `(seq)` for events; default 25, maximum 100. Invalid/reused idempotency keys with a different request hash return 409. Record request hashes and completed command results; document a 24-hour retention floor for mutation idempotency. Creation commands require keys where network retries could duplicate cases, sources, review requests or exports.

Errors include stable machine code, safe message, request ID and bounded field details. Add `RUN_ALREADY_ACTIVE`, `SCOPE_CHANGED`, `REVIEW_SUPERSEDED`, `INVALID_STATE`, `IDEMPOTENCY_CONFLICT`, `RATE_LIMITED`, and `CASE_DELETED`. Use 401 for invalid identity, 409 for revision/state conflicts, 422 for validation, 429 plus Retry-After for abuse limits. Use indistinguishable 404 responses for resources outside authorized tenancy to reduce identifier probing; update the plan's cross-workspace assertions accordingly.

Preflight planning: `POST /v1/cases/{id}/plans` uses confirmed scope and expected revision to persist a human-readable versioned query/evidence plan. Prefer deterministic domain templates initially. Any optional model-assisted planning reserves against an explicit preflight budget, counts toward workspace spend, and discloses usage before starting. `POST /v1/cases/{id}/runs` accepts `plan_id` and its scope hash; reject a stale plan after scope edits. Adaptation within the accepted scope and ceilings records plan revisions and rationale, without requiring approval of every query. Source/export jobs expose queued/running/completed/failed/cancelled states through authenticated job reads; they inherit workspace limits, deletion fencing, idempotency and durable receipts.

Production identity proposal: same-origin API-mediated OIDC Authorization Code flow with PKCE/state/nonce; encrypted or server-side sessions, Secure/HttpOnly/SameSite cookies, session rotation and bounded expiry. Provider tokens stay server-side. Mutations require CSRF token and Origin validation; CORS is restricted. SSE uses the authenticated same-origin session, never a token in a URL. Dev identity remains explicit, loopback-only, and impossible in production configuration. Choose the hosted issuer only when hosting is authorized; local development requires no hosted account.

Artifact downloads and PDF range reads go through the authenticated API gateway. Check current membership/deletion on every request; set private no-store response policy for sensitive artifacts. Do not deliver permanent bucket locators or bearer object links to the browser. A deletion revokes future requests immediately; already downloaded bytes cannot be recalled. Abort active streams where practical, and document the distinction.

Initial abuse-limit proposal: per actor 60 ordinary API requests/minute, 10 expensive mutations/minute, 2 live event connections/run; per workspace 2 active runs; global load-test envelope 5 active runs. These are configurable starting limits, not measured capacity. Return explicit queue/budget status rather than hidden waiting. Search cache is workspace-scoped, keyed by exact normalized engine/query/localization/date parameters; do not share sensitive query metadata between tenants.

Manual acquisition follows the 20 MB source and parser limits even outside an investigation; cap each workspace at 10 pending manual jobs and 2 active manual acquisitions initially. Suggested local storage allowance is 1 GiB/workspace, with a separate configurable cap for frozen exports; reject admission before exceeding quota. Bound HTML extracted text to 2 million characters and model input to its reserved token allowance. These initial operational choices require measurement and are not verified capacity.

Privacy disclosure at workspace setup identifies what leaves the system: search queries and localization parameters go to SerpApi; selected claim scope and relevant source passages go to the configured model provider. Exclude unrelated human notes/attachments by default. Document selected provider retention/processing terms before real confidential investigations; private membership alone does not mean data stays on the local machine.

## 7. Frontend design brief for consolidated finalization

Direction: a restrained editorial research desk. The premium quality comes from typography, clear hierarchy, precise comparisons and fast source inspection. The key story is claim → observed stage → gap → original excerpt → qualified conclusion → editor decision. Avoid decorative dashboards that make evidence harder to read.

| System | Proposed choice and rationale |
|---|---|
| Typography | Locally available system sans for navigation/data; Georgia/system serif for case title and qualified conclusion; monospace tabular numerals for quantities/IDs. Avoid an external font dependency during investigation |
| Palette | Canvas `#F6F4EF`, surface `#FFFFFF`, ink `#182B2A`, muted ink `#52615E`, border `#D9DFDA`, action `#145C4A`, focus `#1D4ED8`; warm paper and green anchor attention without political or truth-score symbolism |
| Evidence statuses | Full words + distinct icons + subtle tint; support/opposition/mixed/insufficient remain readable in grayscale; test final foreground/background pairs |
| Type scale | 12/14/16/20/28/40 px; body 16 with 1.5 line height; source paragraphs capped near 70 characters; smaller metadata never carries indispensable decisions |
| Spacing/grid | 4/8/12/16/24/32/48/64 px; desktop 12-column grid, maximum content width around 1440 px; border-driven grouping and 6–12 px radii |
| Components | Case header, scoped claim card, stage/funding tables, evidence row, citation chip, anchor reader, gap callout, run activity/budget, review panel, revision diff, conflict dialog and download control |
| Icons/illustration | One consistent locally packaged SVG icon set with text for critical actions; custom stage diagrams only when they clarify evidence; no generic AI illustrations |
| Motion | 120–180 ms hover/focus transitions; short reader reveal; no progress animation that implies certainty; reduced-motion preference disables nonessential motion |

Desktop: claim rail, central table/timeline, reader panel; editor mode foregrounds conclusion and strongest opposition. Tablet: collapsible claim rail, source reader as accessible dialog/panel. Mobile: one pane at a time, labelled navigation, stacked comparison summaries and full source view; semantic tables may scroll inside labelled regions rather than forcing page-wide overflow.

Routes: `/cases`, `/cases/new`, `/cases/:id`, `/cases/:id/runs/:runId`, `/cases/:id/revisions/:revision`, `/reviews`, `/reviews/:requestId`, `/workspace/settings`. URL query parameters preserve selected claim/tab/evidence; never carry private document text or credentials.

Server data uses a query cache with tenant/revision-specific keys; filters and pane selection stay local/URL state. SSE invalidates or updates bounded run queries by event sequence; reconnect resumes, deduplicates and refetches authoritative status on missing history. Do not optimistically approve reviews or resolve revision conflicts. Generated contracts feed feature-specific view models rather than copied domain types.

States: skeletons for initial reads; progressive results during runs; empty library with intake CTA; no-source state with manual addition; inaccessible/scanned/partial-PDF warnings; insufficient evidence with next-needed-record list; offline/reconnecting banner; provider failure with retained results; deletion/role revocation without stale cached artifacts; explicit conflict dialog showing both versions. Unknown dates stay visibly unknown.

At raw-source expiry retain the approved citation envelope: exact quote, necessary surrounding context, extraction version, physical page/character metadata and hashes. Label full-source context as expired. Model replay is available only while its complete versioned input bundle remains retained; after expiry promise excerpt-level auditability, not re-execution or identical provider output. Persistently label fixture/live mode.

Accessibility validation: semantic headings/tables, labelled inputs, complete keyboard flows, visible focus, dialog focus trap/return, useful live announcements without per-token chatter, 44 px preferred touch controls, zoom/reflow checks and reduced motion. Automated checks complement manual keyboard and screen-reader review. A consolidated visual design remains to be finalized before UI coding; the current canvas is a wireframe, not that approval.

## 8. Proposed implementation structure

```text
apps/
  api/product_core/
    domain/              # immutable value types and pure evidence/quantity rules
    application/         # case/run/review/export use cases and ports
    infrastructure/      # database, storage, search/model/fetch adapters
    presentation/        # FastAPI routes, schemas, middleware
    platform/            # settings, identity, telemetry and cross-cutting wiring
  worker/product_worker/ # graph, invocation executor, leases, dispatcher
  web/src/
    app/                 # routes, providers, shell
    features/            # cases, investigation, evidence, review, workspace
    api/                 # generated contracts and typed client
    ui/                  # tokens, accessible primitives and shared components
    assets/
tests/                   # domain, application, integration, security, recovery
eval/                    # fixtures, labeling protocol, scorer and reports
infra/                   # Compose, images, CI and deployment configuration
docs/                    # product/design, API, ADRs, setup and runbooks
```

Keep cohesive case/evidence/run modules inside each layer as they grow; do not force every operation through redundant abstract classes. The API and worker import the same package. Domain code has no HTTP, database, provider SDK or UI imports. Shared frontend primitives stay small; no global state store until cross-feature client state actually needs one.

## 9. Security, performance and recovery acceptance

| Area | Attack/failure scenario | Required implementation and evidence |
|---|---|---|
| Acquisition / SSRF — high | Redirect or DNS rebinding reaches private services | Validate every address and redirect; connect only to approved resolved addresses with TLS hostname verification, disable ambient proxy settings, reject credentials/custom ports unless explicitly supported; egress restriction; connection-level tests |
| PDF resource abuse — high | Small file decompresses into excessive CPU/memory | Restricted subprocess/container, hard memory/time limits, no network, read-only input, bounded pages/text/cells, terminate on limit; test runtime enforcement |
| Identity / authorization — high | Forged token or stale membership accesses another case | Verified issuer/audience/expiry/signature, session/CSRF tests, tenant/case composite FKs and RLS, revoke-next-request tests, separately scoped worker access |
| Sources / injection — high | Source instructs model to exfiltrate or manufacture conclusion | Data-only model input; no unrestricted tools/secrets; validate returned IDs/anchors; protect generated HTML; adversarial fixture tests |
| Downloads / XSS — high | Uploaded HTML or source script executes in app origin | Plain text/escaped excerpts, sanitized exports, private gateway, attachment disposition and nosniff; isolate any PDF preview origin/sandbox |
| Workers / concurrency — high | Replaced worker commits old evidence or purged data | Fencing, deletion tombstone, transactional action commits, late-response/crash/role-removal tests |
| Abuse / costs — high | Large runs/uploads/token inputs exhaust provider budget | Actor/workspace admission limits, bounded body/output, transactional reservations, workspace daily cost limit, worst-case token reservation and unknown-charge tests |
| Privacy — medium | Search URL, errors or telemetry reveal keys/claims | HTTP client log redaction including query strings; sanitized provider payloads; content-free metrics; no secrets or full sources in fixture exports |
| Recovery — high | Redis loss after outbox delivery loses queued work | Durable receipt reconciliation; rebuild pending invocations and expired leases; restore case, objects and pack manifest together |

Model calls select bounded relevant source passages rather than entire 30-document corpora. Extraction records text coverage separately from page coverage. CPU-bound PDF work runs outside the API event loop. Evidence tables use pagination; virtualize only after measurement and retain accessible semantics. SSE payloads contain compact references, not raw documents. Lazy-load reader/graph/revision screens.

Performance measurements: queue wait, stage duration, provider latency, time to first inspectable evidence, successful qualified-draft latency, timeout/partial rate, bytes extracted, input/output tokens, unknown charges, database query count and browser interaction latency. A run stopping at ten minutes does not prove p95 successful completion within ten minutes. Load-test the stated envelope and report misses.

## 10. Test and delivery sequence

Keep the plan's twelve increments, with the following amendments:

| Plan task | Additional acceptance evidence |
|---|---|
| 1 | Tenant/case composite references, transaction-local RLS isolation, identity/session contract, revision heads and run input policy |
| 2 | Separate extraction versions, content identity versus locators, authenticated access/revocation and retention semantics |
| 3 | Durable delivery receipts, workspace limits, unknown-charge accounting, state conflict/idempotency hash tests |
| 4–5 | Redacted search URL/payload, workspace cache isolation, pinned public connections, upload/parser runtime isolation |
| 6 | UC-01–UC-10, attribution versus endorsement, immutable corrections, literal anchors and nonoverlapping Decimal arithmetic |
| 7 | Run-owned progressive results, explicit integration conflicts, labelled partial coverage, keyboard/reader states |
| 8 | Lease generation, late worker response, cancelled/deleted case, pause race and transport rebuild tests |
| 9 | Submission/read/decision endpoints, superseded review, separate reviewer identity, role revocation and concurrent owner changes |
| 10 | Frozen manifest and serialized bytes, source retention versus approved excerpts, safe HTML and inaccessible deleted packs |
| 11 | CI, pinned dependencies/container digests, restore manifest integrity, resource-limit enforcement and measured load |
| 12 | Live evidence separated from replay; per-class quality/coverage; independent labels/pilot explicitly unmet if unavailable |

Pull generated transport contracts and a minimal accessible UI shell forward to the first source-to-anchor increment, after frontend finalization. This exposes intake/reader integration risk before the complete workbench is built; it does not defer any P0 feature or claim a reduced release is complete.

Quality metric proposal: at least 90% precision on decisive SUPPORTS/CONTRADICTS predictions, with per-class precision, coverage, abstention and uncertainty reported on stratified independent labels. Require at least 50% decisive coverage on examples independently labeled as decisively answerable; report inaccessible-source and genuinely insufficient cases separately. This is an initial acceptance target for review, not achieved accuracy. Deterministic anchor/scope invariants remain zero-tolerance regardless of pooled scores.

Before changing product code, agree the amendments, update the normative spec/plan to remove contradictions, then implement task by task with focused review. Unit tests cover domain logic; PostgreSQL integration tests cover real transactions/RLS/races; provider contract tests use sanitized fixtures; API tests cover auth/errors/idempotency; Playwright exercises researcher/editor flows; adversarial security/recovery tests inject failures; measured load tests test the deployment envelope.

Review each increment for duplicate business rules, adapter leakage, missing tenant checks, unsupported evidence inference and over-broad components. Performance and security review occur alongside implementation, not only at the end. Never call the first runnable increment the completed product.

## 11. Operations and documentation plan

Local Compose first: web/API/worker/PostgreSQL/Redis/private object storage. Rootless/non-root processes where supported; API/worker have separate least-privilege credentials; parsers have no network; only web/API ingress is public. Configuration validation fails production readiness for development identity, missing cost rates or unsafe secrets. No cloud account or paid dependency is provisioned during design.

CI: locked installs; formatting/type checks; unit/API/PostgreSQL integration tests; browser journeys; dependency and image vulnerability reports; migration verification; image builds with immutable tags. Do not introduce Kubernetes until measured capacity/availability and operational staffing justify it. Hosted IaC follows the selected provider when hosting is authorized.

Liveness checks process availability; readiness checks configuration and essential dependencies without paid calls. Metrics and structured logs carry request/run IDs and safe error codes. Alert on old queued jobs, failed leases, exhausted workspace budgets, citation failures, parser terminations and backup failure. Thresholds come from the first measured baseline.

Proposed recovery objectives for hosted review: RPO 24 hours and RTO 4 hours; these are targets, not guarantees. Back up PostgreSQL and corresponding artifacts/manifests; encrypt and test selected-case restoration. Keep a durable deletion ledger independently of the database snapshot being restored, retaining content-free tenant/case IDs through the expiry of all affected backups. Reapply its tombstones before restored data is served or jobs dispatch; restoration fails closed if the ledger is unavailable. A pre-deletion snapshot must not erase the knowledge that a case was deleted. Roll back application images only while schema is compatible; destructive schema rollback requires a reviewed recovery procedure.

Deliver README, secure environment-variable reference, clean setup guide, architecture/decision record, generated API reference, developer workflow, contribution guide, runbooks for provider failure/queue rebuild/deletion/restore, deployment guide and troubleshooting. Credentials are added locally at integration readiness; never request keys in chat.

## 12. Approval and unresolved external dependencies

Engineering can resolve the proposed contract details without assigning routine technical decisions to the user. The material user review is whether this amended full-product design reflects the intended workflow, including separate submitter/reviewer identities. No feature scope is reduced for the hackathon deadline.

The existing package requires G0 design review before implementation and G1 consolidated frontend finalization before UI implementation. The brainstorming skill likewise requires review of the written spec before implementation planning/execution. This document is the concrete pre-implementation review for those discussions; implementation has not begun.

Remaining external dependencies are provider credentials, a chosen hosted issuer/provider if public hosting is later requested, qualified independent annotators/pilot participants, and authorization for spend/publication/licenses/submission. Their absence must be disclosed rather than represented as engineering success. Branding stays [Product Name] until supplied.

## 13. Final review status

Product intent, scope and domain invariants reviewed. Proposed architecture retained with explicit consistency, security and frontend amendments. All specialist findings must be reconciled into the normative plan before execution. Code correctness, accessibility conformance, live integrations, model quality, load capacity, recovery objectives and deployment readiness remain unverified because no application exists yet.
