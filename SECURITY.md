# Security policy

FactLedger is a first release. Hosted deployments must satisfy the [hosting prerequisites](docs/architecture.md#hosting-and-recovery). Development identity switching must never be exposed as production authentication.

## Report privately

Do not put exploit details, credentials, personal data or private records in public issues. Private vulnerability reporting is enabled for this repository: use [Security → Report a vulnerability](https://github.com/sankalp2515/FactLedger/security/advisories/new). No dedicated security email or response SLA has been established.

Provide affected commit, impact, prerequisites and a minimal reproduction using synthetic records. Do not test another workspace or deployment without authorization.

## Boundaries

- Production uses OIDC plus workspace membership/role authorization.
- Database isolation requires the documented nonowner role and migrations; migration credentials are separate from runtime credentials.
- Fetching validates public HTTPS destinations/redirects. PDF parsing is resource bounded and network disabled; complete OS sandboxing is not claimed.
- Source/model content is untrusted. Model outputs are proposals constrained by literal evidence guards, never executable instructions.
- Secrets remain in environment configuration. Rotate exposed keys; never attach `.env`.
- Deletion restricts downloads immediately and retains a deletion ledger for restore replay.

Passing tests and dependency scans do not establish vulnerability-free deployment. The owner should set support/disclosure commitments before offering a hosted service.
