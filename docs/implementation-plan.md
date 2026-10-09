# FactLedger Implementation Plan

> **Historical planning document:** the user subsequently authorized implementation. The shipped design uses PostgreSQL polling and private local artifacts instead of the original Redis/S3/LangGraph stack proposed below. Consult [implementation status](implementation-status.md) and [release readiness](release-readiness.md) for current behavior, checks and outstanding deployment gates. Original review-only instructions describe the earlier planning phase.

> **Planning history:** this plan was reviewed before implementation and the release has since been implemented and verified. Its task checkboxes and proposed commands are historical planning detail, not the current delivery checklist. Use [submission checklist](submission-checklist.md) for remaining release work.

> **8 October proposed amendments:** Product name remains **FactLedger**; use `product_core` and `product_worker` instead of prior brand-derived package paths. [Engineering review](engineering-review.md) §§4–6 define the revised correctness/API/data contracts; §10 adds required acceptance evidence to Tasks 1–12 and moves generated contracts/minimal UI shell to the first source-to-anchor increment after frontend finalization. These explicit amendments supersede conflicting earlier plan details, including signed-link tests (test authenticated download revocation), cross-workspace status (indistinguishable 404), missing review submission/read commands, and progressive case-head mutation (use run-owned results and explicit integration). Include MetricObservation in the shared contracts, migration, ledger and UC-04–09 tests. The historical task checkboxes below are not a current delivery status; implementation is recorded in implementation status and release readiness. Reconcile task-level files/interfaces under these contracts during approved implementation planning; do not execute the original conflicting steps.

**Goal:** Deliver a durable evidence investigation workspace for newsroom researchers and editors.

**Architecture:** Modular FastAPI backend and separate checkpointed Python worker, with React UI. PostgreSQL owns cases, evidence, run state and reviews; object storage owns document artifacts. SerpApi supplies search discovery and a model adapter supplies inspectable evidence judgments.

**Implemented stack:** React/TypeScript, FastAPI/Pydantic, PostgreSQL durable polling, private artifact volume, HTTPX, HTML extraction, pypdf + pdfplumber. Redis, S3 and LangGraph below were early proposals and are not dependencies of the shipped local release.

**Spec:** [PRD.md](PRD.md), [product-system-spec.md](product-system-spec.md), [agent-design.md](agent-design.md), [use-cases.md](use-cases.md). Read these and the research record before execution. PRD defines scope; technical spec defines contracts.

## Global constraints

- Primary first-release language: English. Unknown dates and source independence stay unknown.
- HTTPS public sources only; 20 MB streaming limit, 20-second fetch timeout, 100 extracted PDF pages per document per run, redirects revalidated.
- Default run ceilings: 3 claims, 12 uncached search-call attempts, 30 documents, 3 rounds, 60,000 billed input/output model tokens, 10 minutes, USD 2 estimated cost.
- Default worker concurrency: 4 acquisitions, 2 search calls, 2 model calls. At most 2 transient retry attempts, charged to budgets.
- PostgreSQL and persisted outbox are authoritative; Redis must be recoverable. Worker lease is 60 seconds.
- Every decisive evidence relation requires valid anchored source content and comparable scope.
- Every case mutation requires expected_revision. Review approvals and exports bind immutable revisions.
- No numerical truth confidence; automated findings and human conclusions are separate.
- No API credentials in browser, logged queries, stored search payloads or exports.
- Checkboxes below retain planning history; current delivery evidence is recorded in implementation status and release readiness.

## Review focus

1. Articles quoting a false claim: validate attribution separately from endorsement (Task 6).
2. Stage/date/unit mismatches: do not misclassify as contradiction (Task 6).
3. Similar articles: label inferred dependence as possible, not proven copying (Task 7).
4. Concurrent evidence edits during review/export: immutable snapshot and revision conflict (Tasks 9–10).
5. Worker/provider/network failure after partial work: preserve evidence and resume without duplicate cost or jobs (Tasks 3, 8, 11).

## Proposed file map

