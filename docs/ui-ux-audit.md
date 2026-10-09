# UI/UX review and verification

FactLedger's interface is an evidence workbench for researchers and editors. This review prioritizes finding a case, inspecting a preserved quotation, understanding uncertainty, and making an editorial decision without losing context.

## Friction and implemented fixes

| Friction | Severity | Implemented change |
|---|---|---|
| Every evidence card repeated a full comparison; sources followed the same long list | High | Short two-line previews, bounded record pages, separate Sources view; full quotation, rationale and comparison in the source dialog |
| Reader occupied different positions at different widths and pushed review actions down | High | Consistent modal reader; editor decisions remain in their own panel |
| Source loading failure hid an already-loaded assessment | High | Full evidence assessment renders independently of source-fetch success; retry remains available |
| Mobile navigation relied on icons and many horizontal tabs | High | Visible navigation labels and a native Case view selector |
| Fixed card content overflowed narrow screens | High | Grid tracks and flex children can shrink; text wraps; data tables have an intentional labelled scroll region |
| Raw observation IDs and JSON were required for corrections, with silent parse failures | High | Observation selector, supported metadata field selector, labelled value and reason; dates use native validation |
| Scope, original claim, revision comparisons and all run checkpoints consumed space continuously | Medium | Expandable disclosures; event pagination and newest-first/error filtering |
| Activity's error filter omitted failed source acquisition events | Medium | Includes unavailable, exhausted and cancelled outcomes alongside provider errors |
| Long collections were unbounded | Medium | The case library shows four cases per server page; evidence, sources, families, gaps, notes, revisions and review lists use reusable pagination, with two-record defaults |
| Modal background remained reachable by keyboard | Medium | Portal dialog, inert application background, focus containment, Escape dismissal and focus restoration |
| Quotation could be buried deep inside preserved source text | Medium | Automatic positioning and an explicit Jump to quotation control inside the source pane |
| Search fired on every character and terminal runs continued polling | Low | Debounced case search; terminal run polling stops |

## Layout and design rationale

The existing forest-green identity remains, with neutral surfaces, consistent borders and compact spacing. Interface headings use the system sans-serif family for fast scanning; preserved quotations retain Georgia to distinguish records from application instructions. Colour is accompanied by relation text and icons.

The application navigation and case header stay in view. The active workbench pane uses the remaining viewport height. Records have bounded pages; sources and ledger tables scroll within dedicated regions. Full original material is never deleted or rewritten to fit a screen. Expanding a disclosure or reading a long document can require scrolling inside that region. This is intentional: hiding material facts merely to eliminate all scrolling would undermine evidence inspection.

The shared PagedList component centralizes page ranges, disabled controls, collection shrink handling, and positioning when advancing pages. The reader dialog is shared between research and frozen editorial review. Corrections only expose server-supported mapping metadata; stage/value changes still require re-analysis.

## Manual regression checklist

1. Open Case library, search a title, clear search, change filters, and advance a page. Open a case.
2. Expand Original claim and Confirmed scope; confirm the full text is still available. Collapse them again.
3. Open Evidence, then a record. Check the full quote, rationale and comparison. Use Jump to quotation; the highlighted literal passage should be visible within the source pane.
4. Tab and Shift+Tab around the reader. Background navigation must be unreachable. Press Escape; focus must return to the opening record.
5. Open Sources and inspect/download a preserved original. Available and unavailable captures must remain distinct.
6. Open Delivery stages and Correct observation. Select an observation and a metadata field; check required input/date validation. Cancel to avoid changing an existing case, or save on a disposable case with a reason.
7. Open Activity. Expand Run event history, change Show events, and use pagination. Unavailable sources must appear in the incomplete-outcomes filter.
8. Open Editor review. Switch Conclusion, Evidence and Gaps. Inspect a cited source, dismiss it, and verify that the decision form remains usable. Frozen records must offer no research corrections.
9. Repeat at 1440x900, 900x800, 390x844 and 320x700. Mobile navigation labels and Case view must remain readable; card content must not scroll horizontally. Wide ledgers may scroll in their labelled region.
10. Check Workspace and New case forms at a narrow width. Invalid required inputs must prevent submission; errors and retry controls remain visible.

Automated regressions cover collection pagination and shrink handling, keyboard tab navigation, correction payloads, frozen source inspection, source-fetch failure, literal anchor safety, budgets and source-family interaction. See the verification record below. This is targeted QA, not an independent WCAG certification or exhaustive device matrix.

## Verification record

On 9 October 2026 IST:

- Frontend lint, 19 automated tests, TypeScript checking and production bundling passed.
- The rebuilt Docker Compose stack started successfully; API and PostgreSQL health checks passed.
- The no-cost API/worker smoke journey completed investigation, literal-anchor inspection, review, export and disposable-case deletion.
- Browser QA verified mobile Case view navigation, Sources, paged events, incomplete-outcome filtering, frozen review sections, source inspection and Workspace/New case layouts.
- Modal keyboard checks verified Shift+Tab from the close control wraps to the last action, Tab wraps back, Escape closes, and focus returns to the opening evidence card. Background navigation disappears from the accessible tree while the modal is open.
- A real preserved PIB record was inspected without new provider calls. Its quoted passage was positioned inside the source pane; the full comparison remained available. The frozen review reader offered no research correction actions.
- At 390x844, the document width was 390px and the evidence pane's scroll width equalled its client width (375px). At 320x700, Activity's scroll width equalled its client width (305px); Workspace settings also measured 305px for both after the fix. These inner measurements matter because outer document width alone missed the original overflow.
- Independent frontend review identified two P2 regressions, both corrected and confirmed resolved: omitted unavailable-source events and source-request-dependent assessment visibility.

Desktop evidence at 1440x900 measured a 1217px client/scroll width, a 516px pane height and 524px content height (two records plus pagination). At 900x800, client/scroll width was 701px and pane/content height was 344/524px. Body heights remained equal to the viewport (900px and 800px). All three records remained reachable via Next/Previous. Desktop keyboard ArrowRight changed the selected tab and moved focus correctly. Case-library pagination and debounced filtering were exercised against the running API.

![Desktop evidence workbench](demo/ui-workbench-desktop.png)

[Mobile evidence workbench screenshot](demo/ui-workbench-mobile.png)


