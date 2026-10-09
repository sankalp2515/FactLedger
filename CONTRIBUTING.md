# Contributing

Read the [architecture](docs/architecture.md), [user flows](docs/user-flows.md) and [API guide](docs/api-guide.md) before changing behavior. Preserve source bytes, revision history and existing approved exports; change behavior through explicit revisioned commands.

Keep domain validation deterministic, provider adapters bounded, tenant checks transactional, and errors safe to display. Document architectural trade-offs. Add regressions for meaningful correctness/security/failure changes, run the documented verification commands, and request review before merging. Review source/quote linkage and uncertainty rather than approving model prose on fluency alone.

Never commit `.env`, private artifacts, populated credentials or real newsroom data. Use labelled synthetic cases in tests. Report actual validation results; passing fixtures are not independent accuracy or production capacity evidence. Run the README verification commands and keep public documentation links current.