`apps/api/product_core/` contains `cases/`, `runs/`, `search/`, `acquisition/`, `evidence/`, `review/`, `reports/`, and `platform/`. Each module contains typed contracts, domain service and adapter/routes only as needed. `apps/worker/product_worker/` contains graph/lease/job dispatch and imports the shared backend package. `apps/web/src/features/` contains `cases/`, `investigation/`, `evidence/`, and `review/`; API client/generated contracts live in `apps/web/src/api/`. Tests mirror these boundaries under `tests/`; `eval/` contains datasets and scoring. Deployment files live in `infra/`; operator documentation in `docs/runbooks/`.

Shared contracts in `apps/api/product_core/contracts.py`: ClaimScope, ClaimVersion, SearchRequest, SearchBatch, SourceRef, SourceVersion, Evidence, EvidenceSet, RunBudget, RunEvent, CaseRevision, ReviewDecision, ExportPack, ProjectRef, StageObservation, FundingObservation, DerivedQuantity. Values/enum semantics are copied from spec sections 6–10. UUIDs and workspace_id occur on tenant-bound records. Do not generate disconnected copies of these types in worker code.

## Task 1 — Durable cases and workspace identity

**Files:** `apps/api/product_core/contracts.py`, `cases/{models,service,routes}.py`, `platform/{auth,db,settings}.py`, `migrations/0001_cases.py`, `tests/cases/test_cases.py`, `tests/platform/test_auth.py`.

**Consumes:** spec data model and ClaimScope. **Produces:** `CaseService.create(workspace_id, actor_id, title, original_claim) -> CaseRevision`; `CaseService.set_scope(case_id, expected_revision, claims: list[ClaimScope], actor_id) -> CaseRevision`; verified `ActorContext` used by routes.

- [ ] Write tests: create returns revision 1; scope update returns 2; stale revision yields REVISION_CONFLICT; cross-workspace access yields FORBIDDEN; expired/wrong-audience tokens fail; production cannot use development identity.
- [ ] Run `pytest tests/cases tests/platform/test_auth.py -q`; confirm missing contracts/services fail.
- [ ] Implement schema/migration, memberships/roles, OIDC validation, transactional case updates, row policies with non-owner role and optimistic locks. Fold dependency manifests and initial API container setup into this task.
- [ ] Run those tests against PostgreSQL; verify scope changes invalidate affected analysis references.
- [ ] Commit this independently reviewable case foundation when executing in a Git repository.

## Task 2 — Artifact storage and source versions

**Files:** `acquisition/models.py`, `platform/storage.py`, `migrations/0002_sources.py`, `tests/acquisition/test_versions.py`.

**Produces:** `ArtifactStore.put(workspace_id, case_id, data: bytes, media_type: str) -> ArtifactRef`; `SourceRepository.persist(ref: SourceRef, content: bytes, extraction: str, metadata: dict) -> SourceVersion`.

- [ ] Write tests: same bytes retain hash identity; changed bytes create a new version; extraction offsets refer to one stable extraction; foreign workspace cannot resolve artifact; user locator cannot change storage key.
- [ ] Run `pytest tests/acquisition/test_versions.py -q`; confirm expected failure.
- [ ] Implement object adapter, artifact references/hashes and immutable version records; add local MinIO container configuration.
- [ ] Verify tests, artifact round trip and access control; commit.

## Task 3 — Runs, outbox, budgets and events

**Files:** `runs/{models,service,budget,events,routes}.py`, `platform/outbox.py`, `migrations/0003_runs.py`, `apps/worker/product_worker/jobs.py`, `tests/runs/test_runs.py`.

**Produces:** `RunService.start(case_id, expected_revision, claim_ids, budget: RunBudget, idempotency_key, actor_id) -> InvestigationRun`; `BudgetService.reserve(run_id, estimate: UsageEstimate) -> Reservation`; `EventStore.append(run_id, type, payload) -> RunEvent` and `replay(run_id, after_seq) -> list[RunEvent]`.

- [ ] Test duplicate start returns one run; run and outbox rollback together; concurrent reservations cannot exceed caps; SSE reconnect replays ordered events; duplicate delivery cannot create a second job; Redis loss preserves pending work.
- [ ] Run `pytest tests/runs/test_runs.py -q`; confirm fail before implementation.
- [ ] Implement transactions, outbox dispatcher, budget reservations/reconciliation and cancellation endpoint using the spec limits. Add Redis configuration here.
- [ ] Verify tests and queue-rebuild exercise; commit.

