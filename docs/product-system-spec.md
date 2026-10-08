# FactLedger: product and system specification

Design specification v1.0 · 8 October 2026 · Consult implementation-status.md and release-readiness.md for shipped behavior and verified results.

### 8 October engineering amendment precedence

The final product name is **FactLedger**. Read [engineering-review.md](engineering-review.md) as the proposed replacement contract for the affected sections below. In this review package its explicit contracts take precedence over earlier prose: run-owned progressive results and explicit revision integration (§4); submission/decision separation and supersession on edits (§4); fenced leases and durable job receipts (§4); composite tenant/case/version relationships and MetricObservation (§5); preflight plans, API errors/read commands, same-origin OIDC sessions and authenticated artifact downloads (§6); frontend design/states (§7); independent deletion ledger and recovery (§11). The first-release functional scope and existing evidence invariants remain required. These amendments are proposed for G0 review, not implementation authorization.

## 1. Design brief and decision

Build a full functioning investigation workspace for small Indian newsrooms checking public spending and project-delivery claims. The product helps a researcher assemble evidence and an editor reproduce and review the reasoning. Search through SerpApi is central to investigation. Human editorial judgment remains accountable and separately recorded.

Working brand: FactLedger — public-project claims, traced to evidence. Public-web name screening found no exact indexed match; this is not trademark clearance. See naming-and-ip.md. Track decision: **Knowledge & Public Interest**. AI Agents is the technical approach and alternative track if the product's primary purpose later changes. Track choice is not a claim about competition density or win probability. See `research.md` for direct sources, limitations and adoption hypotheses.

The workspace is empty of existing product code. Previous descriptions of FactLedger capabilities are not treated as verified assets. Stack choices below are proposals, not claims about installed software or an existing system.

## 2. Target user and painful workflow

Primary user: a desk researcher or fact-checking journalist in a small Indian newsroom, checking public claims about policy, public spending and infrastructure/project delivery. Primary language for first release: English, including Indian English and public English-language Indian documents. Product usefulness for Hindi and other languages needs a separate evaluated release, not a translation toggle.

Secondary user: the editor who reviews the investigation, requests missing evidence and signs off the resulting case. NGO policy researchers are an expansion audience, not simultaneous first-release personas.

Today: receive a claim → clarify what it means → search many phrasings → follow articles to announcements, reports and underlying data → compare dates, units and definitions → capture notes/quotes → explain the reasoning to an editor → reopen sources during review → update when evidence changes. Documented professional practice supports this sequence; its frequency, duration and our proposed savings require interviews.

| Workflow step | Candidate pain | Product intervention | Proof of value |
|---|---|---|---|
| Scope | Vague claim hides date, denominator or project stage | Confirm atomic claim, geography, period, units and definitions | Fewer reviewer scope corrections |
| Discover | Search language and scattered source locations | Adaptive search plan; primary-source queries | Relevant evidence recall against a human case |
| Trace | Several reports may repeat one announcement | Source lineage and evidence families | Editor can identify original evidence |
| Compare | Announcement mistaken for completion; old numbers mixed with new | Stage/date/unit comparison and explicit mismatches | Correct abstention on incomparable evidence |
| Document | Quote/source/context disconnected in notes | Persistent evidence anchors and search trail | Exported assertions resolve to preserved excerpts |
| Review | Editor reconstructs work from links | Claim workbench, review comments, decisions and versions | Reduced review time without reduced quality |
| Update | Changed source silently changes interpretation | New run and case revision; prior pack retained | Reproducible correction history |

Job to be done: when an important public claim reaches my desk, help me identify exactly what is being asserted, gather independent relevant evidence, inspect contradictions and limitations, and give my editor a reproducible case without manually reconstructing every search and citation.

## 3. Problem statement and success

**Indian newsroom researchers cannot reliably distinguish public-project announcements, approvals, funding, completion and actual operation when evidence is scattered across dated official records and repeated news reports. They need a stage- and time-specific evidence case that traces claims to original records, exposes missing or opposing evidence, and can be reproduced by an editor. Otherwise, they risk misleading reporting or substantial manual reconstruction.**

