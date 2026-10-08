# Civreniq — 10 target-user use cases
8 October 2026 · All names, quantities and situations below are illustrative fixtures, not real-world findings.

Each case uses the same core workflow: scope → plan → SerpApi discovery → source acquisition → stage/quantity comparison → gaps → researcher/editor review → frozen pack. These are ten practical checks within one product, not ten unrelated products.

## UC-01 — Hospital inaugurated versus serving patients
**User:** health-desk researcher. **Input:** “District A's 200-bed hospital is fully operational as of 30 September.”
**Problem:** announcement and inauguration coverage can be mistaken for service delivery.
**Investigation:** find project aliases, sanction, inauguration record, staffing/service notices and dated operating records. Trace repeated articles to source announcements.
**Output:** stage timeline with inaugurated observation; operation evidence if available; otherwise exact missing evidence and qualified insufficient finding.
**Acceptance:** inauguration alone must not support OPERATIONAL. A contemporaneous service record can support operation but not necessarily all 200 beds. Physical availability, staffing and full service remain distinct.

## UC-02 — Budget allocated versus money spent
**User:** public-finance researcher. **Input:** “₹500 crore was spent on Programme B during FY 2025–26.”
**Problem:** budget allocation, sanction, release and expenditure get collapsed into one amount.
**Investigation:** search budget documents, release orders, expenditure statements and audit references; compare exact period and programme boundary.
**Output:** side-by-side funding ledger and deterministic conversion trail.
**Acceptance:** ₹500 crore allocated is CONTEXT, not support for expenditure. ₹5,000 million normalizes to the same magnitude only with matching currency/period/measure. Fiscal/calendar-year mismatch stays incomparable.

## UC-03 — Road sanctioned versus open to traffic
**User:** infrastructure reporter. **Input:** “The entire 80 km Corridor C opened by August.”
**Problem:** sanctioned length or a completed segment does not prove entire-route operation.
**Investigation:** identify sections, approvals, contractor/status records, opening notices and contrary dated reporting.
**Output:** scoped segment evidence and full-route gap checklist.
**Acceptance:** one 20 km opening does not support 80 km; overlapping segment totals cannot be summed twice. Absence of an opening notice is not proof of closure.

## UC-04 — Tap installed versus reliable water supply
**User:** civic-services journalist. **Input:** “All 10,000 households in Block D now receive daily tap water.”
**Problem:** connection counts are not frequency, reliability or universal service.
**Investigation:** source dated connection dashboards, service reports, definitions and available inspection records; separate registered households from serviced households.
**Output:** installation versus service metrics, denominator and evidence limitations.
**Acceptance:** installation data cannot support daily supply; survey and administrative coverage must be labelled and cannot be blended. If field confirmation is necessary, produce that task rather than a fabricated verdict.

## UC-05 — School building completed versus functional school
**User:** education researcher. **Input:** “School E is functioning for 800 students.”
**Problem:** building completion or inauguration does not establish staffing, enrollment or teaching.
**Investigation:** find completion certificate, staffing/enrollment records and dated service notices for the exact school.
**Output:** physical stage ledger plus separate student/staff metrics.
**Acceptance:** seating capacity is not enrollment; academic-year scope required. An unavailable attendance record leaves instruction continuity unverified.

## UC-06 — Housing approved versus occupied
**User:** housing-desk researcher. **Input:** “2,000 families have received homes under Scheme F.”
**Problem:** approval, completion, allotment, handover and occupancy are different events.
**Investigation:** project reports, completion numbers, allotment/handover records and definitions of “received.”
**Output:** disambiguated claim and stage/beneficiary comparison.
**Acceptance:** first ask/confirm whether received means handover or occupancy. Approved units cannot support occupied homes. No personal beneficiary identifiers are needed for aggregate verification.

## UC-07 — Jobs promised versus people placed
**User:** labour-policy researcher. **Input:** “Training Initiative G created 5,000 jobs this year.”
**Problem:** training registrations, completions, placement offers and sustained employment differ.
**Investigation:** find programme definitions, dated outcome reports and methodology; trace promotional articles to originating claims.
**Output:** registration/training/placement/outcome metrics with attribution.
**Acceptance:** causality (“created”) cannot be established from placement counts alone. Unique persons and reporting period required; duplicate offers are not distinct jobs. Qualified conclusion avoids a causal certification.

## UC-08 — Solar capacity approved versus commissioned
**User:** energy correspondent. **Input:** “Project H added 100 MW of operating solar capacity.”
**Problem:** approved capacity, construction and commissioning are different, and capacity is not energy generated.
**Investigation:** approval, commissioning notices, grid-connection records and available generation references.
**Output:** stage/measurement matrix with MW and MWh kept separate.
**Acceptance:** approved MW does not support operating MW; MWh cannot be numerically compared to MW without time/method assumptions. A commissioning source's stated scope is preserved.

## UC-09 — Benefit registrations versus actual payments
**User:** welfare-policy journalist. **Input:** “100,000 beneficiaries received Programme I payments in September.”
**Problem:** eligibility/registration counts, approved accounts and disbursed payments diverge.
**Investigation:** programme definition, dated aggregate disbursement record and reporting methodology.
**Output:** registered/approved/paid metrics, period and unique-beneficiary limitations.
**Acceptance:** transaction count is not unique people; cumulative payments do not support one month's beneficiaries. No private bank records or personal-data scrape. Missing public disbursement evidence produces an explicit gap.

## UC-10 — Update an already approved project claim
**User:** researcher and editor returning to a road/hospital case. **Input:** a prior approved case plus a newly published operation record.
**Problem:** changed web pages and new records can silently invalidate an old assessment.
**Investigation:** new run, fresh discovery, new source versions, comparison against the prior case.
**Output:** revision diff showing new date/stage/evidence, proposed changed conclusion and a new review request.
**Acceptance:** prior approved/exported pack remains byte/content reproducible; new evidence cannot backdate operation or inherit old approval. Editor approves a new revision explicitly.

## Test matrix and user value

| Case | Primary semantic trap | Valuable outcome |
|---|---|---|
| 01 | Inaugurated ≠ operational | Don't mistake ceremony for services |
| 02 | Allocated ≠ expended | Report the correct funding measure |
| 03 | Segment ≠ whole route | Avoid geographic/denominator inflation |
| 04 | Installed ≠ reliable service | Identify needed ground/service evidence |
| 05 | Capacity ≠ attendance/function | Separate building and education outcomes |
| 06 | Approved ≠ handover/occupancy | Clarify what beneficiaries received |
| 07 | Placement ≠ causal job creation | Avoid unsupported outcome attribution |
| 08 | Approved MW ≠ operating MW ≠ MWh | Keep stages and units correct |
| 09 | Transactions ≠ unique recipients | Avoid beneficiary-count distortion |
| 10 | New evidence ≠ retroactive truth | Reproducible correction workflow |

Engineering owns fixture creation and automated assertions for all ten. Human subject-matter validation of real cases remains an external evaluation dependency; the project reviewer is not expected to become the newsroom editor for all ten examples. These examples prove intended behavior when tests are implemented, not current functioning software.
