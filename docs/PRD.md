# FactLedger — Product Requirements Document
Version 1.0 · 8 October 2026 · Design finalized for review; implementation not authorized

## 1. Decision and product promise

**Track: Knowledge & Public Interest.** AI agents are the implementation technique, not the reason to choose the track. The product's primary purpose is civic research and accountable news reporting.

**Problem statement:** Indian newsroom researchers cannot reliably distinguish public-project announcements, approvals, funding, completion and actual operation when evidence is scattered across dated official records and repeated news reports. They need a stage- and time-specific evidence case that traces claims to original records, exposes missing or opposing evidence, and can be reproduced by an editor. Otherwise, they risk misleading reporting or substantial manual reconstruction.

**Product:** FactLedger is an evidence investigation workspace for public spending and project-delivery claims. It turns a scoped claim into a source-backed delivery-stage timeline, comparison matrix, missing-evidence checklist and editor-reviewed evidence pack. It does not certify ground reality or assign a numerical truth score.

**One-line pitch:** “Trace public-project claims from announcement to actual delivery—with evidence your editor can inspect.”

FactLedger is a screened working brand, not a legally cleared mark. See [naming and IP](naming-and-ip.md). Nothing here guarantees a hackathon win, commercial demand, source completeness or factual correctness.

## 2. Target user, buyer and workflow

Primary user: an English-language Indian newsroom desk researcher or fact-checking journalist in a small research team. Their recurring job is checking specific quantitative, funding or status claims about public projects and programmes before publication.

Secondary product user: the newsroom editor who challenges the evidence, requests further work and approves a qualified conclusion. Workspace owner manages memberships and retention. These are product permissions; the human collaborator on this project is not required to perform each product-user action.

First prospective buyer: a newsroom's editor/research lead. Later expansion: NGO/policy research teams. General consumers, political campaign automation and universal misinformation detection are not first-release personas.

Current workflow: receive claim → establish exactly what it asserts → search variants and official records → trace news to underlying documents → compare dates, amounts, units and project stages → preserve quotes and notes → editor reconstructs and challenges reasoning → publish externally → revisit changes.

Research supports the professional workflow, but the frequency, pain intensity, savings and willingness to pay are not yet established by our own customer interviews. Do not represent secondary research as customer validation.

## 3. Simple example and distinctive wedge

Illustrative, fictional claim: “District A's new 200-bed hospital is fully operational.”

A researcher enters the claim, district and as-of date. The system finds an announcement, a funding sanction, repeated coverage of the inauguration, and a later staffing record. It separates each stage, anchors exact passages, groups repeated reporting, and searches specifically for evidence of patient services. If none is found, it reports that operation is not established by the collected records; it does not call the claim false. The researcher can attach service records or field-report notes, and the editor reviews a qualified conclusion.

The distinctive unit is **claim × project × delivery stage × reference period × source version**, not a paragraph of AI prose. Generic research and fact-checking tools already exist. Our differentiation must be demonstrated through this focused workflow, not asserted as “no competitors.”

## 4. Scope and priorities

P0, required for complete first release:
- Persistent cases, atomic claim confirmation, editable scope, project identity and as-of period.
- Meaningful SerpApi discovery through Search and News; Scholar selectively when methodology needs it.
- Safe HTML/PDF acquisition, manual URL/PDF additions, preserved source versions and literal citations.
- Public-project stage ledger, quantitative comparison and date/attribution checks.
- Evidence table/source reader, source families, opposing evidence, gaps and justified overrides.
- Bounded, checkpointed adaptive investigation with visible progress, costs and pause/cancel/resume.
- Researcher/editor workflow, revision conflicts, review decisions and version-bound exports.
- Case library, workspace memberships, role-based access, notes, revision diff and case deletion.
- Runnable local stack, deterministic fixtures, clearly labelled live mode, tests, evaluation and documentation.

P1, after the complete core works: additional domain-specific query templates, enhanced source-family visualization and non-English evaluation. No P1 dependency may hide a P0 failure.

Explicitly outside first release: automatic publication, private-message ingestion, image/video authentication, guarantees of corruption or causality, inaccessible database scraping, autonomous purchasing/account creation, scheduled monitoring, CMS integration, payment billing, general web crawling and a national project registry. Ground investigations remain human work.

## 5. Functional requirements and acceptance contracts