Business hypothesis: small teams value saved researcher/editor time and case reuse. Funding constraints make willingness to pay uncertain. Proposed distribution: locally runnable evaluation edition and a hosted team workspace with organizational subscription; price, open-source license and hosted providers are business decisions for later review. No billing is in release 1.

Primary metric: active researcher-plus-editor minutes to an accepted evidence case. Quality counters: unsupported exported assertions, missed material opposing evidence, incorrectly inferred source independence and incorrect date/definition/stage matches. Adoption: repeat use on a real second case. See the research validation protocol.

Proposed release targets, not measurements: 100% exported factual assertions have resolvable evidence or explicit attributed human notes; 100% decisions include actor/time/version; evidence-relation precision >=90% on a human-labeled 100-pair set; zero decisive classifications from snippet-only material or mismatched geography/period/stage; successful case recovery after worker failure; normal capped investigations reach a qualified draft or explicit partial result within 10 minutes of running time at p95 under a documented test load; fetching complete evidence is not guaranteed. Meeting targets is necessary but does not guarantee truth or complete web coverage.

## 4. Solution alternatives and selected product

| Approach | Strength | Tradeoff |
|---|---|---|
| General autonomous research reports | Broad questions, simple chat input | Strong incumbents; report readability can conceal weak evidence |
| Consumer claim checker / extension | Low-friction reading and public reach | Difficult distribution, multimedia access and overtrust |
| Evidence case workspace | Inspectable professional workflow, reusable work and review | Smaller initial audience; more deliberate interaction |

Select evidence case workspace. Product promise: **turn a public claim into an evidence case that another researcher can inspect, challenge and reproduce.**

## 5. Product scope: full first release

Case library: create, assign, search and archive investigations; revisions and tags; workspace owner/researcher/editor roles. Cases remain private to members; no automatic public sharing.

Intake: paste a claim or public URL; optionally upload a PDF. Preserve original wording and attribution. Suggest atomic claims; user confirms scope and chooses which claims to investigate. Ambiguous/causal/predictive claims can be recorded but require human clarification or specialist work before a decisive finding.

Investigation: user reviews a legible search plan, source preferences, period, geography and budget. Agent uses Google, News and optional Scholar based on evidence need. User can pause/cancel, inspect progress, add a source, request a targeted follow-up, or resume after a blocker. Search plan is adaptable within confirmed scope and budget.

Workbench: claim list; support/opposition/context/insufficient evidence; source reader with exact quote highlights; timeline; detected source families; manual source-type and lineage corrections; editable definitions and stage comparisons; notes and reviewer comments. Table view is default; graph is an optional explanation view.

Review and export: researcher submits a case revision to an editor. Editor approves, returns with comments, or records an unresolved conclusion. Generate Markdown, HTML and JSON evidence packs from a frozen case revision. Draft packs can be exported with a visible draft label. Approved packs are self-contained with excerpts and hashes; full source files remain access-controlled. No automatic publication or claimant contact.

Updates: manually run a fresh search; compare added/changed/withdrawn evidence; create a new revision and reopen review. No scheduled monitoring in release 1. Notifications are in-app task/review notices.

Out of scope by product boundary: private messaging ingestion, forensic image/video authenticity, causality certification, automated legal/medical/financial advice, deepfake detector, unrestricted browsing/actions, automated publishing, claimant outreach, paywall access and newsroom CMS integration. Users may record offline expert or claimant input as attributed human notes with attachment and provenance; it is never represented as web-verified evidence.

## 6. Evidence semantics and invariants

Atomic Claim fields: subject, predicate, object/value, unit, geography, time window, comparison baseline, asserted delivery stage, measure kind, attribution, original text and scope version. DeliveryStage = UNKNOWN/ANNOUNCED/APPROVED/PROCURED/UNDER_CONSTRUCTION/PHYSICALLY_COMPLETED/INAUGURATED/OPERATIONAL. FundingMeasure = ALLOCATED/SANCTIONED/RELEASED/EXPENDED, not a delivery stage. Programme outcomes retain a typed domain metric and denominator. Full domain rules in PRD section 6.