## Task 4 — SerpApi discovery adapter

**Files:** `search/{contracts,serpapi,normalize,cache}.py`, `tests/search/test_serpapi.py`, `tests/fixtures/search/`.

**Produces:** `SearchGateway.search(request: SearchRequest) -> SearchBatch`. Request includes engine, query, hl/gl, time constraints, source preference and run reservation. Batch includes raw artifact ID, normalized results, execution time, provider search ID when present and charged usage.

- [ ] Test Search, News and Scholar shapes, missing dates, empty results, malformed payload, 429, auth failure, cache parameter isolation and redacted API key.
- [ ] Run `pytest tests/search -q`; confirm fail.
- [ ] Implement HTTPS API calls, exact-parameter caching, normalization, provider errors and spec retry rules; use current official engine docs, not invented fields. Scholar is optional per plan need.
- [ ] Verify fixture tests; when credentials are available run `pytest tests/integration/test_serpapi_live.py -m live -q` with one bounded call per engine. Skip with an explicit reason when absent; never assert live verification from fixture success.
- [ ] Commit.

## Task 5 — Public source/PDF acquisition

**Files:** `acquisition/{fetch,extract,anchors,service,routes}.py`, `tests/acquisition/test_fetch.py`, `tests/acquisition/test_extract.py`.

**Produces:** `AcquisitionGateway.acquire(ref: SourceRef, page_ranges: list[PageRange] | None = None) -> SourceVersion`; `AnchorValidator.resolve(source_version, anchor) -> str`. User PDF uploads follow the same acquisition path and access checks.

- [ ] Test redirect to loopback, private IPv6, DNS changes, streaming oversize, content-type mismatch, PDF extraction request over 100 pages; a 459-page PDF with explicit 20-page range is accepted without claiming full coverage, script sanitization, scanned PDF/unavailable handling and exact quote/table anchors.
- [ ] Run `pytest tests/acquisition -q`; confirm relevant failures.
- [ ] Implement public address validation at connection and redirect, bounded retrieval, extraction and PDF anchoring; save access failure as a source record rather than fake evidence. No bypass or credentials for source sites.
- [ ] Verify tests including real public fixture PDFs and extraction preview; commit.

Manual notes and attachments also use source ownership/access checks. Record attribution and distinguish uploaded user material from externally retrieved evidence; upload is never automatically proof of authenticity.

## Task 6 — Claim comparison and quote validation

**Files:** `evidence/{compare,analyze,validate,findings}.py`, `platform/models.py`, `tests/evidence/test_relations.py`.

**Produces:** `EvidenceAnalyzer.analyze(claim: ClaimVersion, source: SourceVersion) -> EvidenceSet`; `EvidenceValidator.validate(evidence: Evidence, claim, source) -> ValidationResult`; `FindingService.derive(claim, validated_evidence) -> Finding`.

- [ ] Test model-invented quote rejects; snippet-only evidence cannot produce decisive finding; date/unit/stage mismatch yields incomparable; attribution is not endorsement; no evidence yields insufficient; material opposition survives final synthesis; claim-version changes invalidate evidence.
- [ ] Run `pytest tests/evidence/test_relations.py -q`; confirm failures.
- [ ] Implement structured model output through configurable provider adapter; deterministic quote/scope validation; typed relation/finding states and prompt/model version recording. Retry malformed output within budget; otherwise abstain.
- [ ] Verify deterministic tests with fake model responses; run labeled evaluation in Task 12 before claims of quality; commit.

### Task 6 domain extension — stage/funding ledger (required, same test cycle)

**Files:** apps/api/product_core/evidence/{ledger,quantities}.py; tests/evidence/test_delivery_ledger.py; tests/evidence/test_quantities.py; migrations/0004_delivery_ledger.py.

