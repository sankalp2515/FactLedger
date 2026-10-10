import { useState } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  Search,
  Fingerprint,
  ClipboardCheck,
  Check,
  ArrowUpRight,
} from "lucide-react";
import "./landing.css";

const repo = "https://github.com/sankalp2515/FactLedger";

export function LandingPage() {
  const [stage, setStage] = useState<"operational" | "inaugurated">(
    "operational",
  );
  return (
    <div className="landing">
      <a className="skip" href="#landing-main">
        Skip to content
      </a>
      <header className="landing-header">
        <Link to="/" className="landing-brand">
          <BookOpen size={24} /> FactLedger
        </Link>
        <nav aria-label="Product">
          <a href="#workflow">How it works</a>
          <a href="#examples">Use cases</a>
          <a href="#pricing">Costs</a>
        </nav>
        <Link className="landing-cta" to="/cases">
          Open workspace
        </Link>
      </header>
      <main id="landing-main">
        <section
          className="landing-hero landing-container"
          aria-labelledby="hero-title"
        >
          <div className="landing-hero-copy">
            <p className="landing-audience">
              For researchers and editors checking public claims
            </p>
            <h1 id="hero-title">Every claim deserves an evidence trail.</h1>
            <p className="landing-lead">
              Find the records. Inspect the exact quotation. Give your editor a
              conclusion they can trace.
            </p>
            <div className="landing-actions">
              <Link className="landing-cta" to="/cases">
                Open workspace
              </Link>
              <a className="landing-secondary" href="#example">
                Explore a comparison <ArrowUpRight size={17} />
              </a>
            </div>
            <p className="landing-assurance">
              Run locally. Try a synthetic case without API keys. Keep editorial
              judgment in human hands.
            </p>
          </div>
          <div
            className="landing-record"
            aria-label="Illustrated evidence trail"
          >
            <div className="landing-record-top">
              <span>
                <span className="landing-dot" /> The evidence trail
              </span>
              <span>Illustrative workflow</span>
            </div>
            <div className="landing-record-claim">
              <span>Start with a precise question</span>
              <h2>
                Approved. Funded. Delivered.
                <br />
                Which does the record establish?
              </h2>
            </div>
            <div className="landing-trail">
              <div>
                <Search size={20} />
                <strong>Discover</strong>
                <span>Queries and opposing records</span>
              </div>
              <div>
                <Fingerprint size={20} />
                <strong>Inspect</strong>
                <span>Preserved text and literal anchors</span>
              </div>
              <div>
                <ClipboardCheck size={20} />
                <strong>Review</strong>
                <span>A frozen revision and editor decision</span>
              </div>
            </div>
            <div className="landing-record-bottom">
              <Check size={17} /> An inspectable handoff, from claim to source.
            </div>
          </div>
        </section>

        <section
          className="landing-proof landing-container"
          aria-label="Verifiable product foundations"
        >
          <span>Proof you can inspect</span>
          <a href={repo}>
            MIT-licensed source <ArrowUpRight size={14} />
          </a>
          <a href={`${repo}/actions/workflows/verify.yml`}>
            Public automated checks <ArrowUpRight size={14} />
          </a>
          <a href={`${repo}/blob/main/docs/architecture.md`}>
            Documented evidence guards <ArrowUpRight size={14} />
          </a>
        </section>

        <section
          id="example"
          className="landing-comparison landing-container"
          aria-labelledby="comparison-title"
        >
          <div className="landing-section-copy">
            <h2 id="comparison-title">The difference a single word makes.</h2>
            <p>
              An inauguration is an event. Operation is a service. A useful
              investigation keeps those claims separate.
            </p>
            <p className="landing-caption">
              Illustrative comparison · synthetic record
            </p>
          </div>
          <div className="landing-comparison-body">
            <div
              className="landing-stage-controls"
              aria-label="Choose the asserted stage"
            >
              <button
                aria-pressed={stage === "operational"}
                onClick={() => setStage("operational")}
              >
                Operational
              </button>
              <button
                aria-pressed={stage === "inaugurated"}
                onClick={() => setStage("inaugurated")}
              >
                Inaugurated
              </button>
            </div>
            <div className="landing-comparison-grid">
              <div>
                <span>Claim</span>
                <p>
                  Hospital A was {stage} in District A during September 2026.
                </p>
              </div>
              <div>
                <span>Preserved record</span>
                <blockquote>
                  “Hospital A was inaugurated in District A in September 2026.”
                </blockquote>
              </div>
            </div>
            <div
              className={`landing-verdict ${stage === "inaugurated" ? "landing-verdict-match" : ""}`}
              role="status"
            >
              <strong>
                {stage === "operational"
                  ? "Operation is not established"
                  : "The stages match"}
              </strong>
              <span>
                {stage === "operational"
                  ? "The quotation establishes inauguration. Operational evidence is still needed."
                  : "The literal passage supports the asserted stage. Source quality and completeness still need review."}
              </span>
            </div>
          </div>
        </section>

        <section
          id="workflow"
          className="landing-workflow landing-container"
          aria-labelledby="workflow-title"
        >
          <div className="landing-section-heading">
            <h2 id="workflow-title">
              From a loose claim to a reviewable case.
            </h2>
            <p>
              One workspace for the questions, records and reasoning that
              usually live across tabs and notes.
            </p>
          </div>
          <ol className="landing-steps">
            <li>
              <span>1</span>
              <h3>Define what is being claimed</h3>
              <p>
                Confirm the subject, place, period and delivery stage before
                collecting evidence.
              </p>
            </li>
            <li>
              <span>2</span>
              <h3>Search beyond the headline</h3>
              <p>
                Use SerpApi to find relevant and opposing records. Inspect
                originals, not just snippets.
              </p>
            </li>
            <li>
              <span>3</span>
              <h3>Compare, with the gaps visible</h3>
              <p>
                Connect literal quotations to the claim. Keep missing dates,
                mismatched quantities and uncertain sources explicit.
              </p>
            </li>
            <li>
              <span>4</span>
              <h3>Give the editor the whole trail</h3>
              <p>
                Submit a frozen revision and export its evidence, sources,
                review and usage.
              </p>
            </li>
          </ol>
        </section>

        <section className="landing-benefits" aria-labelledby="benefits-title">
          <div className="landing-container landing-benefits-inner">
            <div>
              <h2 id="benefits-title">Research that stays inspectable.</h2>
              <p>
                AI helps collect candidate evidence. The record, its scope and
                your editor remain the authority.
              </p>
            </div>
            <div className="landing-benefit-list">
              <article>
                <h3>Open the quotation in context</h3>
                <p>
                  Jump from a comparison to the preserved passage and download
                  its original.
                </p>
              </article>
              <article>
                <h3>Keep related facts from becoming stronger claims</h3>
                <p>
                  Distinguish allocation from spending, targets from delivery
                  and approval from operation.
                </p>
              </article>
              <article>
                <h3>See what a run used—and what it could not establish</h3>
                <p>
                  Inspect provider activity, limits, estimated costs and partial
                  results before drawing a conclusion.
                </p>
              </article>
            </div>
          </div>
        </section>

        <section
          id="examples"
          className="landing-container landing-examples"
          aria-labelledby="examples-title"
        >
          <div className="landing-section-heading">
            <h2 id="examples-title">Start with a question that matters.</h2>
            <p>
              Worked examples to explore, not customer success claims or
              accuracy benchmarks.
            </p>
          </div>
          <div className="landing-example-grid">
            <article>
              <span className="landing-example-label">
                Real public-record scenario
              </span>
              <h3>Scheme approval or benefits delivered?</h3>
              <p>
                Investigate Cabinet approval of PM-Surya Ghar in February 2024.
                Inspect whether collected sources establish approval without
                treating a household target as delivered installations.
              </p>
              <a href="https://www.pib.gov.in/PressReleasePage.aspx?PRID=2010130&lang=2&reg=48">
                Read the official approval record <ArrowUpRight size={15} />
              </a>
              <small>
                A known source can be acquired manually; manual provenance stays
                visible. Live discovery may return partial results.
              </small>
            </article>
            <article>
              <span className="landing-example-label">
                Synthetic, key-free walkthrough
              </span>
              <h3>Inaugurated or operational?</h3>
              <p>
                Try the fictional Hospital A case. Inspect an inauguration
                record, identify missing operational evidence and hand a
                qualified conclusion to a separate editor.
              </p>
              <Link to="/cases/new">
                Create a practice case <ArrowUpRight size={15} />
              </Link>
              <small>
                Use Hospital A, District A, September 2026 and the operational
                stage. Select synthetic fixture mode.
              </small>
            </article>
          </div>
        </section>

        <section
          id="pricing"
          className="landing-container landing-pricing"
          aria-labelledby="pricing-title"
        >
          <div className="landing-section-copy">
            <h2 id="pricing-title">Clear costs. No mystery plan.</h2>
            <p>
              Start with the open-source application. Choose your provider
              accounts when you need live research.
            </p>
          </div>
          <div className="landing-pricing-options">
            <article>
              <h3>Local application</h3>
              <p className="landing-price">No software license fee</p>
              <p>
                MIT-licensed. Run on your own machine. Synthetic practice cases
                need no provider keys.
              </p>
              <ul>
                <li>
                  <Check size={16} /> Research and editorial workflows
                </li>
                <li>
                  <Check size={16} /> Preserved sources and evidence exports
                </li>
                <li>
                  <Check size={16} /> One Docker Compose startup command
                </li>
              </ul>
              <Link className="landing-cta" to="/cases">
                Open workspace
              </Link>
            </article>
            <article>
              <h3>Live research</h3>
              <p className="landing-price">Your provider usage</p>
              <p>
                Connect SerpApi and one supported LLM provider. Account rates,
                credits and availability apply.
              </p>
              <ul>
                <li>
                  <Check size={16} /> Visible search and model activity
                </li>
                <li>
                  <Check size={16} /> Configured budgets and cost estimates
                </li>
                <li>
                  <Check size={16} /> OpenAI, Anthropic, Gemini, Groq or NVIDIA
                </li>
              </ul>
              <a
                className="landing-secondary"
                href={`${repo}/blob/main/docs/api-guide.md#environment-and-setup`}
              >
                See provider setup <ArrowUpRight size={16} />
              </a>
            </article>
          </div>
          <p className="landing-pricing-note">
            Cost estimates are not invoices. Hosting and infrastructure are your
            responsibility; no managed subscription is offered.
          </p>
        </section>

        <section
          className="landing-container landing-faq"
          aria-labelledby="faq-title"
        >
          <h2 id="faq-title">Before you start.</h2>
          <div>
            {[
              [
                "Does FactLedger decide what is true?",
                "It describes what collected evidence establishes about a scoped claim. Models propose candidates; literal quotation and scope guards constrain them. A human editor remains responsible for any published conclusion.",
              ],
              [
                "Can I try it without paying for APIs?",
                "Yes. The visibly labelled synthetic fixture workflow makes no provider calls. Live research requires your SerpApi account and one supported LLM provider account.",
              ],
              [
                "What if search does not find enough evidence?",
                "Missing records, provider failures and budget limits remain visible. Partial or insufficient results are useful limits to inspect, not proof that a claim is false. You can acquire a known public source manually with its provenance retained.",
              ],
              [
                "Where do my records and keys live?",
                "The local deployment stores records in PostgreSQL and a private artifact volume. Provider keys stay on the server. Live extraction sends bounded claim and source excerpts to your selected provider; do not send sensitive material without appropriate authorization.",
              ],
              [
                "Can another editor reproduce the investigation?",
                "An editor can inspect a frozen revision, preserved originals, literal quotations and gaps, then approve or return a qualified conclusion. Exports preserve the selected revision rather than rewriting it after later draft edits.",
              ],
              [
                "Can I host this for my newsroom?",
                "Local Compose is for local use and development identities. Public hosting requires OIDC, TLS, restricted database permissions, protected storage, monitoring and verified recovery procedures. Review the architecture guide before hosting.",
              ],
            ].map(([question, answer]) => (
              <details key={question}>
                <summary>{question}</summary>
                <p>{answer}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="landing-final">
          <div className="landing-container">
            <BookOpen size={30} />
            <h2>Give the next claim a better starting point.</h2>
            <p>Start small. Inspect the record. Leave an evidence trail.</p>
            <div className="landing-actions">
              <Link className="landing-cta" to="/cases">
                Open workspace
              </Link>
              <a className="landing-secondary" href={repo}>
                View source on GitHub <ArrowUpRight size={16} />
              </a>
            </div>
          </div>
        </section>
      </main>
      <footer className="landing-footer landing-container">
        <Link to="/" className="landing-brand">
          <BookOpen size={20} /> FactLedger
        </Link>
        <span>Original records. Visible gaps. Human judgment.</span>
        <a href={`${repo}/blob/main/docs/user-flows.md`}>User guide</a>
        <a href={`${repo}/blob/main/SECURITY.md`}>Security</a>
        <a href={`${repo}/blob/main/LICENSE`}>MIT license</a>
      </footer>
    </div>
  );
}