Evidence relation: SUPPORTS, CONTRADICTS, CONTEXT, INCOMPARABLE, INSUFFICIENT. A relation is to a particular claim version, not to a generic topic. Include original-language exact quote, surrounding context, source version, page/character anchors, structured comparison and classifier rationale. A claim quoted in an article is evidence that the claim was made; it is not automatically evidence that it is true.

Source type is a fact about the document (official release, statistical table, original reporting, scholarly paper, other), not a universal credibility score. Primary sources can themselves be wrong or self-interested. No numeric truth confidence or source reputation ranking is displayed.

Lineage: exact document duplicates are detected by hash/canonical URL. Repeated excerpts and explicit outgoing attribution suggest a family. Semantic similarity alone creates a *possible dependency*, not proven copying. Record DETECTED or HUMAN_CONFIRMED edges and the evidence for them. Uncertain independence is labeled unknown. Do not count different domains as independent evidence by default.

Temporal interpretation: publication date, event date, reference period and retrieval time are separate nullable fields. Unknown dates remain unknown. A new article may cite older data. Contradiction requires comparable scope; different periods or project stages trigger INCOMPARABLE or context.

Automated finding states: SUPPORTED_BY_COLLECTED_EVIDENCE, CONTRADICTED_BY_COLLECTED_EVIDENCE, MIXED_EVIDENCE, INSUFFICIENT_EVIDENCE. They describe bounded evidence collection. Human final conclusion is a separate record with text, reason, cited evidence, reviewer and revision. User can override a model relation with a reason; the prior relation is preserved.

Invariants:

1. Snippets discover sources; snippet-only content cannot support a decisive finding.
2. Every evidence quote is a literal substring of its preserved normalized extraction or an anchored PDF table/cell; model-created quotations fail validation.
3. Unsupported summary sentences are removed or rendered as explicitly attributed uncertainty/human notes, never silently assigned citations.
4. No evidence found means insufficient evidence, never false.
5. Corroboration is not a majority vote. One authoritative relevant record can outweigh many repeated reports, with the reasoning shown.
6. Material contradictory evidence appears in export even if the editor approves another conclusion.
7. A scope change invalidates affected relations, findings and review approval until reevaluated.
8. Revision approvals and exports bind immutable input/evidence/review versions. New evidence cannot mutate a previously approved export.
9. Hashes establish content identity within the stored case, not authenticity or truth.
10. All model judgments are identifiable and reproducible from recorded model/prompt versions and stored inputs; provider nondeterminism is disclosed.

## 7. System architecture and boundaries

Deployment: a modular API and a separately running investigation worker, sharing domain code and durable storage. Avoid per-agent microservices. Browser communicates only with API; worker alone invokes search, fetching and models. Checkpoints and evidence records persist in PostgreSQL. Transactional outbox drives run jobs through Redis-backed workers; retries are idempotent.

Proposed stack: React + TypeScript for web UI; FastAPI + Pydantic for API/contracts; Python LangGraph for checkpointed orchestration; PostgreSQL for tenancy, cases, runs, evidence and audit (full-text search; optional pgvector candidate retrieval); Redis for queue/rate limiting, not evidence durability; object storage with S3-compatible interface (local MinIO in Docker Compose) for raw search payloads, extracted documents and evidence packs. HTTPX + HTML text extraction and pypdf + pdfplumber for supported source acquisition; scanned PDFs need manually confirmed OCR or remain unavailable. Exact dependency versions chosen and pinned during implementation after compatibility checks.

Public deployment uses a single configured OIDC issuer with verified issuer/audience/expiry; local-only development identity is disabled outside explicit development mode. Members and roles are stored server-side. Team isolation is enforced on every endpoint, object access and worker lookup. SQL row policies provide defense in depth with a non-owner application DB role. Signed object links have short expiry.

Module responsibilities:

| Module | Owns | Interface |
|---|---|---|
| Cases | Workspace membership, claim versions, case revisions | REST commands and domain records |
| Runs | Job creation, budget reservation, state, SSE progress | Run commands + durable RunEvent |
| Investigation | Search-plan state, checkpoints, next-query decisions | RunExecutor(run_id) |
| Search | SerpApi engine parameters, caching, response normalization | SearchGateway.search(SearchRequest) -> SearchBatch |
| Acquisition | Public URL/PDF retrieval, extraction, anchors, failure states | AcquisitionGateway.acquire(SourceRef, page_ranges?: list[PageRange]) -> SourceVersion |
| Evidence | Claim comparisons, quote validation, lineage suggestions | EvidenceAnalyzer.analyze(ClaimVersion, SourceVersion) -> EvidenceSet |
| Review | Comments, overrides, immutable approval records | ReviewService.decide(ReviewDecision) |
| Reports | Revision-bound packs and integrity manifest | ReportService.export(case_id, revision_id, format) |
| Platform | Auth, storage, outbox, observability, provider configuration | Adapters; no provider keys to browser |

Full-text retrieval over the case corpus precedes model analysis; optional embeddings retrieve candidates but never certify evidence. No separate Qdrant dependency in release 1. LangGraph coordinates roles as typed nodes, not unbounded autonomous agent conversations.

## 8. Investigation algorithm and operational policy

START → scope confirmed → plan → reserve run budget → dispatch search batch → persist raw search payload + normalized result → acquire selected source versions → extract/anchor → classify claim relations → validate quotes/comparability → suggest lineage → evaluate gaps → either search again or checkpoint a findings draft → human review.

Follow-up logic: missing primary record triggers site/organization-focused queries; material disagreement triggers comparable-date/definition queries; apparent repetition triggers original-source queries; stale evidence triggers recent-news queries. A targeted follow-up creates a new run within the same case and new revision; it does not rewrite old evidence.

Default per run: at most 3 selected claims, 12 uncached search-call attempts, 30 acquired documents, 3 planning rounds, 60,000 billed input/output model tokens and 10 minutes wall time. Hard user-configured ceilings override defaults; default maximum dollar budget USD 2 estimated using configured provider rates. Larger cases proceed in additional explicit runs. Stop when every selected claim has the required evidence checks completed or a limit/cancellation is reached. This is not exhaustive search proof. Budget-stop produces partial evidence and an explicit completion reason.

Concurrency defaults: 4 acquisitions, 2 search calls, 2 model calls per worker; workspace aggregate limits cap simultaneous runs. Reserve call/token/cost capacity transactionally before dispatch; reconcile actual usage after response. Provider retries count toward attempts; at most 2 retry attempts with exponential backoff and jitter for transient failures. HTTP 429 respects Retry-After within wall budget. No retry for authorization or invalid requests. Mark estimated cost when actual provider usage is unavailable. Pricing is configuration, not hardcoded current-market claims.

Persist each stage and idempotency key. Worker lease expires after 60 seconds without heartbeat; recovery resumes from last persisted checkpoint. Cancel enters CANCEL_REQUESTED and becomes CANCELLED after active calls return or time out; show outstanding call status. Documents already collected are retained. SSE replays by durable event sequence; reconnect does not launch another run.

Fetcher: HTTPS only in v1; resolve and validate public IPs, block loopback/private/link-local, enforce redirect revalidation, streaming byte limit 20 MB, timeout 20 seconds, PDF extraction max 100 pages per document per run, allowlisted content types. Access failure yields an unavailable source record plus suggestion for user-provided lawful copy. Prompt-injection text is treated as evidence data; models cannot acquire tools or issue network calls directly. HTML is sanitized for display and never executed.

## 9. Data model and consistency

Workspace → Membership(User, role). Workspace → Case → ClaimVersion and CaseRevision. Case → InvestigationRun → SearchBatch/SearchResult, RunEvent and Checkpoint. SearchResult → Source (canonical locator) → SourceVersion (retrieval timestamp, content hash, extraction and artifact locator). ClaimVersion + SourceVersion → Evidence. Evidence connects through LineageEdge/SourceFamily with observed rationale. CaseRevision snapshots claim/evidence/finding IDs. ReviewDecision binds CaseRevision. ExportPack binds revision, review decision and manifest. AuditEvent records actor, action and version.

Key fields: UUID identifiers; every tenant record has workspace_id; each case mutation carries expected_revision (optimistic lock); evidence character offsets refer to extraction version, not raw HTML; PDF page/table anchors preserve cell metadata; SourceVersion fields include access status, original URL, final URL, raw hash, extracted hash, timestamps, date provenance and extraction method. Search records store query/engine/localization/date parameters, result rank, timestamp and SerpApi search ID when returned. Reruns reference prior run and comparison baseline.

