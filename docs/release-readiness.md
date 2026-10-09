# FactLedger release readiness

Updated: 9 October 2026. The original audit and measured checkpoints are retained below. The final supplied local checks passed: **149 backend regressions, 14 PostgreSQL evaluations, 19 frontend tests and Ruff across 61 files**. Runtime dependency audits reported zero known vulnerabilities at scan time. The final search-only approval case met its expected finding; see the latest report below. These are engineering checks, not independent human assessment or hosted-production evidence. Publication is public and verified; all three remote CI jobs passed at code commit `a1b84d0815a6d19c99a58a9aba75a13c649b2c24` ([verified run](https://github.com/sankalp2515/FactLedger/actions/runs/37932859762)).

## Release decision

| Target | Decision | Conditions |
|---|---|---|
| GitHub repository | Published; public access verified | [sankalp2515/FactLedger](https://github.com/sankalp2515/FactLedger), MIT, `main`; fresh remote Compose/frontend passed. All three CI jobs passed at code commit `a1b84d0` ([run](https://github.com/sankalp2515/FactLedger/actions/runs/37932859762)). |
| Hackathon submission | Worth submitting after final packaging | Publish accessible code, record an actual local workflow under three minutes, verify the video link privately and complete the official entry/disclosure. |
| Public hosted production | **No-go today** | Hosted identity/TLS, restricted-role deployment, operational alerts, durable deletion-ledger replication, restore objectives and load testing need deployment evidence. |

The architecture is appropriate for an early newsroom product. It does not establish capacity for millions of users. A shared artifact volume constrains multi-host deployment; add an object storage adapter and prove distributed controls when actual scale warrants them.

## Defects addressed in this release audit

| Finding | Impact | Repair and evidence |
|---|---|---|
| P1: tenant-scoped worker could not enumerate runs | Documented restricted database role silently left jobs queued | Migration003 provides bounded SECURITY DEFINER identity-only dispatch, pinned search path and revoked PUBLIC execution. Worker sets workspace before claiming. Real nonowner PostgreSQL regression verifies dispatch and cross-tenant denial. |
| P1: missing/false Content-Length bypassed body limit | Multipart parsing could spool oversized unauthenticated input | Streaming ASGI byte cap before parsers; safe413 and partial spool cleanup. Ten regressions include headerless/chunked bodies and the actual composed API. |
| P1: case/run lock inversion, including foreign-key inserts | Actual API/worker smoke reproduced HTTP500 from a PostgreSQL deadlock | Case-before-run locking plus Case FOR NO KEY UPDATE permits worker FK KEY SHARE. Deterministic PostgreSQL tests reproduce both previous failures and verify corrected interleavings. |
| P2: review/case lock inversion | Concurrent editorial decision and draft change could deadlock | Resolve the parent identity, lock Case, then lock ReviewRequest consistently. PostgreSQL concurrency regression verifies behavior. |
| P2: nested News records dropped | Useful publisher records inside News clusters were omitted | Flatten bounded highlight/story records, deduplicate URLs and preserve provider ISO dates as unverified metadata. A regression covers the documented response shape. |
| P2: preflight queries ignored asserted stage | Approval claims received operational-specific negative wording | Use the same stage/measure-aware query planner in preflight and execution. |
| Documentation/branding drift | Old index incorrectly said implementation had not started | FactLedger branding, rewritten README/index, security/changelog and GitHub issue/PR templates. Immutable historical packs retain original bytes. |
| P2: tab keyboard navigation absent | Arrow keys did not move between case tabs | Added roving focus, Left/Right/Home/End selection and labelled panel relationships. Browser and React regression verified the behavior. |

## Verification evidence

Final measurements are recorded after the rebuilt local API/worker acceptance journey. Commands are in the root README and CI. PostgreSQL evaluation runs in a separate process with an actual migrated database; skipped tests do not count as passes.

- Backend regression: 107 passed. One existing Starlette/httpx TestClient deprecation warning remains.
- PostgreSQL evaluation: **14 passed**, including three deterministic concurrency regressions and nonowner tenant/worker checks.
- Frontend: 14 passed; TypeScript, ESLint and production Vite build passed. JavaScript bundle approximately111KB gzip; this is a bundle measurement, not a rendering/load guarantee.
- Ruff passed; Alembic reported no migration drift.
- Pinned Python runtime and frontend production dependency audits found no known vulnerabilities at scan time. Python audit used the complete pinned runtime list with `--no-deps --disable-pip`; inherited unrelated local packages were not represented as shipped dependencies.
- A fresh bounded live SerpApi News probe returned23 result groups with Success. The final actual live API/worker run used2 searches,2 document attempts and8537 tokens, preserving2 evidence excerpts in61.626 active seconds at a configured estimate of$0.0352864. It ended **PARTIAL / BUDGET_EXHAUSTED:documents**; one search reported SEARCH_PROVIDER_NETWORK_ERROR and retained its conservative reservation. This is evidence of live acquisition/extraction and honest failure reporting, not an entirely successful investigation. NVIDIA live inference remains unverified.
- Earlier isolated synthetic backup/restore drill preserved hashes and replayed later deletions to deny restored case/source/export access. It does not establish production RPO/RTO.

The final rebuilt Compose image passed `scripts/smoke_fixture.py`: health, case creation/scope, stale revision rejection, run idempotency, actual durable worker execution, literal source anchors, denial of self approval, separate editor approval, export immutability after draft changes and download denial after deletion. API and PostgreSQL report healthy; the separate worker is running.

The browser journey created synthetic case `c9e3ea25-8861-4cca-9fab-f12dcb41beeb`, confirmed its scope, inspected the plan/fixture label, completed and integrated the run, inspected the preserved source and delivery gap, submitted a cited conclusion, verified researcher decision denial, switched to a separate development editor and approved the qualified conclusion. It downloaded [the FactLedger pack](demo/factledger-evidence-pack-r3.json); canonical payload and preserved source hashes verified. This is an AI-operated role-separation test, not independent human editorial review. [Screenshot](demo/editor-review.jpg) shows actual local UI.

Desktop review was checked at1440×900 and mobile at390×844; mobile DOM document width375 did not overflow the390 viewport and checked visible controls had labels. Case tab arrow/Home focus and selection work in the final browser. This targeted check does not establish full WCAG conformance, cross-browser compatibility or assistive-technology certification.

A bounded local read smoke made40 case-list requests at concurrency5:40 HTTP200 responses, p50 62.30ms, p95 91.62ms. These small-library results are not sustained load/capacity evidence. Core document links and actual configured secret values were scanned across public working files and existing Git history: no matches or broken links found. This targeted scan is not an exhaustive secret detector.

## Hosted-production gates

1. Deploy a separate production environment with HTTPS, exact allowed hosts, secure cookies and high-entropy secrets from a secrets manager. The local Compose configuration deliberately uses development mode.
2. Register OIDC and verify real sign-in/callback, expired and mismatched tokens, workspace membership, revocation and separate researcher/editor accounts. Configuration validation alone is insufficient.
3. Apply migrations using maintenance credentials. API/worker runtime must use a nonowner LOGIN role inheriting evidence_app; prove the full deployed journey with those credentials, not merely policy tests.
4. Configure reverse-proxy body/time limits and shared abuse controls. Application per-IP rate limiting is process-local, so it does not provide a distributed limit.
5. Deploy metrics/log collection and actionable alerts for readiness, queue age, lease failures, storage quota, provider errors and spend. Prove delivery to an operator.
6. Replicate the deletion ledger independently and durably. Encrypt/retain backups, automate retention and perform a production-like restore against measured RPO/RTO.
7. Exercise multiple workers, provider timeouts/restarts, concurrent editors and sustained realistic document workloads under load. Real database regressions are useful but do not replace capacity testing.
8. Establish support, vulnerability reporting, licensing and data handling policy before onboarding real newsroom records.

Remaining product limitations: no OCR; PDF tables/partial extraction need human inspection; unknown dates and source independence remain unknown; model/provider availability is account dependent; cost estimates depend on configured rates; source authenticity and ground reality are not certified. Independent adjudication and customer pilot remain unmet.

## Judging assessment and highest-value improvements

| Criterion | Strength | Improvement with greatest impact |
|---|---|---|
| Idea strength | Clear public-interest insight: delivery stages are often conflated | Lead the demo with one precise, understandable stage mismatch. |
| Originality | Scoped evidence comparison, source-family uncertainty and immutable editorial handoff | Show the difference between related evidence and evidence that establishes the claim. |
| Technical complexity | Durable provider recovery, fenced jobs, tenant isolation, literal anchors and concurrency regressions | Make this engineering visible through one recovery example and test evidence. |
| Usefulness | A repeatable researcher-to-editor workflow with inspection and export | Obtain one researcher/editor walkthrough and document candid feedback; do not claim a pilot before it happens. |
| Meaningful SerpApi usage | Live discovery supplies sources, query provenance and opposing coverage | Record a successful live case with inspectable originals and show how removing search prevents discovery. |

**Assessment:** FactLedger has a credible submission concept and substantial engineering. The largest competitive gaps are demonstrated live-source quality and independent usefulness evidence. No defensible winning percentage can be calculated without the competing entries and judges' decisions. A focused, honest demonstration is likely more valuable before the deadline than adding unrelated features.

Suggested pre-submission priorities: (1) rehearse a concise live case and a labelled deterministic fallback; (2) have a person inspect quotations and the conclusion; (3) obtain brief user feedback; (4) publish reproducible setup and accessible links; (5) include AI disclosure and actual limitations. Contest eligibility, agreement acceptance and final entry belong to the participant.

## Repository packaging

README, setup/API guide, architecture/PRD, contributing workflow, security policy, changelog, CI, issue/PR templates, operational/backup guides, evaluation protocol and submission disclosure are present. The README presentation adapts structural patterns from [PraisonAI](https://github.com/MervinPraison/PraisonAI): a strong opening, concise setup, use cases, architecture and documentation links. Product wording and claims are original. The CI badge targets the actual `verify.yml` workflow on `main`; static badges identify Python, TypeScript and the owner-selected MIT license. A pending badge or configured repository URL is not proof of a completed remote check.

Release checks completed: tracked/history credential scans, core-document links, final diff, public GitHub destination and remote CI were verified. Repeat the appropriate checks for later changes. `.env`, private artifacts, backups, local execution logs and generated dependencies remain excluded. Public screenshots and exports may contain labelled synthetic demonstrations or non-sensitive public-record cases; private provider payloads and participant details are excluded. MIT licensing covers the project's own materials, not third-party captured records.

Official submission requirements and deadline are linked in [submission readiness](submission-readiness.md). This engineering assessment does not assert eligibility, acceptance or a prize.

## Real-case walkthrough and accounting verification — 9 October 2026 IST

The [manual testing guide](manual-testing.md) and README now include precise public-record use cases, a live PM-Surya Ghar approval walkthrough and a no-cost labelled fixture alternative. The root command `docker compose up --build -d` successfully built the frontend/API/worker, migrated PostgreSQL and started the whole stack. Existing volumes and private `.env` were retained. Optional `.env` permits fixture configuration without provider keys; Compose requires version 2.24+.

Fresh checks: 115 backend regressions, 14 PostgreSQL evaluations and 15 frontend tests passed; Ruff lint/format, TypeScript/Vite build, frontend lint and Alembic drift checks passed. The actual API/worker fixture journey passed idempotency, quotation anchoring, independent local-role approval, immutable export after a draft edit and deleted-case download denial. Browser checks verified invalid USD disables Start, valid live limits enable it, exact manual source controls, review status and per-provider Activity display at the existing narrow browser viewport.

Two bounded live SerpApi/Groq cases exercised source attachment, discovery, extraction, guarded quotations, integration, local-role review and JSON export. The retest `ea94e4db-2059-4a5b-97ce-aa88f842f8f1` recorded 2 searches, 4 document attempts, 11254 reported tokens, 33.465 seconds and $0.0272496 configured estimate with zero uncertain reservations. Three literal anchors and three original-download hashes passed; one external source was unavailable. No provider errors occurred on this retest. The initial run exposed a successful empty-news search being classified as failure; the exact successful-empty case is now covered by regression tests. Account errors and other provider failures still remain failures. An initial Groq HTTP 429 retained conservative budget reservations.

**Quality limit:** both small runs remained partial at the document limit. The retest model selected contextual/subsidy evidence and produced subject/period gaps, so the finding stayed insufficient. A preserved official source does not guarantee a correct or complete model interpretation. Qualified editorial workflow success is not an automated accuracy benchmark. Both development reviewer identities were operated by the AI QA runner, not independent people. Public screenshots in this update contain only this public-record case and configured estimates; private provider payloads/packs remain ignored.

Operational API/worker JSON logs and Docker 10 MB × 3 rotation were observed. Durable audit/run events remain in PostgreSQL. New runs pin pricing/provider/model; successful LLM input/output usage reconciles both tokens and estimated USD; pending and unknown outcomes remain visible reservations. The Activity panel, run API and frozen exports include provider breakdowns. Actual provider invoices, centralized log shipping/alert delivery, independent accuracy evaluation, OIDC production login and deployment gates remain unverified requirements for hosting.

Independent read-only code review found no significant regression. Its pending-acknowledgment accounting observation was covered with a failing test and fixed so pending acknowledged searches contribute to uncertain reserved USD. Known-secret/history scanning and core-document link checks are required again before publishing.

## Search-only approval quality test — 9 October 2026

The first measured search-only approval run began with **no manual URL or attachment** and tested the claim “The Union Cabinet approved PM-Surya Ghar: Muft Bijli Yojana in February 2024.” The expected outcome was `SUPPORTED_BY_COLLECTED_EVIDENCE`. That expectation **failed**: the returned finding was `INSUFFICIENT_EVIDENCE`, with unresolved subject, period, stage and missing-comparable-evidence gaps. The run ended `PARTIAL / BUDGET_EXHAUSTED:documents`. Workflow completion does not convert this failed retrieval/evaluation result into successful claim verification.

| Measurement | Observed result |
|---|---|
| Manual source attached | No |
| Search/document attempts | 2 / 6 |
| Validated literal anchors | 2 |
| Original download hashes checked | 5 |
| Groq attempts | 5, including three HTTP 429 rate-limit errors |
| Reported successful model usage | 7,477 input + 1,596 output tokens |
| Budget-accounted tokens | 59,881, including conservative reservations; not all reported billed tokens |
| Active duration | 77.42 seconds |
| Configured estimated USD | $0.0577478, including $0.0319848 uncertain reservations |
| Workflow checks | Idempotency, self-approval denial, review/export and manifest checks passed |
| Expected approval quality | **Failed** |

The second search-only run also failed the expected approval finding and ended partial at the document budget. Unlike the first run, it recorded no provider errors: **8,694 reported tokens, 17.575 seconds, three validated anchors and three download-hash checks**, with a **$0.025755 configured estimate and zero uncertain reservations**. Workflow review/export checks passed. Removing rate limits did not resolve the retrieval/evaluation quality failure.

At this checkpoint the query refinements and final live rerun were still pending. The final measured outcome below supersedes that pending status while preserving both failed-quality runs.

These are sanitized measurements, not a provider invoice or independent accuracy benchmark. Development researcher/editor identities were operated by AI QA. Raw execution reports and provider payloads remain private and are not submission artifacts. Publication and public accessibility are verified; all three remote CI jobs passed at code commit `a1b84d0815a6d19c99a58a9aba75a13c649b2c24` ([verified run](https://github.com/sankalp2515/FactLedger/actions/runs/37932859762)). Use the [demo script](demo-script.md) to show this limitation and any separately labelled manual/fixture fallback transparently.

## Final search-only approval result — 9 October 2026

Run `71dab61d-a01b-425c-9584-b4444fb5e3d6` started without a manual URL and ended **COMPLETED / SUPPORTED_BY_COLLECTED_EVIDENCE**, meeting the expected narrow approval finding. It recorded **2 searches, 2 document attempts, 4,763 reported tokens, 8.244 seconds and $0.0230872 configured estimated USD**, with no provider errors or uncertain reservations. Two literal anchors and two original-download hashes validated; workflow review/export checks passed through AI-operated local identities.

**Source attribution correction:** both accepted anchors, including the approval statement scoped to `2024-02`, map to the secondary article `https://pmsvy-cloud.in/pm-surya-ghar-muft-bijli-yojana-2024/`. The acquired government-hosted PDF contained unrelated Sikkim election-expense material and supplied zero accepted candidates. The earlier attribution of the approval quotation to that PDF was incorrect and has been corrected throughout the release documentation. Host-ranking signals do not authenticate source relevance or authority. Primary-record discovery remains unresolved; an editor should separately inspect the official PIB release through the visibly manual-source workflow. Contextual launch dates in the secondary article are not promoted to verified facts. Approval does not establish installation delivery, household coverage or later operational results.

The rebuilt running image exercised this final live case. Both the latest local key-free fixture and a fresh remote Compose fixture passed; all three remote CI jobs passed at code commit `a1b84d0815a6d19c99a58a9aba75a13c649b2c24` ([verified run](https://github.com/sankalp2515/FactLedger/actions/runs/37932859762)). Local final regression results are **149 backend, 14 PostgreSQL and 19 frontend**, with full Ruff across 61 files passing. Pinned Python runtime and production pnpm audits reported zero known vulnerabilities at scan time. Both delivery-target and earlier-period follow-ups below are inconclusive for negative accuracy.

This selected case meets the expected finding against a collected secondary article, not an authenticated primary record or independent truth assessment. Its primary-source quality gap and the two earlier failed-quality runs remain disclosed. No independent human adjudication, generalized success rate, hosted readiness or guaranteed outcome is inferred.

| Follow-up probe | Finding and measured outcome | Accuracy interpretation |
|---|---|---|
| Delivery target, run `a4a3b4ec-981a-4882-8c6e-4ca3343bb372` | Insufficient evidence; partial, two Groq 429 errors; 2 searches, 5 document attempts, 5 anchors, 43,203 reported/reserved tokens, 19.326 seconds, $0.0475342 configured estimate | No false-positive finding was observed, but provider failures and budget limits make negative-accuracy validation **inconclusive**. |
| Earlier period, run `c4de5e18-ddb5-404c-a183-217cbd59cd14` | Insufficient evidence; `PARTIAL / PROVIDER_ACTIONS_INCOMPLETE`, one search network error; 2 search attempts, 0 documents, 0 anchors, 0 tokens, 63.51 seconds, $0.02 configured estimate | No false-positive finding was observed, but no document evidence was collected. Negative-accuracy validation is **inconclusive**. |

## Publication and remote verification

The release was pushed to public `main` at `cfef80c`; public access was independently checked through the web reader. Public-file/history credential/private-data scans, document links and final diff checks passed. The [first remote CI run](https://github.com/sankalp2515/FactLedger/actions/runs/37931620057) passed frontend verification and a clean fresh Compose fixture journey. Its backend job exposed one budget test that depended on a locally configured provider key. Test setup now blanks provider keys and that specific test supplies a fake key; all 149 backend tests passed locally again. This corrects test isolation without changing application behavior. The corrected code commit `a1b84d0815a6d19c99a58a9aba75a13c649b2c24` passed all three jobs in the [second remote CI run](https://github.com/sankalp2515/FactLedger/actions/runs/37932859762).

The latest local packaged fixture also completed with a literal anchor, role-separated review/export and deletion denial after the final query changes. The passing remote run verified 149 backend tests, 14 PostgreSQL evaluations, the actual API/worker fixture, migration drift and wheel build; frontend lint, types, 19 tests and production build; and a clean key-free Compose fixture. These results bind to code commit `a1b84d0815a6d19c99a58a9aba75a13c649b2c24`. Later documentation commits trigger their own CI runs and are not claimed passing by this record.

Participant-owned recording/upload, eligibility and personal details, Rules/Terms acceptance and final entry remain. An independent researcher/editor trial is recommended; independent adjudication and a customer pilot remain unmet and are not contest prerequisites. Hosted-production gates remain unchanged.

## Fresh-volume startup regression

A subsequent [documentation CI run](https://github.com/sankalp2515/FactLedger/actions/runs/37933366554) passed backend and frontend checks but reproduced an intermittent Docker initialization race. API and worker container creation both tried to populate the empty shared artifact volume, causing `mkdir ... artifacts: file exists` before startup.

Migration now initializes the shared volume once. API and worker mount it with `nocopy: true` and start after successful migration. The image's UID/GID `10001` owns the artifact directory; the existing named volume and its contents are retained. Independent configuration review passed. Two separate fresh-volume cycles passed startup, investigation, literal anchoring, review/export, deletion denial, directory ownership and cross-process artifact read/write checks. The existing local stack also restarted healthy with its retained volumes. See the [verification workflow](https://github.com/sankalp2515/FactLedger/actions/workflows/verify.yml) for the remote result at the latest revision.
