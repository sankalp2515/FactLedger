# Research record

Research date: 8 October 2026. This is desk research, not customer validation. Evidence below supports problem selection; product differentiation, demand, willingness to pay, and performance remain hypotheses. No user interviews, competitor account trials, or representative Indian newsroom workflow study were conducted.

## Evidence register

| ID | Primary source | Finding | Design consequence | Limitation |
|---|---|---|---|---|
| R1 | [Full Fact methodology](https://fullfact.org/about/how-we-fact-check/) | Understand the claim and assumptions, gather evidence, prefer primary documents, consult experts when needed, and review before publication. | Scope confirmation, primary-document tracing, human notes, separate review. | One organization's published practice; not a demand study. |
| R2 | [Full Fact live checking](https://fullfact.org/blog/2025/apr/multitasking-ai-tools-and-22785-words-of-preparation-how-we-live-fact-check/) | Teams prepare shared source material and coordinate claim scoping, investigation, and editorial review in shared documents. | Persistent cases, reusable evidence, assignment, review handoff. | Live checking is demanding; v1 targets desk investigations, not live broadcast latency. |
| R3 | [IFCN 2024 report, published 2025](https://www.poynter.org/wp-content/uploads/2025/03/2.Facts-Report-March-2025-.pdf) | Survey of 141 organizations: nearly 90% identify funding concerns; 73.7% have at most ten full-time employees. Documented sourcing is a professional requirement. | Small-team deployment, explicit cost limits, portable evidence exports. | Global network sample; funding pressure does not establish willingness to pay. |
| R4 | [Reuters Institute India 2025](https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2025/india) | WhatsApp was named the largest misinformation threat by 53% of surveyed Indian respondents; trust in news was 43%. | Public claims are a relevant Indian problem; permit pasted claim intake. | Mainly English-speaking online sample, not nationally representative. No private WhatsApp access assumed. |
| R5 | [FYI design probe, August 2026](https://arxiv.org/abs/2608.06804) | Exploratory study of 22 users found AI/manual combinations and visual evidence inspection important for auditing AI. | Evidence workbench and human decisions are core, not an optional appendix. | Preprint, small exploratory sample, structured-data claims rather than the entire open web. |
| R6 | [Deep Research Bench](https://arxiv.org/abs/2506.06287) | Evaluation covers multi-step web research and identifies evidence gathering and verification failures in tested agents. | Evaluate evidence precision, completeness, and abstention separately from report readability. | Historical models and benchmark tasks; not a claim about current competitor accuracy. |
| R7 | [Google Fact Check Explorer training](https://newsinitiative.withgoogle.com/resources/trainings/verification/google-fact-check-tools/) | Finds published fact checks and publisher verdicts. | Find prior work before investigating; preserve attribution and date. | Existing-check discovery cannot guarantee coverage of new claims. |
| R8 | [Google Fact Check usability study](https://arxiv.org/abs/2402.13244) | Study found matches for 15.8% of 1,000 COVID-related false claims; wording affects retrieval. | Use claim variants and search beyond published fact checks. | Specific dataset and 2024 study; not a current general coverage estimate. |
| R9 | [Full Fact AI](https://fullfact.org/ai/) | Offers monitoring, checkable-claim detection and repeat-claim matching; expert investigation remains central to its described workflow. | Our candidate wedge is evidence assembly and editorial handoff after claim selection. | Feature descriptions do not prove competitors lack equivalent capabilities. |
| R10 | [Meedan Check](https://meedan.org/check) | Tipline intake, community questions and verification work already have specialist products. | Focus initial scope on the investigation case, with manual intake and portable outputs. | No hands-on competitive trial performed. |
| R11 | [Perplexity research](https://www.perplexity.ai/en-GB/hub/products/deep-research) | Advertises research planning, multi-source synthesis and cited reports. | Citations and planning alone cannot be our differentiation. | Vendor claims; no independent comparison conducted. |
| R12 | [SerpApi Search](https://serpapi.com/search-api), [News](https://serpapi.com/google-news-api), [Scholar](https://serpapi.com/google-scholar-api) | Structured search discovery, localization, news chronology and scholarly references support investigative discovery. | Search tools feed evidence acquisition; fetched source text supplies claim evidence. | Search is not full-text access or truth certification; individual metadata fields may be absent. |
| R13 | [Hackathon site](https://serpapi.github.io/serpapi-india-hackathon-2026/), [Rules](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html) | Knowledge & Public Interest includes research and news literacy. Material search use and reviewable functioning code are required; judging has no fixed weights. | Select Knowledge & Public Interest by user purpose; expose reproducible search provenance. | No track entry counts or winning probabilities are public. |

## Pain synthesis: observations versus hypotheses

Observed: professional verification involves scoping, gathering primary evidence, understanding context, shared documentation and editorial review [R1–R2]. Small organizations have resource pressure [R3]. AI outputs require inspection [R5–R6]. Tools for claim detection, tiplines, research and existing-check discovery already exist [R7–R11].

Hypotheses to test: researchers lose material time assembling quote-level provenance; editors repeatedly reopen links to reconstruct reasoning; repeated reporting is mistaken for independent corroboration; policy/project stage confusion creates recurring errors; preserving cases would reduce rework. These are plausible design hypotheses, not measured prevalence claims.

## Candidate-user comparison

| User | Work outcome | Search fit | Main uncertainty | Decision |
|---|---|---|---|---|
| Newsroom researcher checking public claims | Editor-reviewable evidence case | Strong, public documents and news | Adoption and time saved | Primary |
| Policy analyst at NGO | Brief or advocacy evidence pack | Strong | Different review conventions | Secondary after pilot |
| General consumer | Quick yes/no answer | Moderate | Low patience, sensitive trust and distribution | Later |
| Academic researcher | Literature synthesis | Strong Scholar fit | Mature alternatives, paywalls, domain depth | Later |
| Investor/vendor diligence analyst | Commercial risk decision | Strong | Paid registries and legal/financial domain needs | Separate future product |

## Alternatives and competitive positioning

1. General research assistant: broad usage, easy onboarding, strong incumbents, weak specific adoption reason.
2. Consumer claim checker or browser extension: easy claim intake, valuable public use, but distribution, private media access and overtrust are harder; unsupported claims often need offline work.
3. Evidence case workspace: lower initial audience breadth, clear editorial handoff and reusable work; human validation and source quality are essential. **Selected.**

Candidate advantage: original-source lineage, date/definition/stage comparison, explicit evidence gaps, preserved quote anchors, and review history in one case. This is a testable product proposition, not a claim of world-first invention.

## Validation plan before product commitment

Recruit five researchers and two editors from at least three Indian newsrooms or verification organizations; no outreach has been sent. Ask each to walk through a recent public-source investigation with identifying information removed. Record tasks, tool changes, source selection, handoff expectations, rework and blockers. Avoid asking whether they like the concept.

Then test the proposed workflow with at least ten matched claim investigations: compare existing workflow against the prototype, counterbalance order, independently review outputs, and measure active time to an editor-accepted case, unsupported assertions, evidence omissions and reviewer reconstruction time. Record denominators; do not extrapolate to all journalists.

Adoption gate proposed: at least three of five researchers choose to use it on a second real task; editors can reproduce every substantive exported assertion; median active time decreases at least 30% without worse evidence quality. These are goals, not achieved results. If discovery shows collection is already efficient but review is the bottleneck, focus on review integration. If source access dominates, change source strategy before scaling AI.

Grok Bot could provide additional search leads if the user opens it later. Any bot-generated pain claims would still require direct verification and user research.

## 8 October finalization supplement

| ID | Primary source | Verified observation | Product consequence | Limit |
|---|---|---|---|---|
| R14 | [Factiverse](https://www.factiverse.ai/) | Describes evidence checking for media/research and shows supported/disputed/mixed claim states. | Direct competitive overlap: evidence relations/citations alone are not novel. Focus on delivery-stage records and revision-bound editorial cases. | Vendor description; no account trial or feature-exhaustive comparison. |
| R15 | [CAG health infrastructure performance audit](https://www.cag.gov.in/uploads/download_audit_report/2024/Full_English_PHIMS-066a38e83d51cd7.42146357.pdf) | The official-source search excerpt identifies non-functional PHCs and attributes the information to department data. | Operation is a material evidence dimension, not an automatic consequence of construction. | PDF metadata showed 459 pages, but subsequent text fetches timed out; the whole report was not studied. This is a research lead, not decisive product evidence. Historical audit scope is not current status or newsroom-pain prevalence. |
| R16 | [Union Budget documents](https://www.indiabudget.gov.in/doc/), [Agriculture demand for grants](https://www.indiabudget.gov.in/doc/eb/sbe1.pdf) | The opened 2026–27 agriculture demand document labels Actual 2024–25, Budget 2025–26, Revised 2025–26 and Budget 2026–27 separately. | Preserve measure/period; do not equate allocation with spending. | The expenditure-profile PDF failed to open, so the smaller demand document was inspected instead. No live product evidence acquisition is claimed. |
| R17 | [Hackathon Rules](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html), [Terms](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html) | Require functioning public submission and AI disclosure; original participant materials remain theirs, but submission grants an organizer evaluation/promotion license and is not confidential. | Explicit publication/license gate; do not list AI as a human teammate or expose private evidence/secrets. | Read governing text before submitting; no legal-clearance opinion. |

Final problem narrows general public-claim verification to public spending and project-delivery evidence. This is our design inference from source structure and professional verification workflow, not a completed user study. We have not shown that competitors cannot implement this or that customers will pay.

Name screen: exact “FactLedger” and contextual/domain-string searches returned no indexed exact match in performed public searches on 8 October. Registry and domain availability checks are incomplete. [Naming/IP record](naming-and-ip.md) documents limitations. Working brand is finalized for this design; legal exclusivity is not claimed.

Track remains Knowledge & Public Interest. Deadline reconfirmed as 10 October 2026, 23:59 IST. The full design is not silently turned into a smaller hackathon-only scope; readiness requires functioning software and disclosed validation limits.