Object keys include workspace/case/source-version identifiers and never user-supplied path components. No credentials stored in search parameter payloads. Provider keys remain process secrets. Idempotency-Key unique per workspace+operation prevents duplicate run creation. Outbox creation and run record commit in one transaction; delivery deduplicates by job ID. Redis loss cannot delete a case; replay outbox jobs and reconcile leased runs.

Retention proposal: workspace-configured default 90 days for raw/extracted document artifacts and 30 days for content-free operational logs. Approved packs retain cited excerpts/metadata until case deletion; export warns before source retention expires. User can archive a case or request deletion; deletion must remove case artifacts and derived embeddings after a grace period. Backup expiry is documented. Public demo fixtures use public, attributed excerpts; no private real newsroom data is placed in the hackathon repository.

## 10. API and event contracts

API prefix `/v1`. All commands are authenticated except liveness. Standard error `{code,message,request_id,details}`; stable codes AUTH_REQUIRED, FORBIDDEN, REVISION_CONFLICT, INVALID_SCOPE, BUDGET_EXCEEDED, PROVIDER_UNAVAILABLE, SOURCE_UNAVAILABLE. Run-level partial errors are stored as events, not hidden by successful HTTP status.

| Command | Contract |
|---|---|
| POST /cases | `{title, original_claim, attribution?, workspace_id}` -> `{case_id, revision:1}` |
| POST /cases/{id}/scope | `{expected_revision, claims:[ClaimScope]}` -> new revision; invalidate affected analysis |
| POST /cases/{id}/runs | Idempotency-Key + `{expected_revision, claim_ids, budget, preferences, mode:initial/follow_up/refresh}` -> 202 `{run_id,state}` |
| GET /runs/{id}/events | SSE event `{seq,type,time,payload}`; resume with Last-Event-ID |
| POST /runs/{id}/cancel | Idempotent; accepted cancellation state |
| POST /runs/{id}/pause | Request checkpoint pause; active calls finish/timeout; state becomes PAUSED |
| POST /runs/{id}/resume | Idempotent; PAUSED only; retain original scope and remaining budgets |
| POST /cases/{id}/sources | `{expected_revision,url,page_ranges?}` or validated PDF upload -> acquisition job |
| PATCH /evidence/{id}/relation | `{expected_revision, relation, reason}` -> human override and new case revision |
| POST /cases/{id}/reviews | `{expected_revision,decision:approve/return, conclusion, citations, note}` -> immutable review decision |
| POST /cases/{id}/exports | `{revision_id,format:md/html/json}` -> export job and download locator |
| GET /cases/{id}/revisions/{revision}/diff | Added/removed evidence, scope/decision changes |
| GET /workspaces/{id}/cases | Paginated case library with tags/state filters |
| PATCH /cases/{id} | `{expected_revision,title?,tags?,assignee_id?,archived?}` -> new case metadata version |
| POST /cases/{id}/notes | `{expected_revision,text,attribution,attachment_id?,evidence_ids?}` -> attributed human note |
| PATCH /lineage/{id} | `{expected_revision,status,reason}` -> human correction and new case revision |
| POST /workspaces/{id}/members | Owner adds existing verified user ID with role; no unsolicited email invitation |
| PATCH /workspaces/{id}/members/{user_id} | Owner updates role; prevent removal of the final owner |
| DELETE /cases/{id} | Owner/researcher with case permission schedules deletion after 7-day grace; immutable exports withdrawn from access |

Pause becomes effective at a persisted safe boundary after active calls settle. The 10-minute wall budget counts accumulated RUNNING time, excluding explicit pauses. Failed/cancelled/completed runs do not resume; new runs reference their prior run. Case deletion cancels active jobs and immediately denies further case/artifact access, purges active data after the 7-day grace and expires backups within 30 days; workspace owner can restore during grace. Storage lifecycle and deletion audit retain no removed document/claim content.

Run event types: run.created, plan.ready, search.completed, source.acquired, source.unavailable, evidence.ready, gap.detected, budget.updated, run.paused, run.cancel_requested, run.cancelled, run.failed, run.ready_for_review. Human-readable messages describe user actions/evidence progress, not internal stack names.