| ID | Requirement | Acceptance criterion | Plan tasks |
|---|---|---|---|
| FR-01 | Identity and tenant isolation | Researcher/editor/owner permissions enforced server-side; cross-workspace reads/writes denied; last owner cannot be removed | 1, 9 |
| FR-02 | Cases and confirmed scope | Claim stores subject, assertion, geography, period, value/unit/baseline, attribution and asserted stage; ambiguity must be confirmed; every mutation checks expected_revision | 1, 9 |
| FR-03 | Project identity | Aliases retain original text; similar names across districts are not automatically merged; unresolved identity produces a gap | 1, 6 |
| FR-04 | Search discovery | Persist query purpose, engine, params, result ranks and retrieved time with sanitized provider response; no snippet becomes decisive evidence | 4, 8 |
| FR-05 | Acquisition and provenance | URL/PDF content has hash, access status and HTML character/PDF page anchors; blocked/scanned documents remain unavailable unless human-confirmed text is added | 2, 5 |
| FR-06 | Stage ledger | Each stage observation links claim, project, event/reference date, source version and evidence; announcement/inauguration cannot silently become operation | 6, 7 |
| FR-07 | Amounts and measures | Amount type, currency, unit, reference period, denominator and geographic scope retained; permitted conversions are deterministic and auditable | 6 |
| FR-08 | Evidence relations | SUPPORTS/CONTRADICTS require valid literal anchor and comparable scope; other relations are CONTEXT/INCOMPARABLE/INSUFFICIENT; automated finding separate from human conclusion | 6 |
| FR-09 | Source families | Exact duplicates grouped; inferred dependence labelled possible; editor can override with reason; source count is never a truth vote | 7 |
| FR-10 | Agent investigation | Planner → search → acquire → extract/compare → critic → purposeful follow-up → draft; stop on budgets, cancellation or unresolved decisive gaps | 3, 8 |
| FR-11 | Inspectable workbench | Every judgment opens quote and context; strongest opposing evidence and missing stage evidence visible; usable by keyboard and without color-only meaning | 7, 9 |
| FR-12 | Human review | Researcher submits a frozen revision; editor approves or returns with reason; newer revision cannot inherit approval; no auto publication | 9 |
| FR-13 | Reproducible packs | Export contains confirmed scope, qualified conclusion, citations, gaps, query trail, costs, reviewer status and source hashes; no provider secrets | 10 |
| FR-14 | Corrections | Refresh creates new run/revision; source and conclusion differences shown; old approved pack remains reproducible | 10 |
| FR-15 | Durable operations | Lease expiry, provider failure and Redis loss preserve authoritative state; replays do not create duplicate committed work; costs record uncertain outcomes | 3, 8, 11 |
| FR-16 | Privacy and deletion | Case access revoked immediately on deletion; jobs cancelled; documented grace/purge/backups; secrets redacted; owners control membership | 1, 11 |
| FR-17 | Honest demo | Fixture mode labelled; live SerpApi dependency demonstrable; no canned data passed off as live investigation | 4, 12 |

Use-case acceptance tests UC-01–UC-10 in [use-cases.md](use-cases.md) are normative examples of FR-03/06/07/08/14.

## 6. Domain model and finding rules

Delivery stages: UNKNOWN, ANNOUNCED, APPROVED, PROCURED, UNDER_CONSTRUCTION, PHYSICALLY_COMPLETED, INAUGURATED, OPERATIONAL. They are observations, not a guaranteed sequence. Inauguration may precede operation; a stalled/cancelled observation is separate from achieved stages. A document can assert a stage without proving it. Preserve attribution and evidence type.

Funding measures are separate: ALLOCATED, SANCTIONED, RELEASED, EXPENDED. Completion percentages are separate metrics with denominator/measurement date. Programme outcomes use domain metrics such as REGISTERED, APPROVED_BENEFICIARIES, PAID_BENEFICIARIES, PLACED or OCCUPIED, not invented infrastructure stages.

No automatic inference from an earlier stage to a later one. “Inaugurated” may support an inauguration claim but not operation. A later contrary record must match relevant period to contradict. Missing data produces a gap. Separate publication date, event date, reference period and retrieval timestamp; unknown remains unknown.

Monetary normalization uses Decimal, original expression, currency and unit multiplier. Lakh = 100,000; crore = 10,000,000. No FX conversion or inflation adjustment in v1. No addition across overlapping periods or geography. Every derived calculation stores operands, operation, units and evidence IDs. Arithmetic is deterministic; the LLM only proposes mappings.

Findings use “supported/contradicted/mixed/insufficient in the collected evidence,” not universal truth. A contradiction is not proof of wrongdoing. An official source is not automatically authoritative for outcomes; domain, method, attribution and limitations remain inspectable.

## 7. Product experience and user flows

Primary navigation: Cases / Review queue / Workspace settings. Case screen: header with revision/state; claim sidebar; central stage timeline and evidence table; source reader; run activity and budget panel.

