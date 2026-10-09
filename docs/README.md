# FactLedger documentation

FactLedger is an implemented newsroom evidence workspace. The name was finalized on 8 October 2026. Internal `product_core` and `evidence-workspace` identifiers stay stable to preserve environments. Historical design reports and immutable exports describe their state at creation.

Start with the [repository README](../README.md), [release readiness](release-readiness.md) and [implementation status](implementation-status.md).

| Reference | Purpose |
|---|---|
| [API/development guide](api-guide.md) | Setup, configuration, API and troubleshooting |
| [UI/UX audit](ui-ux-audit.md) | Friction fixes, design rationale and responsive/keyboard regression checks |
| [Manual testing](manual-testing.md) | Judge walkthrough, real records, measured live test and provider accounting |
| [Production runbook](runbooks/production.md) | Hosted deployment and operational gates |
| [Backup/restore](runbooks/backup-restore.md) | Recovery, deletion replay and retention |
| [Local operations](runbooks/local-operations.md) | Local environment and verification history |
| [Submission readiness](submission-readiness.md) | Judging evidence, demo flow and disclosure |
| [Submission checklist](submission-checklist.md) | Engineering handoff, participant recording and final entry |
| [Demo script](demo-script.md) | 2:50 local screen-recording steps and transparent fallback |
| [PRD](PRD.md) | Product requirements, users and flows |
| [System specification](product-system-spec.md) | Architecture, contracts, data and failure states |
| [Agent design](agent-design.md) | Extraction tools and deterministic safeguards |
| [Implementation plan](implementation-plan.md) | Original milestones; consult status for completion |
| [Execution ledger](execution-ledger.md) | Milestone evidence and remaining gates |
| [Evaluation](../eval/README.md) | Synthetic fixtures and independent evaluation |
| [Research](research.md) | Assumptions and evidence limits |
| [Editable diagrams](factledger.drawio) | diagrams.net architecture source |
| [Historical design canvas](review-canvas.html) | Early review, not the running application |

Naming is final and the owner selected the [MIT License](../LICENSE). Trademark/domain clearance remains a separate owner decision. [sankalp2515/FactLedger](https://github.com/sankalp2515/FactLedger) is published and public. Fresh remote Compose fixture and frontend checks passed; all three remote CI jobs passed at code commit `a1b84d0815a6d19c99a58a9aba75a13c649b2c24` ([verified run](https://github.com/sankalp2515/FactLedger/actions/runs/37932859762)).
