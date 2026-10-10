# Interface design

FactLedger keeps the claim, original records and uncertainty close together. The interface is an investigation workbench: restrained colour, readable text and clear status labels put scrutiny ahead of decoration.

![Desktop evidence workbench](assets/ui-workbench-desktop.png)

## Layout and hierarchy

The application shell separates the case library, active workbench, editor review and workspace settings. A case uses focused views for investigation, evidence, sources and conclusion instead of one long document. Source/evidence pagination bounds page length. The claim and revision remain visible so edits and decisions have context. Mobile uses a **Case view** selector and stacked controls.

The visual system uses the shared tokens and typography in `apps/web/src/styles.css`. Consistent spacing, borders, radii and control heights align forms and cards. Evidence text receives the largest reading area; metadata and actions remain secondary. Status uses text alongside colour so support, contradictions, partial runs and gaps are distinguishable without colour perception.

## Components and states

Shared controls include buttons, form fields, status pills, tabs, dialogs, paginated cards and source readers. The frontend keeps API contracts in `contracts.ts` and centralized transport in `api.ts`; the server remains authoritative for permissions, revisions and job state. Visible run activity explains progress and provider costs. Loading, error and empty states offer concrete actions without inventing results.

Dialogs contain keyboard focus and support Escape; tab controls support keyboard navigation. Forms use labels, visible focus and validation feedback. Original-record reading and quotation navigation are separate from interpretation. Responsive layouts preserve primary actions without requiring horizontal page scrolling.

Motion is limited to feedback and state transitions. Reduced motion is respected. Long-running research shows durable status rather than a decorative animation suggesting progress. Captured source text is rendered as text; exports escape untrusted content.

## Evidence presentation

An evidence card presents the relation, literal quotation, source identity and comparison gaps. **Jump to quotation** connects the claim back to preserved extraction text. Synthetic sources and manual additions retain visible provenance. Editorial review displays a frozen revision; local role switching is explicitly development-only. Approval records an editorial decision about a qualified conclusion and does not certify real-world conditions.

![Mobile workbench](assets/ui-workbench-mobile.png)

These screenshots document an earlier live walkthrough with a manually attached PIB record. They are examples of the interface, not a guarantee of future search results or provider availability.

## Public landing page

The root route introduces FactLedger without requiring a session or an API request. **Open workspace** enters the existing case library; direct investigation and editorial links keep their existing behavior. The landing page uses scoped styles, an editorial serif headline, a restrained green accent and responsive grids. The workbench retains its task-focused layout.

| Section | Decision it supports |
| --- | --- |
| Hero and evidence-trail illustration | Identifies researchers and editors, states the inspectable outcome and offers a clear next action. |
| Verifiable foundations | Links source code, automated checks and evidence guards instead of inventing customer logos or testimonials. |
| Interactive stage comparison | Lets visitors experience the distinction between inauguration and operation before starting a case. The record is explicitly synthetic. |
| Four-step workflow | Explains the effort required and how SerpApi discovery connects to inspection and editorial review. |
| Features and benefits | Connects preserved quotations, scoped comparisons and visible usage to practical research decisions. |
| Worked examples | Provides a real public-record scenario and a synthetic practice scenario, with explicit provenance and limitations. These are not customer case studies. |
| Cost presentation | Separates the MIT-licensed application from provider usage and hosting costs; it does not imply a managed subscription. |
| Expandable FAQs | Addresses evidence limits, provider keys, reproducibility and hosting without making the page an expanded manual. |
| Closing action and footer | Offers entry to the workspace, source code and public guidance after visitors have assessed the product. |

Native disclosure controls and stage buttons support keyboard interaction; the comparison announces its result through a status region. Narrow screens stack the main sections and preserve the workspace action. No decorative animation or autoplay media is required. This design aims to reduce uncertainty; conversion gains have not been measured through an experiment.