Researcher happy path: create case → confirm atomic scope/project/time → inspect search plan → start run → follow progress → inspect evidence and gaps → add sources/correct mappings → write qualified conclusion → submit revision for editor review.

Editor: open review queue → read confirmed scope and conclusion → inspect decisive/opposing evidence and stage/date mappings → request changes or approve → export approved evidence pack.

Uncertainty: identity/date/denominator unclear → clarify or preserve unknown → targeted search/manual source → still unresolved → insufficient finding and explicit next evidence needed.

Recovery: provider failure retains partial evidence → retry within budget; process crash reclaims lease; paused run resumes remaining budget; exhausted/cancelled/completed run starts a new run, not a budget reset.

Correction: refresh an approved case → new revision → diff → new review → new pack. Prior pack cannot change.

Detailed data contracts, state machines, APIs and failure paths are in [product-system-spec.md](product-system-spec.md). AI orchestration is in [agent-design.md](agent-design.md).

## 8. Architecture and nonfunctional requirements

React/TypeScript client → FastAPI modular API → PostgreSQL + S3-compatible artifacts. Transactional outbox dispatches durable runs through Redis to a Python LangGraph worker. Worker accesses SerpApi, bounded public-source fetcher and provider-independent LLM adapter. Worker events feed API SSE with replay. Browser never receives provider keys.

Default ceilings per run: 3 claims; 12 uncached search-call attempts; 30 documents; 3 investigation rounds; 60,000 billed input/output model tokens; 10 running minutes excluding explicit pause; USD 2 estimated maximum. Up to 4 fetches, 2 searches and 2 model calls concurrently. At most 2 transient retries per action; retries consume ceilings. Cost ceiling is a budget guard, not observed average cost.

Public HTTPS acquisition: SSRF protection including every redirect and resolved address; 20 MB streaming cap, 20-second fetch timeout, 100 extracted PDF pages per document per run. No browser execution of untrusted pages. PDF parsing isolated (512 MiB / 20-second extraction cap). Long documents allow bounded page ranges, with unexamined pages explicitly reported. Use pypdf/pdfplumber and reject ambiguous table mappings. Document text is untrusted data, never tool instructions.

PostgreSQL owns runs, checkpoints, costs, reviews and outbox. Redis is transport/cache only. Lease 60 seconds with heartbeat; idempotency and expected-revision prevent duplicate/conflicting committed work. External provider requests cannot be guaranteed exactly-once across crashes; record ambiguous charges and reconcile.

Initial test envelope, not verified capacity: 5 simultaneous runs, 20 workspace members and 100 cases/day. Pagination, object storage and queued workers support horizontal worker growth. Production scale claims require measured load tests and provider quota planning. No microservice split until measured bottlenecks justify it.

Raw-source retention default 90 days; content-free operational logs 30 days. Approved minimal excerpts retained until case deletion; avoid unnecessary full-article redistribution. Immediate deletion access denial; 7-day recoverable grace then active-store purge; backup expiry at most 30 days. Validate against provider terms and deployment policy before public hosting.

Accessibility target: WCAG 2.2 AA for core flows; semantic tables, keyboard access, text labels and responsive layout. Engineering must test it rather than claim certification.

## 9. Evaluation, release and business evidence

Engineering gates:
1. Every decisive citation resolves to an exact preserved anchor; malformed citations rejected.
2. Cross-tenant isolation, prompt-injection, SSRF, revisions, cancellation and deletion tests pass.
3. All 10 use-case fixtures pass; repeated articles, missing dates and stage mismatches included.
4. Worker kill/restart and Redis recreation preserve state; export immutability and restore exercise pass.
5. At least 100 stratified evidence-pair fixtures with independently adjudicated labels; target ≥90% decisive relation precision, report coverage/abstention and uncertainty. Engineering owns preparation/scoring. If qualified independent reviewers are unavailable, do not label synthetic/self-reviewed tests “human-validated”; disclose that gate as unmet.
6. Live provider smoke test, clean local setup, regression suite and measured cost report pass.

Customer validation is separate from code release: proposed pilot with 5 researchers, 2 editors, 10 paired tasks. Targets: ≥30% median active-time reduction without evidence-quality regression, ≥3/5 researchers voluntarily investigate a second case. These are hypotheses, not validated results or promised savings. Engineering prepares recruitment materials and instruments tests; external participation is a dependency, not a compulsory task assigned to the user.

