# Changelog

## Unreleased — FactLedger first release

- Scoped claims and versioned investigation cases.
- SerpApi discovery, preserved HTML/PDF sources and literal quotation anchors.
- Groq, NVIDIA, OpenAI, Anthropic and Gemini extraction adapters with deterministic guards and provider-specific usage accounting.
- Delivery, funding and metric comparisons, gaps and source-family hypotheses.
- Durable jobs, budgets, fenced leases, pause/cancel/resume and acknowledgment recovery.
- Workspace roles, separate editorial review and immutable JSON/Markdown packs.
- Compose deployment, operational runbooks, CI and synthetic evaluation fixtures.
- Final product branding: FactLedger.
- Responsive workbench with paginated evidence, separate source browsing, quotation navigation and accessible dialogs.
- Structured operational logs and pinned provider pricing with reported token reconciliation and visible uncertain reservations.
- Search selection balances relevance, public-record cues, opposing discovery and source diversity; URL identity preserves meaningful query ordering.
- Bounded extraction retains relevant regions of long records and discloses omitted material.
- Model rate limits use bounded, cancellable `Retry-After` waits; explicitly rejected requests release reservations while uncertain network outcomes remain accounted for.
- Compact literal extraction windows reduce per-request reservations; incomplete-run notices explain recovery and retain technical diagnostics.
- One-command, key-free Docker fixture startup, clean-stack CI, publication checks and MIT licensing.

See [hosting and recovery](docs/architecture.md#hosting-and-recovery) for deployment requirements and [user flows](docs/user-flows.md) for usage.
