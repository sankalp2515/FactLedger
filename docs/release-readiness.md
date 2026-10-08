# FactLedger release readiness

Assessment date: 8 October 2026. This record distinguishes repository preparation, a locally running hackathon demonstration and hosted production. It supersedes older branding and test totals. Tests described as synthetic are engineering checks, not independent human assessment.

## Release decision

| Target | Decision | Conditions |
|---|---|---|
| GitHub repository | Prepared locally; publication pending | Owner supplies target repository/visibility and chooses a license. No remote or public URL is claimed. |
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

README, setup/API guide, architecture/PRD, contributing workflow, security policy, changelog, CI, issue/PR templates, operational/backup guides, evaluation protocol and submission disclosure are present. The README presentation draws on structural patterns from [FastAPI](https://github.com/fastapi/fastapi/blob/master/README.md), [Immich](https://github.com/immich-app/immich/blob/main/README.md) and [PostHog](https://github.com/PostHog/posthog/blob/master/README.md); product wording and claims are original. No CI badge, hosted demo, license or public repository is invented.

Before pushing: run tracked/history secret checks and core-document link checks, inspect the final diff, add the owner's chosen license, configure the exact GitHub destination and run the remote CI after publication. `.env`, private artifacts, backups, local execution logs and generated dependencies remain excluded. Public screenshots and fixture exports must contain only explicitly synthetic data.

Official submission requirements and deadline are linked in [submission readiness](submission-readiness.md). This engineering assessment does not assert eligibility, acceptance or a prize.