Revenue hypothesis: paid organizational seats/workspace with included case quota and usage overages, not ad-driven verdicts. Price should be tested; ₹10,000/month/workspace is an interview hypothesis only. Track costs per accepted case, gross margin after support, retention and acquisition cost. No revenue forecast without conversion/retention evidence. Existing competitors indicate demand for research tooling, not demand for our version.

Potential future moat: an expert-reviewed Indian delivery-stage ontology, difficult-case evaluation corpus, curated original-source relationships and integrated editorial workflow. None exists today; raw public data or an LLM wrapper is not a defensible moat.

## 10. Roles and decision rights

| Workstream | Responsible/accountable | Your involvement |
|---|---|---|
| Product scope and requirement coherence | Codex engineering team | Review this design; raise material objections |
| Architecture, backend, database, agent orchestration | Codex | No routine architecture approvals |
| Frontend UX, accessibility, implementation | Codex | One consolidated frontend design finalization before UI implementation |
| QA, security, evaluation, runbooks, cost reporting | Codex | Receive evidence-based milestone summaries |
| SerpApi and LLM credentials | You supply; Codex integrates safely | Create accounts/add keys locally; never put secrets in docs, browser or public repo |
| Local database/storage/dev identity | Codex | No account required |
| Hosted account/domain/identity provider if needed | You create/authorize; Codex configures | Only when needed; local-first avoids premature accounts |
| Spending, paid tiers, legal agreements, public release/submission | You authorize/sign | Explicit authority required; no autonomous purchase, publication or terms acceptance |
| Source investigation and editorial conclusions inside product | Product researcher/editor | Not automatically assigned to you as project reviewer |
| External pilot recruitment/independent evaluation | Codex prepares; qualified participants provide judgments | Optional introductions only; not routine engineering review |

Approval gates are batched: (G0) this design review because you previously required it; (G1) frontend finalization; (G2) keys/accounts only when integrations need them; (G3) public publication/submission and meaningful spend. Subsequent engineering milestones are verification gates owned by Codex, not approval requests to you. Escalate only a material scope change, unresolved safety/legal issue, external authority or budget change. Do not introduce tools requiring new accounts without explaining why.

## 11. Delivery sequence and hackathon strategy

1. Durable identity/cases/artifacts/runs.
2. Search and acquisition; first live source-to-anchor vertical slice.
3. Domain comparison/stage ledger/source families.
4. Bounded agents and complete workbench/review flows.
5. Frozen packs/corrections/security/operations.
6. Evaluation, clean setup and demo/submission preparation.

The task-level test-first plan is [implementation-plan.md](implementation-plan.md); its 12 tasks implement every FR above. No product implementation starts in this documentation turn.

Competition demonstration: one fictional fixture for repeatable setup plus one verified live-source case; explicitly distinguish them. Show a tempting announcement→operation mistake, agent's evidence gap and follow-up, source anchor, source-family grouping, editor review and frozen export. A sub-three-minute recording should show product behavior, not architecture slides. Real allegations or political conclusions require qualified editorial review.

The official event assesses idea strength, originality, technical complexity, usefulness and meaningful SerpApi usage together, without fixed weights. This design can address all five, but feature count and agent count do not predict a win. The strongest proof is an editor accepting a case faster without losing correctness.

**Calendar constraint:** official final submission closes 10 October 2026 at 23:59 IST. The full product scope is not silently reduced because of that date. If verified readiness and deadline diverge, report that honestly; an eligible submission must be genuinely runnable, not an unfinished product disguised as complete. User-first product work remains valuable even if contest readiness is not achieved.

## 12. Risks and decision log

| Risk | Response / decision |
|---|---|
| Search misses non-indexed/local records | Coverage limitations and next-evidence checklist; manual source additions |
| Official records do not establish ground reality | Preserve attribution; no operation certification; field work outside automation |
| Repeated news gives false corroboration | Source families and visible dependence uncertainty |
| LLM stage/numeric/date hallucination | Literal anchors, typed schemas, deterministic checks, abstention, reviewer override |
| Small newsrooms may not pay | Test willingness to pay and repeat usage before business expansion |
| Generic competitors reproduce features | Focused delivery ontology and measured editor workflow, not broad chatbot positioning |
| Name/IP conflict | Screened brand; registry/domain clearance before commercial branding |
| Public repository conflicts with secrecy | Hackathon requires public code; explicit release gate and deliberate license; keep customer data/secrets private |

Final decisions: focused public-project domain; Knowledge & Public Interest; FactLedger working brand; modular API/worker; constrained agents; reviewable evidence rather than autonomous verdicts; no implementation before design review.

Sources and confidence levels: [research.md](research.md). External facts are sourced there; proposed architecture, demand and metrics remain our design choices/hypotheses.