**Consumes:** validated EvidenceSet, ProjectRef and ClaimVersion. **Produces:** LedgerService.derive(claim: ClaimVersion, project: ProjectRef, evidence: EvidenceSet) -> DeliveryLedger; QuantityNormalizer.normalize(expression: str, currency: str, period: str) -> NormalizedQuantity; LedgerService.override(observation_id, expected_revision, corrected_fields, reason, actor_id) -> CaseRevision. DeliveryLedger is the aggregate of StageObservation[], FundingObservation[], DerivedQuantity[] and Gap[] defined in shared contracts. API GET /cases/{id}/ledger and POST /cases/{id}/ledger-overrides use these services and tenant/revision checks.

- [ ] Write test_inauguration_does_not_establish_operation, test_allocated_not_expended, test_crore_lakh_conversion_decimal, test_wrong_district_not_merged, test_unknown_event_date_not_publication_date, test_overlap_not_summed, test_source_anchor_required, test_old_observation_immutable. Assert ₹500 crore = ₹5,000 million only with compatible measure/period; reject MW vs MWh comparison. Map UC-01–UC-10 to replayable fixtures.
- [ ] Run pytest tests/evidence/test_delivery_ledger.py tests/evidence/test_quantities.py -q; verify meaningful failures before implementing.
- [ ] Implement enums/observations and deterministic Decimal conversions from PRD section 6. LLM proposals pass quote/scope validation first; no monotonic-stage inference or unsupported override.
- [ ] Run ledger/quantity/evidence suites; assert independent funding measures, stage gaps and preserved source IDs; commit this increment separately if it merits its own review.

## Task 7 — Source lineage and research workbench

**Files:** `evidence/{lineage,notes,routes}.py`, `apps/web/src/features/evidence/{Workbench,SourceReader,LineageView,Timeline}.tsx`, `apps/web/src/api/client.ts`, `tests/evidence/test_lineage.py`, `apps/web/tests/evidence.spec.ts`.

**Produces:** table-first stage timeline, funding comparison, anchor-linked observation inspector; `LineageService.suggest(sources: list[SourceVersion]) -> list[LineageEdge]`; `EvidenceService.override(evidence_id, expected_revision, relation, reason, actor_id) -> CaseRevision`.

- [ ] Test identical hash grouping, explicit attribution dependency, similarity-only possible link, unknown independence, corrected lineage history and workspace isolation. Browser test: select claim → open evidence → exact quote visible → override with reason creates revision.
- [ ] Run `pytest tests/evidence/test_lineage.py -q` and `pnpm --dir apps/web test`; confirm fail.
- [ ] Implement families/edges and correction audit; implement default table, anchored reader, optional graph and date timeline. Fold web scaffold and generated API contracts into this task.
- [ ] Verify keyboard access and label-based relation meaning; commit.

## Task 8 — Checkpointed adaptive investigation

**Files:** `apps/worker/product_worker/{graph,executor,leases}.py`, `runs/checkpoints.py`, `tests/worker/test_graph.py`.

**Produces:** `RunExecutor.execute(run_id: UUID) -> RunOutcome`; `RunExecutor.resume(run_id: UUID) -> RunOutcome`. Consumes search/acquisition/evidence interfaces without UI or provider-specific graph logic.

- [ ] Test missing primary source creates primary query; repeated reporting triggers original-source search; incomparable evidence triggers scoped follow-up; three-round/call/token/time limits stop with partial evidence; checkpoint recovery avoids redispatching completed calls; cancellation preserves acquired evidence.
- [ ] Run `pytest tests/worker -q`; confirm fail.
- [ ] Implement typed graph state, leases/heartbeat, per-stage checkpoints, idempotent invocation records, bounded next-query decisions and durable RunEvents. Unknown call outcome is recorded, not retried silently as free work.
- [ ] Verify worker-kill/restart and budget race exercises; commit.

Add `/pause` and `/resume` commands: pause only at safe checkpoint after active calls settle; resume only PAUSED state, preserving scope and remaining budget. Test elapsed RUNNING time excludes pauses; failed/completed/cancelled runs require a new run.

## Task 9 — Product intake and editorial review