## 11. User flows and information architecture

Navigation: Cases; case workspace (Claims, Evidence, Sources, Timeline, Activity); Review queue; workspace settings (members, provider readiness, budgets). A graph view is available within Evidence. Product language uses claim/source/review rather than agent/memory/NLI.

Flow A — researcher: library → create case → paste claim/URL/PDF → confirm extracted claims and scope → inspect plan and budget → start investigation → inspect progressively arriving evidence → open exact excerpt in source reader → correct scope/relation or add source → request targeted follow-up → write qualified conclusion → submit revision for review. Empty/evidence-unavailable state offers source addition or unresolved handoff.

Flow B — editor: review queue → open submitted frozen revision → see scope + proposed conclusion + strongest contrary evidence → inspect citations and lineage → approve or return with a specific comment. Request for missing primary evidence returns case to research. Approval freezes that revision; researcher changes create a new draft.

Flow C — uncertainty: budget exhausted, missing primary source, incomparable dates or extraction failed → show completed searches, missing evidence and why the result is partial → user chooses another bounded run, uploads source or submits unresolved conclusion. No evidence count is portrayed as truth confidence.

Flow D — correction: open prior approved case → fresh search → compare new source versions/evidence → evaluate affected claims → new revision → editor review → export updated pack referencing superseded revision. Existing export remains intact.

Flow E — cancellation/recovery: cancel request → active-call indicator → retained partial evidence → resume via new run. On connection loss: reconnect to persisted events. On worker failure: automatic lease recovery; user sees resumed status and failed stage if retry limit reached.

Case lifecycle: DRAFT → INVESTIGATING → READY_FOR_REVIEW → IN_REVIEW → APPROVED. RETURNED goes back to DRAFT; changed approved case creates DRAFT revision while old approved revision remains. ARCHIVED is library visibility. Run lifecycle is separate: QUEUED → RUNNING → PAUSED/READY/FAILED/CANCELLED. CANCEL_REQUESTED is a transient state while active calls settle; READY may contain a partial evidence brief. PAUSED resumes through a checkpoint command; budget exhaustion completes a partial run and requires a new run.

Wireframe: header with case title, revision and review state; left claim list; central evidence table with comparison fields; right source reader with anchored excerpt; bottom search timeline/activity. Editor mode foregrounds proposed conclusion, contrary evidence and review controls. Keyboard navigation and accessible status labels are required; color never carries relation meaning alone.

## 12. Evaluation, deployment and release gates

Create human-curated test cases for supported/contradicted/mixed/insufficient claims, repeated-source reporting, changed dates, incompatible metrics, announcements vs operations, source attribution vs endorsement, unavailable sources and prompt injection. Use synthetic documents for algorithm tests, public-source snapshots with attribution for evaluation, and fresh live searches for integration demonstrations. Clearly label replayed data; never represent it as live.

Evaluate deterministic quote and revision invariants before model quality. Label at least 100 evidence pairs with two independent annotators and adjudicate disagreements. Measure precision by relation class and report coverage/abstention; a high score from refusing everything fails usefulness. Run user-task tests against the manual baseline and an available general research tool using matched scope, frozen inputs where possible and fresh-web differences disclosed.

Proposed initial deployment envelope: 5 concurrent investigations, 100 cases/day and 20 workspace members; validate before claiming capacity. Horizontal workers scale within provider/workspace budgets. API restarts preserve state. Backup PostgreSQL and objects; periodically restore a selected case/export; monitor queue age, failure rates, stage latency, cost, citation errors and reviewer-return reasons. Logs contain IDs and timings, not full claims/documents by default.

First full release includes identity/membership, case persistence, all specified investigation and review flows, manual sources/PDFs, revision diff, exports, limits, recovery, accessibility and runbook. Later expansion includes evaluated Indian languages, source-specific structured datasets, monitoring, newsroom integrations and multimedia verification; these require separate designs.

Implementation is gated on the user's review of this specification, canvas and plan. All implementation tasks are proposed; no scaffold, application dependencies, migration or product service has been created.

## 13. Decisions to review

