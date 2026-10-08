# Full-product execution ledger

Plan: implementation-plan.md plus engineering-review.md. User authorized full implementation on 8 October 2026, including configured local SerpApi/Groq/NVIDIA integrations. Do not repeat design authorization requests. Branding remains FactLedger.

## Execution decisions

- Use independent implementation workstreams for backend/domain, investigation/adapters, frontend and operations, with shared interfaces agreed before work. User requested collaborative engineering.
- Ruling: use PostgreSQL-polled durable jobs instead of Redis dispatch initially. The accepted review identifies this simpler transport alternative; the small initial envelope does not justify a second durable receipt protocol. PostgreSQL leases/fencing remain mandatory. Cost if wrong: add Redis as a wake-up transport without changing correctness.
- Ruling: local artifact storage behind authenticated API is the default; keep the storage function as the future S3 adapter seam. This avoids unreviewed distribution obligations and public bearer URLs. Docker volumes persist artifacts. Cost if wrong: swap adapter before horizontal API scaling.
- Use SQLite only for fast isolated tests; verify actual PostgreSQL transactions and application flows on the Docker stack.
- Full first-release scope stays required; pilot/independent annotations and public release are distinct external gates.

## Tasks / acceptance tracking

- [x] 1. Identity, memberships, cases, versions, revisions and tenant isolation
- [x] 2. Immutable source/extraction artifacts and authenticated access
- [x] 3. Durable runs, reservations, events, leases, state transitions and idempotency
- [x] 4. SerpApi Search/News adapters and provenance
- [x] 5. Safe public/PDF acquisition with partial coverage
- [x] 6. Anchored evidence, quantities, stage/funding/service metrics and findings
- [x] 7. Lineage and accessible research workbench
- [x] 8. Bounded adaptive investigation and recovery
- [x] 9. Intake, library, notes, membership and frozen review
- [x] 10. Reproducible packs and revision diff
- [x] 11. Compose, CI, migration/restore/deletion/retention and measured checks
- [ ] 12. Evaluation, live proof, setup, demo and criteria evidence

## Judging evidence

Idea strength: UC-01 stage trap and UC-02 funding semantics. Originality: stage/metric ledger + original-source lineage + immutable editorial case. Technical complexity: bounded adaptive research, anchored versions, worker fencing and review transactions. Usefulness: completed researcher/editor journey and reusable exports. Meaningful SerpApi usage: persisted live Search/News queries and purposeful follow-up; no decisive snippet evidence.

## Verification closeout

See implementation-status.md for 95 backend, 10 PostgreSQL operations/evaluation and 14 frontend passing tests, live provider proof with partial coverage, independent review corrections, browser handoff/export, concurrency measurements and restore evidence. Task 12 engineering tooling/setup/live demonstration is implemented; independent annotations, customer pilot, final recorded submission demo and public-release gates remain open. Production identity/TLS, full accessibility conformance and realistic deployment load are unverified.
