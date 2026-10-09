# FactLedger submission checklist

Use this handoff with the [release audit](release-readiness.md), [judge walkthrough](../README.md#try-it-as-a-judge) and [AI disclosure](submission-readiness.md#ai-assistance-disclosure-draft). A checkbox is complete only when its evidence exists. Local verification and repository publication do not submit a contest entry.

## AI engineering and repository handoff

- [x] Document the product, architecture, reproducible Compose setup and provider configuration.
- [x] Keep fixture mode clearly labelled and usable without provider keys.
- [x] Define a search-only default judge flow; distinguish optional manual attachments and historical attachment-assisted measurements.
- [x] Add owner-selected MIT licensing, copyright 2026 Sankalp.
- [x] Disclose AI assistance, synthetic checks, local development reviewer identities and evaluation limits.
- [x] Run final local regression checks: 149 backend, 14 real PostgreSQL and 19 frontend tests; Ruff across 61 files passed. The rebuilt running image completed the final live approval case; an earlier packaged key-free fixture journey passed.
- [x] Complete fresh packaged acceptance: remote clean Compose fixture passed; the latest local fixture also passed worker completion, quotation anchoring, review/export and deletion checks.
- [x] Confirm full remote CI after the environment-independent test correction: all three jobs passed at code commit `a1b84d0815a6d19c99a58a9aba75a13c649b2c24` ([run](https://github.com/sankalp2515/FactLedger/actions/runs/37932859762)).
- [x] Reproduce a bounded search-only live case: the final approval test completed with support against a secondary article, two anchors, no provider errors and $0.0230872 configured estimate; primary-record discovery remains unresolved. Preserve disclosure of the two earlier failed-quality runs.
- [x] Recheck public files/history for credentials and private data; verify document links and inspect the final diff.
- [x] Push the authorized release to [sankalp2515/FactLedger](https://github.com/sankalp2515/FactLedger) and verify public accessibility (`main`, initial release `cfef80c`). Full remote CI is tracked separately above.

The badges link to the actual workflow; they do not certify a pending run. Screenshots contain labelled synthetic demonstrations or public-record cases. Hosted production remains gated by the [production runbook](runbooks/production.md).

The passing CI evidence binds to the exact code commit above. Later documentation commits trigger their own workflow runs; this checklist does not pre-claim their result.

Final supplied local checks: **149 backend tests, 14 PostgreSQL evaluations, 19 frontend tests**, plus Ruff across 61 files. Pinned Python runtime and production pnpm dependency audits reported zero known vulnerabilities at scan time. The [2:50 demo script](demo-script.md) and [judge scorecard](submission-readiness.md#judge-scorecard) reflect the successful narrow approval result and preserve earlier failures. Public release and fresh packaged acceptance passed. All three remote CI jobs passed at code commit `a1b84d0815a6d19c99a58a9aba75a13c649b2c24` ([verified run](https://github.com/sankalp2515/FactLedger/actions/runs/37932859762)). Both delivery-target and earlier-period negative-accuracy checks are inconclusive because of provider failures and incomplete evidence.

## Participant recording, entry and agreement

Requirements below follow the [official rules](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html), checked 9 October 2026.

- [ ] Confirm every contributor is eligible: age 18+, India resident, eligible under the exclusions; team size at most five.
- [ ] Supply accurate lead name, email, mobile, occupation and experience; list additional contributors with names/emails.
- [ ] Select a track, declare prior project existence and community source.
- [ ] Record the actual local workflow under three minutes, showing SerpApi's material role; label fixtures and partial results.
- [ ] Upload the video and verify access in a private/incognito window without an access request.
- [ ] Include the public repository, SerpApi explanation and AI-tool disclosure; confirm the setup instructions work.
- [ ] Personally review and accept the [Rules and Terms](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html).
- [ ] Submit through the GitHub-authenticated form before **10 October 2026, 23:59 IST**; verify submitted status and receipt. A saved draft is incomplete.

## Independent usefulness evidence

- [ ] Ask a researcher/editor to try a case and inspect the preserved quotation and conclusion. Record their consented, candid feedback, including friction and errors.
- [x] Clearly disclose that independent 100-pair adjudication and a customer pilot remain unmet. They are product-validation goals, not contest prerequisites.

Do not replace independent human evidence with AI-operated role-switching, synthetic fixtures or an invented accuracy/adoption claim. No hosted production readiness, contest eligibility or award outcome is asserted by this checklist.