**Files:** `review/{models,service,routes}.py`, `apps/web/src/features/cases/{Library,Intake,ScopeEditor}.tsx`, `apps/web/src/features/investigation/{Plan,Progress}.tsx`, `apps/web/src/features/review/{Queue,Review}.tsx`, `tests/review/test_decisions.py`, `apps/web/tests/journeys.spec.ts`.

**Produces:** `ReviewService.submit(case_id, expected_revision, actor_id) -> ReviewRequest`; `ReviewService.decide(decision: ReviewDecision) -> ReviewRecord`. Role checks: researchers submit; editors/owners approve or return. Decision binds frozen submitted revision.

- [ ] Test researcher cannot approve; edit during review creates newer draft and stale approval conflicts; return preserves comments; approved revision remains after new changes. Browser tests cover intake, claim confirmation, budget view, cancellation, insufficient evidence and editor handoff.
- [ ] Run `pytest tests/review -q` and `pnpm --dir apps/web test`; confirm fail.
- [ ] Implement roles/review records and full flows; source addition and follow-up use the earlier commands. Case lifecycle and run lifecycle remain separate.
- [ ] Add owner membership controls (existing verified users only), case title/tag/assignee/archive controls, attributed human notes/attachments and human lineage corrections. Test final-owner protection, role removal, correction audit and library pagination/filtering; no external invite is sent.
- [ ] Verify complete journeys and WCAG keyboard/focus checks; commit.

## Task 10 — Frozen evidence packs and correction flow

**Files:** `reports/{service,manifest,markdown,html,json_export}.py`, `cases/diff.py`, `apps/web/src/features/cases/RevisionDiff.tsx`, `tests/reports/test_packs.py`.

**Produces:** `ReportService.export(case_id, revision_id, format) -> ExportPack`; `RevisionService.diff(case_id, old_revision, new_revision) -> RevisionDiff`.

- [ ] Test every substantive assertion resolves; generated HTML escapes source content; draft label is visible; negative/mixed evidence included; changed source cannot alter old export; correction references old revision; unauthorized artifacts are excluded.
- [ ] Run `pytest tests/reports -q`; confirm fail.
- [ ] Implement self-contained excerpts/citations/query metadata and hash manifest; downloadable md/html/json and UI revision comparison. Export content cannot execute embedded source scripts.
- [ ] Open and inspect example packs; verify no unresolved citations or mutation; commit.

## Task 11 — Operational release and recovery

**Files:** `infra/{compose,api.Dockerfile,worker.Dockerfile,web.Dockerfile}`, `platform/{telemetry,retention}.py`, `docs/runbooks/{local,hosted,recovery,retention}.md`, `tests/integration/test_recovery.py`.

**Produces:** reproducible local stack, production configuration contract, restore/retention jobs, license/dependency inventory and readiness checks.

- [ ] Test invalid provider config fails readiness; API restart preserves case; Redis loss rebuilds jobs; worker failure resumes; cross-tenant signed link fails; retention removes expired source artifacts while approved excerpts remain; restore recreates a selected approved case and pack.
- [ ] Run `pytest tests/integration/test_recovery.py -q`; confirm fail.
- [ ] Inventory direct/transitive dependency and container licenses, notices and known vulnerabilities; evaluate MinIO/Redis distribution obligations and compatible pinned versions before public release. Do not assume all components are permissively licensed. Swap the ArtifactStore adapter to local filesystem/S3-compatible service if license/distribution needs require it; no commercial license is purchased automatically.
- [ ] Implement Compose, health checks, configuration redaction, bounded content-free logs, backup/restore and documented deletion/retention semantics. Hosted deployment remains a separately approved action.
- [ ] Implement case deletion scheduling: immediately deny access and cancel jobs; allow owner recovery within 7 days; purge active artifacts after 7 days and backups within 30 days. Test jobs cannot resurrect deleted-case evidence, expired retention removes artifacts/embeddings, and approved packs keep cited excerpts only until case deletion.
- [ ] Run full test suite and documented 5-concurrent-run load exercise; compare latency/cost to spec targets, record misses without claiming pass; commit.

## Task 12 — Evidence quality and user validation release gate

