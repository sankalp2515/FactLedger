# FactLedger submission checklist

Use this handoff with the [release audit](release-readiness.md), [judge walkthrough](../README.md#try-it-as-a-judge) and [AI disclosure](submission-readiness.md#ai-assistance-disclosure-draft). A checkbox is complete only when its evidence exists. Local verification and repository publication do not submit a contest entry.

## AI engineering and repository handoff

- [x] Document the product, architecture, reproducible Compose setup and provider configuration.
- [x] Keep fixture mode clearly labelled and usable without provider keys.
- [x] Define a search-only default judge flow; distinguish optional manual attachments and historical attachment-assisted measurements.
- [x] Add owner-selected MIT licensing, copyright 2026 Sankalp.
- [x] Disclose AI assistance, synthetic checks, local development reviewer identities and evaluation limits.
- [x] Run final local regression checks: 149 backend, 14 real PostgreSQL and 19 frontend tests; Ruff across 61 files passed. The rebuilt running image completed the final live approval case; an earlier packaged key-free fixture journey passed.
- [ ] Complete the stronger fresh final packaged acceptance check and inspect remote CI after publication.
- [x] Reproduce a bounded search-only live case: the final approval test completed with support, two anchors, no provider errors and $0.0230872 configured estimate. Preserve disclosure of the two earlier failed-quality runs.
- [ ] Recheck public files/history for credentials and private data; verify document links and inspect the final diff.
- [ ] Push the authorized release to [sankalp2515/FactLedger](https://github.com/sankalp2515/FactLedger), verify public accessibility and inspect remote CI.

The badges link to the actual workflow; they do not certify a pending run. Screenshots contain labelled synthetic demonstrations or public-record cases. Hosted production remains gated by the [production runbook](runbooks/production.md).

Final supplied local checks: **149 backend tests, 14 PostgreSQL evaluations, 19 frontend tests**, plus Ruff across 61 files. Pinned Python runtime and production pnpm dependency audits reported zero known vulnerabilities at scan time. The [2:50 demo script](demo-script.md) and [judge scorecard](submission-readiness.md#judge-scorecard) reflect the final successful narrow approval result and preserve the earlier failures. Remote CI, stronger final packaged acceptance and earlier-period accuracy checks remain pending. The delivery-target follow-up is inconclusive because of provider errors and budget limits.

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
- [ ] Clearly disclose that independent 100-pair adjudication and a customer pilot remain unmet. They are product-validation goals, not contest prerequisites.

Do not replace independent human evidence with AI-operated role-switching, synthetic fixtures or an invented accuracy/adoption claim. No hosted production readiness, contest eligibility or award outcome is asserted by this checklist.