1. Primary persona and initial domain: newsroom desk researcher; public spending and project delivery claims.
2. Knowledge & Public Interest as final submission track.
3. Evidence cases and editorial review as primary product experience.
4. English first release and source acquisition limits.
5. Separate AI findings and human conclusions; no uncalibrated truth percentage.
6. Modular API + durable worker; PostgreSQL as authority, object storage for artifacts.
7. Default per-run budget and initial deployment envelope as configurable proposals.
8. Adoption pilot before asserting product-market fit; all performance targets unverified.

## 14. Finalized domain ledger and contract supplement

PRD v1.0 is the product scope/requirements authority; this document specifies technical behavior. Neither authorizes implementation. AI boundaries are in agent-design.md; UC-01–UC-10 are normative fixtures. Any future conflict must be corrected across artifacts, not silently chosen by an implementer.

ProjectRef: id, workspace_id, case_id, canonical_name, aliases (original_text, source_version_id?), geography, external_identifiers[], identity_status CONFIRMED/AMBIGUOUS. Never merge projects based on a matching name alone.

StageObservation: id, workspace_id, claim_version_id, project_id, stage: DeliveryStage, attributed_to?, event_date?, reference_period?, observed_status? (STALLED/CANCELLED/RESUMED), evidence_ids[], source_version_id, extraction_version. Store observations rather than overwriting one global “current stage.” A timeline displays event dates, unknown dates separately and conflicting attributed observations. Stalled/cancelled is not an achieved delivery stage.

FundingObservation: id, workspace_id, claim_version_id, project_id, kind: FundingMeasure, original_expression, value_decimal, currency, unit_multiplier, reference_period, geography, denominator?, evidence_ids[], source_version_id. DerivedQuantity stores operation, operands with evidence IDs, normalized value/unit and limitations. No FX/inflation adjustments or speculative sum across overlaps.

CaseRevision snapshots project refs, stage/funding observations and derived quantities along with claims/evidence/findings. Override creates a new revision with actor/reason; approved observations cannot mutate. Typed domain outputs are derived from validated evidence, never search snippets.

Additional read API: GET /cases/{id}/ledger?revision={revision} -> {projects, stage_observations, funding_observations, derived_quantities, gaps}. Authorization and revision filters apply. A ledger-mapping correction uses POST /cases/{id}/ledger-overrides with {expected_revision, observation_id, corrected_fields, reason}; domain service validates permitted fields and creates a new revision. This is not an arbitrary write of unsupported stages.

Workbench adds a table-first delivery-stage timeline and funding comparison tabs. Each observation opens the same preserved source reader as evidence. Source dates and claim as-of period remain distinct; unknown stage/date is a visible state.

Execution ownership follows PRD section 10: Codex owns engineering, automated validation and release preparation; user gates are design/front-end/keys-accounts/spend-publication. Subject-matter editors and independent pilot participants are separate product/external roles, not default obligations assigned to the project reviewer. No real-customer or independent accuracy validation is claimed until performed.

PDF scope and resource supplement: a long PDF is not rejected solely for total page count. Extract explicit one-based inclusive page_ranges (validated against document page count), at most 100 unique pages per document across a run. Without ranges, extract the first min(100,total) pages and mark PARTIAL coverage when more remain. Agent may inspect embedded outline/first-page contents and request relevant ranges within remaining page/run limits; user can select a range on source addition. Never claim evidence absence across unexamined pages. SourceVersion includes total_pages, extracted_pages and unexamined_ranges. A later extraction creates a new extraction version/anchors; no prior quote offsets change. Partial-page excerpts remain attributable to physical PDF page numbers even if printed numbering differs.

PDF parsing uses pypdf for page/text access and pdfplumber for bounded layout/table cell extraction. Unclear merged headers/cell mapping produces an ambiguous table warning, not a decisive numeric relation; researcher may confirm a mapping with actor/reason and source anchor. Parser runs in a restricted process with a 512 MiB memory cap and 20-second CPU/wall-time extraction cap; decompression/complexity failures remain unavailable/partial. Scanned pages need manually confirmed OCR; do not pretend pypdf provides OCR. Engineering verifies sandbox enforcement on the supported container runtime. Licensing motivation and sources are in naming-and-ip.md.