**Files:** `eval/{cases.jsonl,labels.jsonl,score.py,protocol.md}`, `tests/integration/test_live_case.py`, `docs/validation-results.md`, project `README.md`.

**Produces:** quality scorecard and pilot results; reproducible public local setup and functioning demo description.

- [ ] Engineering prepares public-attributed fixtures plus synthetic adversarial cases; qualified independent participants label/adjudicate 100 evidence pairs when available. Self-generated/self-reviewed labels are not represented as independent human validation. User is not assigned annotation work. Record sampling, class balance and coverage, not only a pooled accuracy.
- [ ] Implement `score(predictions, labels) -> QualityReport` for per-class precision, coverage, quote validity and decisive-invalid findings; run `python eval/score.py --predictions eval/results.jsonl --labels eval/labels.jsonl`.
- [ ] Verify all deterministic invariants; perform one live end-to-end investigation and record engine calls, budget, unavailable sources and evidence anchors. Replayed demo mode is explicitly labeled.
- [ ] Run research pilot defined in `research.md` after authorized recruitment; compare task quality/time and second-case adoption. If participants are unavailable, record the gate as unvalidated rather than fabricate success.
- [ ] Create setup instructions and a sub-three-minute local demonstration; verify private-window access to repo/video when submission is later authorized. Check existing-project and AI-tool disclosures before submission.
- [ ] Review spec coverage, measured failures and release readiness; commit documentation. User approves final release separately from design approval.

## Dependency sequence

1 → 2 → 3 → 4/5 → 6 → 7 → 8 → 9 → 10 → 11 → 12. Tasks 4 and 5 have independent adapters after shared contracts; same-agent sequential execution is the default unless the user explicitly chooses delegation. Each task ends in a runnable, testable increment; completion of the first increment is not the full product.

## Self-review record

All first-release spec features map to Tasks 1–12: membership/cases (1), sources/artifacts (2,5), budgets/events (3), discovery (4), evidence (6), lineage/workbench (7), adaptive runs/recovery (8), intake/review (9), packs/corrections (10), operations (11), evaluation/pilot (12). The five review-focus failures are assigned tests above. Future languages/monitoring/CMS/media work is explicitly outside this release. No tests, migrations, code or services described above have been executed or created.

## Execution ownership and approval schedule

Codex acts as engineering lead, architect, backend/agent/frontend implementer, QA/security engineer and documentation owner. Tasks 1–12 are internal verification checkpoints, not requests for user approval after each task. Default execution is native in this chat; no separate task/subagent is created without applicable authorization.

G0: user reviews finalized design as previously requested; implementation remains stopped until that review authorizes it. G1: Codex prepares one consolidated frontend design for finalization before UI implementation. G2: request SerpApi and LLM keys/accounts only at integration readiness; use local secure configuration, never chat/docs/public source. G3: user authorizes public repo/video/submission, paid spend and legal/license choices. Bundle related requests; safe backend work may continue while frontend feedback is pending after G0. No premature cloud/domain account is required.

Responsibility mapping: requirements/architecture/interfaces Codex; integration/configuration Codex; keys/account ownership user; all automated tests/triage Codex; real-case editorial signoff product editor; independent pilot judgments recruited participants; release preparation Codex; public publication/terms acceptance user. Do not list Codex as a human hackathon teammate: disclose AI assistance under the event rules.

PRD traceability: FR-01/02/03 -> Task 1 and 6 domain extension; FR-04 -> 4/8; FR-05 -> 2/5; FR-06/07/08 -> 6; FR-09/11 -> 7/9; FR-10/15 -> 3/8/11; FR-12 -> 9; FR-13/14 -> 10; FR-16 -> 1/11; FR-17 -> 4/12. Ten use-case fixtures are implemented in 6, surfaced in 7/9, corrections tested in 10. Stage-ledger endpoints are owned by 6, not a deferred feature.

Completion evidence: commands and artifacts per task, test counts/failures, measured provider costs, clean setup, accessibility check, recovery exercise, live-mode proof and disclosed external validation gaps. Report readiness honestly; no win, market fit, legal clearance or scale guarantee. Dates are not task duration estimates; the official submission deadline remains 10 October 2026, 23:59 IST.
