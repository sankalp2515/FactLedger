import {
  useState,
  useEffect,
  createContext,
  useContext,
  type ReactNode,
  useRef,
} from "react";
import {
  Link,
  NavLink,
  Routes,
  Route,
  Navigate,
  useParams,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import {
  Library,
  ClipboardCheck,
  Settings,
  Plus,
  Search,
  BookOpen,
  ArrowUpRight,
  Pause,
  Play,
  Square,
  Download,
  X,
  Check,
  FileText,
  ChevronRight,
  ArrowLeft,
  AlertCircle,
} from "lucide-react";
import { api, ApiError } from "./api";
import { AnchorText } from "./AnchorText";
import { BudgetFields, validBudget } from "./BudgetFields";
import { PagedList } from "./PagedList";
import { createPortal } from "react-dom";
import { EvidenceComparison } from "./EvidenceComparison";
import { SourceFamilies } from "./SourceFamilies";
import { scopeInput } from "./scope";
import type {
  Session,
  CaseItem,
  CaseDetail,
  Payload,
  Evidence,
  Source,
  Plan,
  Run,
  RecordData,
  Review,
  Member,
  Claim,
} from "./contracts";
const SessionContext = createContext<Session | null>(null);
const useSession = () => useContext(SessionContext)!;
const pretty = (v: unknown) =>
  v === null || v === undefined || v === ""
    ? "Unknown"
    : typeof v === "object"
      ? JSON.stringify(v)
      : String(v).replaceAll("_", " ").toLowerCase();
const date = (v?: string) =>
  v
    ? new Date(v).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "Date unknown";
function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <BookOpen size={30} />
      <h3>{title}</h3>
      {children}
    </div>
  );
}
function Loading() {
  return (
    <div role="status" className="loading">
      <div className="skeleton" />
      <div className="skeleton short" />
      <p>Loading research records…</p>
    </div>
  );
}
function ErrorNotice({ error, retry }: { error: Error; retry?: () => void }) {
  return (
    <div role="alert" className="error">
      <AlertCircle size={20} />
      <div>
        <strong>
          {error instanceof ApiError && error.status === 409
            ? "This revision changed."
            : "Request could not be completed."}
        </strong>
        <p>{error.message}</p>
        {error instanceof ApiError && error.status === 409 && (
          <p>
            Your edits have not been applied. Reload the current revision,
            compare the changes, and submit again.
          </p>
        )}
        {retry && <button onClick={retry}>Try again</button>}
      </div>
    </div>
  );
}
function Field({
  label,
  name,
  defaultValue = "",
  type = "text",
  required = false,
}: {
  label: string;
  name: string;
  defaultValue?: string | number;
  type?: string;
  required?: boolean;
}) {
  return (
    <label className="field">
      {label}
      <input
        name={name}
        type={type}
        defaultValue={defaultValue}
        required={required}
      />
    </label>
  );
}
function useCommand<T = unknown>(onSuccess?: (data: T) => void) {
  const q = useQueryClient();
  return useMutation({
    mutationFn: ({
      path,
      body,
      method,
    }: {
      path: string;
      body: unknown;
      method?: string;
    }) => api.command<T>(path, body, method),
    onSuccess: (data) => {
      q.invalidateQueries();
      onSuccess?.(data);
    },
  });
}
function CommandState({
  m,
}: {
  m: { isPending: boolean; error: Error | null };
}) {
  return (
    <>
      {m.isPending && (
        <p role="status" className="muted">
          Saving to workspace…
        </p>
      )}
      {m.error && <ErrorNotice error={m.error} />}
    </>
  );
}
export function App() {
  const session = useQuery({
    queryKey: ["session"],
    queryFn: () => api.get<Session>("/session"),
    retry: false,
  });
  useEffect(() => {
    if (session.data) api.csrf = session.data.csrf_token;
  }, [session.data]);
  if (session.isPending) return <Loading />;
  if (session.error)
    return (
      <main className="login">
        <div className="brand">
          <BookOpen />
          FactLedger
        </div>
        <h1>Your newsroom research desk.</h1>
        <p>
          Trace claims through original records, exact comparisons and editorial
          review.
        </p>
        <ErrorNotice error={session.error} retry={() => session.refetch()} />
        {session.error instanceof ApiError && session.error.status === 401 && (
          <>
            <a className="button primary" href="/v1/auth/login">
              Sign in to your newsroom
            </a>
            <p className="muted">
              Use your organization's identity provider. Ask your workspace
              owner for access.
            </p>
          </>
        )}
      </main>
    );
  const s = session.data!;
  return (
    <SessionContext.Provider value={s}>
      <a href="#main" className="skip">
        Skip to content
      </a>
      <div className="app-shell">
        <aside className="sidebar">
          <Link className="brand" to="/cases">
            <span className="brand-icon">
              <BookOpen size={21} />
            </span>
            <span>
              FactLedger<small>Research workspace</small>
            </span>
          </Link>
          <div className="workspace-name">{s.workspace.name}</div>
          <nav aria-label="Workspace">
            <NavLink to="/cases">
              <Library size={19} />
              Case library
            </NavLink>
            <NavLink to="/reviews">
              <ClipboardCheck size={19} />
              Editor review
            </NavLink>
            <NavLink to="/workspace/settings">
              <Settings size={19} />
              Workspace
            </NavLink>
          </nav>
          <div className="sidebar-bottom">
            <span className="avatar">{s.user.name.slice(0, 1)}</span>
            <div>
              {s.user.name}
              <small>{pretty(s.role)}</small>
            </div>
          </div>
        </aside>
        <div className="app-content">
          <header className="topbar">
            <span>Public-interest research</span>
            <div>
              <Badge>
                {s.mode === "development"
                  ? "Local workspace"
                  : "Workspace session"}
              </Badge>
              <span className="session-dot" />
              Connected
            </div>
          </header>
          <main id="main">
            <Routes>
              <Route path="/cases" element={<LibraryPage />} />
              <Route path="/cases/new" element={<NewCase />} />
              <Route path="/cases/:id" element={<Workbench />} />
              <Route path="/cases/:id/runs/:runId" element={<Workbench />} />
              <Route
                path="/cases/:id/revisions/:revision"
                element={<Workbench />}
              />
              <Route path="/reviews" element={<Reviews />} />
              <Route path="/reviews/:requestId" element={<ReviewPage />} />
              <Route path="/workspace/settings" element={<Workspace />} />
              <Route path="*" element={<Navigate to="/cases" replace />} />
            </Routes>
          </main>
          <footer>Original records. Visible gaps. Human judgment.</footer>
        </div>
      </div>
    </SessionContext.Provider>
  );
}
function LibraryPage() {
  const [search, setSearch] = useState(""),
    [state, setState] = useState(""),
    [archived, setArchived] = useState(false),
    [cursor, setCursor] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState(search);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 250);
    return () => window.clearTimeout(timer);
  }, [search]);
  const list = useQuery({
    queryKey: ["cases", debouncedSearch, state, archived, cursor],
    queryFn: () =>
      api.get<{ items: CaseItem[]; next_cursor: string | null }>(
        `/cases?${new URLSearchParams({ search: debouncedSearch, state, archived: String(archived), cursor, limit: "4" })}`,
      ),
  });
  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <p className="kicker">The research desk</p>
          <h1>Case library</h1>
          <p className="intro">
            Follow a claim from the first question to an inspectable conclusion.
          </p>
        </div>
        <Link className="primary button" to="/cases/new">
          <Plus size={18} />
          New case
        </Link>
      </div>
      <div className="filters">
        <label className="search">
          <Search size={18} />
          <input
            aria-label="Search cases"
            placeholder="Search claims or case titles"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCursor("");
            }}
          />
        </label>
        <select
          aria-label="Case state"
          value={state}
          onChange={(e) => {
            setState(e.target.value);
            setCursor("");
          }}
        >
          <option value="">All states</option>
          {[
            "DRAFT",
            "INVESTIGATING",
            "READY_FOR_REVIEW",
            "IN_REVIEW",
            "APPROVED",
            "RETURNED",
          ].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
        <label className="check">
          <input
            type="checkbox"
            checked={archived}
            onChange={(e) => {
              setArchived(e.target.checked);
              setCursor("");
            }}
          />
          Archived cases
        </label>
      </div>
      {list.isPending ? (
        <Loading />
      ) : list.error ? (
        <ErrorNotice error={list.error} retry={() => list.refetch()} />
      ) : !list.data?.items.length ? (
        <Empty title="Your next investigation starts here.">
          <p>
            Create a case, confirm what the claim asserts, then collect records
            that can answer it.
          </p>
        </Empty>
      ) : (
        <div className="case-list">
          {list.data.items.map((c) => (
            <Link className="case-row" key={c.id} to={`/cases/${c.id}`}>
              <div className="case-monogram">
                <FileText size={23} />
              </div>
              <div className="case-text">
                <h2>{c.title}</h2>
                <p>{c.original_claim}</p>
                <span className="muted">
                  Updated {date(c.updated_at)} · Revision {c.revision}
                </span>
              </div>
              <Badge>{pretty(c.state)}</Badge>
              <ChevronRight size={20} />
            </Link>
          ))}
        </div>
      )}
      {list.data?.next_cursor && (
        <button onClick={() => setCursor(list.data!.next_cursor!)}>
          Next page
        </button>
      )}
      {cursor && (
        <button onClick={() => setCursor("")}>Back to first page</button>
      )}
      <div className="desk-note">
        <span>Research principle</span>
        <p>
          An announcement, an allocation and a delivered service are different
          claims. Keep them separate.
        </p>
      </div>
    </div>
  );
}
function NewCase() {
  const nav = useNavigate();
  const m = useCommand<CaseDetail>((c) => nav(`/cases/${c.id}`));
  return (
    <div className="page narrow">
      <Link className="back" to="/cases">
        <ArrowLeft size={16} />
        Case library
      </Link>
      <h1>A claim worth checking.</h1>
      <p className="intro">
        Preserve the original wording. You will confirm geography, period and
        delivery stage before research starts.
      </p>
      <form
        className="panel form"
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          m.mutate({
            path: "/cases",
            body: { title: f.get("title"), original_claim: f.get("claim") },
          });
        }}
      >
        <Field label="Case title" name="title" required />
        <label className="field">
          Original claim
          <textarea
            name="claim"
            required
            rows={5}
            placeholder="What exactly was claimed? Include the quoted amount, date or delivery stage."
          />
        </label>
        <div className="form-actions">
          <Link to="/cases">Cancel</Link>
          <button className="primary" disabled={m.isPending}>
            Create case
          </button>
        </div>
        <CommandState m={m} />
      </form>
    </div>
  );
}
function Workbench() {
  const { id, runId, revision } = useParams();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "evidence";
  const selected = params.get("evidence");
  const [modal, setModal] = useState("");
  const [correctionField, setCorrectionField] = useState("event_date");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [budget, setBudget] = useState<Record<string, number>>({});
  const [mode, setMode] = useState("fixture");
  const [format, setFormat] = useState("md");
  const [exportUrl, setExportUrl] = useState("");
  const q = useQueryClient();
  const nav = useNavigate();
  const s = useSession();
  const detail = useQuery({
    queryKey: ["case", s.workspace.id, id, revision],
    queryFn: () =>
      api.get<CaseDetail>(
        `/cases/${id}${revision ? `?revision=${revision}` : ""}`,
      ),
  });
  const runQuery = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.get<Run>(`/runs/${runId}`),
    enabled: !!runId,
    refetchInterval: (query) =>
      ["COMPLETED", "FAILED", "CANCELLED", "PARTIAL"].includes(
        query.state.data?.state ?? "",
      )
        ? false
        : 2500,
  });
  const m = useCommand<CaseDetail>();
  const integration = useCommand<CaseDetail>(() => nav(`/cases/${id}`));
  const planning = useCommand<Plan>((p) => {
    setPlan(p);
    setBudget(p.budget);
  });
  const start = useCommand<Run>((r) => {
    setModal("");
    nav(`/cases/${id}/runs/${r.id}`);
  });
  const deleting = useCommand(() => {
    q.invalidateQueries();
    nav("/cases");
  });
  const exporting = useCommand<{ download_url: string }>((r) => {
    setExportUrl(r.download_url);
    window.location.assign(r.download_url);
  });
  const run = runQuery.data ?? detail.data?.latest_run;
  const active =
    run &&
    ![
      "COMPLETED",
      "FAILED",
      "CANCELLED",
      "PARTIAL",
      "INTEGRATED",
      "BUDGET_EXHAUSTED",
    ].includes(run.state.toUpperCase());
  const streamRunId = run?.id;
  useEffect(() => {
    if (!active || !streamRunId) return;
    const stream = new EventSource(`/v1/runs/${streamRunId}/events`, {
      withCredentials: true,
    });
    const refresh = () => {
      q.invalidateQueries({ queryKey: ["run", streamRunId] });
      q.invalidateQueries({ queryKey: ["case", s.workspace.id, id] });
    };
    stream.onmessage = refresh;
    stream.onerror = refresh;
    return () => stream.close();
  }, [streamRunId, active, id, q, s.workspace.id]);
  if (detail.isPending) return <Loading />;
  if (detail.error)
    return (
      <div className="page">
        <ErrorNotice error={detail.error} retry={() => detail.refetch()} />
      </div>
    );
  const c = detail.data!;
  const p = runId && run ? run.results : c.payload;
  const evidence = p.evidence ?? [];
  const selectedEvidence = evidence.find((e) => e.id === selected);
  const readonly = !!revision;
  const path = `/cases/${id}`;
  const expected = { expected_revision: c.revision };
  const choose = (key: string, value: string) =>
    setParams((old) => {
      const next = new URLSearchParams(old);
      next.set(key, value);
      return next;
    });
  return (
    <div className="workbench">
      <div className="case-header">
        <div className="breadcrumbs">
          <Link to="/cases">Case library</Link>
          <ChevronRight size={14} />
          <span>Case {c.id.slice(0, 8)}</span>
        </div>
        <div className="case-heading">
          <div>
            <div className="case-meta">
              <Badge>{pretty(c.state)}</Badge>
              <span>Revision {revision ?? c.revision}</span>
              {readonly && <Badge tone="warn">Historical snapshot</Badge>}
              {runId && (
                <Badge tone="warn">Run-owned results · not integrated</Badge>
              )}
            </div>
            <h1>{c.title}</h1>
            <details className="claim-disclosure">
              <summary>Original claim</summary>
              <p className="original-claim" tabIndex={0}>
                “{c.original_claim}”
              </p>
            </details>
          </div>
          <div className="header-actions">
            {!readonly && (
              <button
                className="primary"
                onClick={() =>
                  setModal(c.payload.claims.length ? "research" : "scope")
                }
              >
                <Search size={16} />
                {c.payload.claims.length ? "Investigate" : "Confirm claim"}
              </button>
            )}
            <button onClick={() => setModal("export")}>
              <Download size={16} />
              Export
            </button>
          </div>
        </div>
        {readonly && <Link to={path}>Return to current draft</Link>}
        {run && (
          <div className="run-strip">
            <div>
              <Badge tone={run.mode === "fixture" ? "warn" : ""}>
                {run.mode === "fixture"
                  ? "Synthetic fixture"
                  : "Live investigation"}
              </Badge>
              <strong>{pretty(run.state)}</strong>
              <span>Based on revision {run.base_revision}</span>
            </div>
            <Link to={`${path}/runs/${run.id}`}>Inspect run</Link>
            {active && (
              <button
                onClick={() =>
                  m.mutate({
                    path: `/runs/${run.id}/${run.state.toUpperCase() === "PAUSED" ? "resume" : "pause"}`,
                    body: {},
                  })
                }
              >
                {run.state.toUpperCase() === "PAUSED" ? (
                  <Play size={15} />
                ) : (
                  <Pause size={15} />
                )}{" "}
                {run.state.toUpperCase() === "PAUSED" ? "Resume" : "Pause"}
              </button>
            )}
            {active && (
              <button
                onClick={() =>
                  m.mutate({ path: `/runs/${run.id}/cancel`, body: {} })
                }
              >
                <Square size={14} />
                Cancel
              </button>
            )}
            {!active &&
              !readonly &&
              run.state.toUpperCase() !== "INTEGRATED" &&
              !run.checkpoint?.integrated_revision && (
                <button
                  className="primary"
                  disabled={m.isPending}
                  onClick={() =>
                    integration.mutate({
                      path: `/runs/${run.id}/integrate`,
                      body: expected,
                    })
                  }
                >
                  Integrate results
                </button>
              )}
          </div>
        )}
        <CommandState m={m} />
        <CommandState m={integration} />
      </div>
      <div className="workbench-grid">
        <aside className="claim-rail">
          <details className="scope-details">
            <summary>
              Confirmed scope{" "}
              <span>
                {p.claims?.length
                  ? `${p.claims[0].geography} · ${p.claims[0].period}`
                  : "Not confirmed"}
              </span>
            </summary>
            <div className="section-head">
              <h2>Confirmed scope</h2>
              {!readonly && (
                <button
                  className="text-button"
                  onClick={() => setModal("scope")}
                >
                  Edit
                </button>
              )}
            </div>
            {!(p.claims ?? []).length ? (
              <p className="muted">
                Confirm the subject, period and stage before starting research.
              </p>
            ) : (
              p.claims.map((cl, i) => (
                <div className="claim" key={cl.id ?? i}>
                  <h3>{cl.text}</h3>
                  <dl>
                    {[
                      ["Subject", cl.subject],
                      ["Geography", cl.geography],
                      ["Period", cl.period],
                      ["Asserted stage", pretty(cl.stage)],
                      ["Measure", pretty(cl.measure)],
                      ["Value", `${cl.value ?? "Unknown"} ${cl.unit ?? ""}`],
                      ["Denominator", cl.denominator],
                      ["Attribution", cl.attribution],
                    ].map(([k, v]) => (
                      <div key={String(k)}>
                        <dt>{k}</dt>
                        <dd>{v || "Unknown"}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              ))
            )}
          </details>
          <details className="case-tools">
            <summary>Case actions</summary>
            <div className="rail-bottom">
              <p className="muted">Case record</p>
              <button onClick={() => choose("tab", "history")}>
                Revision history
              </button>
              {!readonly && (
                <>
                  <button onClick={() => setModal("metadata")}>
                    Edit details
                  </button>
                  <button onClick={() => setModal("delete")}>
                    Delete case
                  </button>
                  <CommandState m={deleting} />
                </>
              )}
            </div>
          </details>
        </aside>
        <section className="evidence-center">
          <label className="view-switcher">
            Case view
            <select
              value={tab}
              onChange={(event) => choose("tab", event.target.value)}
            >
              {[
                "evidence",
                "families",
                "sources",
                "stages",
                "funding",
                "metrics",
                "gaps",
                "notes",
                "review",
                "history",
                "activity",
              ].map((view) => (
                <option key={view} value={view}>
                  {view === "review"
                    ? "Conclusion"
                    : view === "stages"
                      ? "Delivery stages"
                      : pretty(view)}
                </option>
              ))}
            </select>
          </label>
          <div className="tabs" role="tablist" aria-label="Case record">
            {[
              "evidence",
              "families",
              "sources",
              "stages",
              "funding",
              "metrics",
              "gaps",
              "notes",
              "review",
              "history",
              "activity",
            ].map((x) => (
              <button
                key={x}
                role="tab"
                id={`case-tab-${x}`}
                data-tab={x}
                aria-controls="case-tab-panel"
                aria-selected={tab === x}
                tabIndex={tab === x ? 0 : -1}
                onClick={() => choose("tab", x)}
                onKeyDown={(event) => {
                  if (
                    !["ArrowLeft", "ArrowRight", "Home", "End"].includes(
                      event.key,
                    )
                  )
                    return;
                  event.preventDefault();
                  const buttons = Array.from(
                    event.currentTarget.parentElement!.querySelectorAll<HTMLButtonElement>(
                      '[role="tab"]',
                    ),
                  );
                  const current = buttons.indexOf(event.currentTarget);
                  const next =
                    event.key === "Home"
                      ? 0
                      : event.key === "End"
                        ? buttons.length - 1
                        : (current +
                            (event.key === "ArrowRight" ? 1 : -1) +
                            buttons.length) %
                          buttons.length;
                  choose("tab", buttons[next].dataset.tab!);
                  buttons[next].focus();
                }}
              >
                {x === "stages"
                  ? "Delivery stages"
                  : x === "review"
                    ? "Conclusion"
                    : pretty(x)}
                {x === "evidence" && <span>{evidence.length}</span>}
              </button>
            ))}
          </div>
          <div
            key={`${c.id}:${tab}`}
            className="tab-content"
            role="tabpanel"
            id="case-tab-panel"
            aria-labelledby={`case-tab-${tab}`}
          >
            {tab === "evidence" && (
              <>
                <div className="section-head">
                  <div>
                    <h2>Evidence, in context</h2>
                    <p className="muted">
                      Inspect the passage before accepting the comparison.
                    </p>
                  </div>
                  {!readonly && (
                    <button onClick={() => setModal("source")}>
                      <Plus size={16} />
                      Add source
                    </button>
                  )}
                </div>
                {!evidence.length ? (
                  <Empty title="No evidence collected yet.">
                    <p>
                      Confirm the claim and investigate, or attach an original
                      document.
                    </p>
                  </Empty>
                ) : (
                  <div className="evidence-list">
                    <PagedList
                      key={c.id}
                      label="Evidence"
                      items={evidence}
                      renderItem={(e) => (
                        <button
                          key={e.id}
                          className={`evidence-card ${selected === e.id ? "selected" : ""}`}
                          onClick={() => choose("evidence", e.id)}
                        >
                          <div className="evidence-meta">
                            <Relation
                              value={String(e.override?.relation ?? e.relation)}
                            />
                            <span>
                              {p.sources.find((s) => s.id === e.source_id)
                                ?.title ?? "Source document"}
                            </span>
                            <ArrowUpRight size={16} />
                          </div>
                          <blockquote className="record-preview">
                            {e.quote}
                          </blockquote>
                          <p className="record-preview">{e.rationale}</p>
                          <span className="record-open">
                            Read source and comparison{" "}
                            <ChevronRight size={14} />
                          </span>
                        </button>
                      )}
                    />
                  </div>
                )}
              </>
            )}
            {tab === "sources" && (
              <>
                <div className="section-head">
                  <h2>
                    Original sources{" "}
                    <span className="muted">{p.sources.length}</span>
                  </h2>
                  {!readonly && (
                    <button onClick={() => setModal("source")}>
                      <Plus size={16} />
                      Add source
                    </button>
                  )}
                </div>
                <Sources
                  sources={p.sources ?? []}
                  onSelect={(source) => {
                    choose("evidence", "");
                    choose("source", source.id);
                  }}
                />
              </>
            )}
            {tab === "families" && (
              <SourceFamilies
                caseId={c.id}
                revision={c.revision}
                readonly={readonly}
                sources={p.sources}
                edges={p.lineage}
              />
            )}
            {["stages", "funding", "metrics"].includes(tab) && (
              <Ledger
                kind={tab}
                entries={
                  p.ledger?.[
                    tab === "stages"
                      ? "stages"
                      : tab === "funding"
                        ? "funding"
                        : "metrics"
                  ] ?? []
                }
                onCorrect={!readonly ? () => setModal("ledger") : undefined}
              />
            )}{" "}
            {tab === "gaps" && (
              <>
                <h2>What the collected records do not establish</h2>
                {!p.ledger?.gaps?.length ? (
                  <Empty title="No gap records yet.">
                    <p>
                      Absence of a recorded gap does not establish the claim.
                    </p>
                  </Empty>
                ) : (
                  <PagedList
                    label="Gaps"
                    items={p.ledger.gaps}
                    renderItem={(g, i) => (
                      <div className="gap" key={i}>
                        <AlertCircle size={20} />
                        <div>
                          <h3>{pretty(g.type)}</h3>
                          <p>{pretty(g.reason)}</p>
                          <strong>Next evidence needed</strong>
                          <p>{pretty(g.next_evidence_needed)}</p>
                        </div>
                      </div>
                    )}
                  />
                )}
              </>
            )}
            {tab === "notes" && <Notes c={c} readonly={readonly} />}{" "}
            {tab === "review" && <Conclusion c={c} readonly={readonly} />}{" "}
            {tab === "history" && <History id={id!} revision={c.revision} />}{" "}
            {tab === "activity" && <Activity run={run} />}
          </div>
        </section>
        {(selectedEvidence || params.get("source")) && (
          <Dialog
            title="Inspect original source"
            onClose={() =>
              setParams((old) => {
                const next = new URLSearchParams(old);
                next.delete("source");
                next.delete("evidence");
                return next;
              })
            }
          >
            <Reader
              evidence={selectedEvidence}
              sourceId={
                selectedEvidence?.source_id ?? params.get("source") ?? undefined
              }
              source={p.sources?.find(
                (x) =>
                  x.id ===
                  (selectedEvidence?.source_id ?? params.get("source")),
              )}
              revision={c.revision}
              readonly={readonly}
            />
          </Dialog>
        )}
      </div>
      {modal && (
        <Dialog
          title={
            {
              scope: "Confirm the claim",
              research: "Review the investigation plan",
              source: "Add an original source",
              export: "Export a frozen revision",
              metadata: "Edit case details",
              delete: "Delete case",
              ledger: "Correct a ledger observation",
            }[modal] ?? modal
          }
          onClose={() => setModal("")}
        >
          {modal === "scope" && <ScopeForm c={c} onDone={() => setModal("")} />}
          {modal === "research" && (
            <>
              <p>
                The plan is pinned to revision {c.revision}. Collected records
                remain on the run until you explicitly integrate them.
              </p>
              {!plan ? (
                <button
                  className="primary"
                  disabled={!c.payload.claims.length || planning.isPending}
                  onClick={() =>
                    planning.mutate({ path: `${path}/plans`, body: expected })
                  }
                >
                  Generate research plan
                </button>
              ) : (
                <>
                  <div className="plan-queries">
                    {plan.queries.map((x, i) => (
                      <div key={i}>
                        <Search size={16} />
                        <div>
                          {typeof x === "string"
                            ? x
                            : String(x.query ?? x.text ?? JSON.stringify(x))}
                          <small>
                            {typeof x === "object"
                              ? pretty(x.purpose)
                              : "Discovery query"}
                          </small>
                        </div>
                      </div>
                    ))}
                  </div>
                  <BudgetFields budget={budget} onChange={setBudget} />
                  <label className="field">
                    Investigation mode
                    <select
                      value={mode}
                      onChange={(e) => setMode(e.target.value)}
                    >
                      <option value="fixture">
                        Synthetic fixture · evaluation only
                      </option>
                      <option value="live" disabled={!s.providers.serpapi}>
                        Live search and original records
                      </option>
                    </select>
                  </label>
                  <p className="notice">
                    {mode === "fixture"
                      ? "Fixture results are synthetic examples, not real-world findings."
                      : "Live research calls configured providers within the displayed budget."}
                  </p>
                  {!s.providers.serpapi && (
                    <p className="muted">
                      Live search is unavailable until the server has a
                      configured SerpApi connection.
                    </p>
                  )}
                  <button
                    className="primary"
                    disabled={start.isPending || !validBudget(budget)}
                    onClick={() =>
                      start.mutate({
                        path: `${path}/runs`,
                        body: { ...expected, plan_id: plan.id, mode, budget },
                      })
                    }
                  >
                    Start investigation
                  </button>
                </>
              )}
              <CommandState m={planning} />
              <CommandState m={start} />
            </>
          )}
          {modal === "source" && (
            <SourceForm c={c} onDone={() => setModal("")} />
          )}
          {modal === "export" && (
            <>
              <p>
                The pack preserves confirmed scope, citations, gaps and review
                status for revision {revision ?? c.revision}.
              </p>
              <label className="field">
                Format
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                >
                  <option value="md">Markdown</option>
                  <option value="html">HTML</option>
                  <option value="json">JSON</option>
                </select>
              </label>
              <button
                className="primary"
                disabled={exporting.isPending}
                onClick={() =>
                  exporting.mutate({
                    path: `${path}/exports`,
                    body: { revision: Number(revision ?? c.revision), format },
                  })
                }
              >
                Create and download pack
              </button>
              <CommandState m={exporting} />
              {exportUrl && (
                <p role="status">
                  Frozen pack created.{" "}
                  <a href={exportUrl}>Download evidence pack again</a>
                </p>
              )}
            </>
          )}
          {modal === "metadata" && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                m.mutate({
                  path,
                  method: "PATCH",
                  body: {
                    ...expected,
                    title: f.get("title"),
                    tags: String(f.get("tags"))
                      .split(",")
                      .map((t) => t.trim())
                      .filter(Boolean),
                    archived: f.get("archived") === "on",
                  },
                });
                setModal("");
              }}
            >
              <Field
                name="title"
                label="Case title"
                defaultValue={c.title}
                required
              />
              <Field
                name="tags"
                label="Tags, separated by commas"
                defaultValue={c.tags.join(", ")}
              />
              <label className="check">
                <input
                  name="archived"
                  type="checkbox"
                  defaultChecked={c.archived}
                />
                Archive this case
              </label>
              <button className="primary">Save details</button>
            </form>
          )}
          {modal === "delete" && (
            <>
              <p>
                Deleting this case revokes access to its sources and packs and
                cancels active research. The server applies the workspace
                retention policy.
              </p>
              <button
                className="danger"
                disabled={deleting.isPending}
                onClick={() =>
                  deleting.mutate({
                    path: `${path}?expected_revision=${c.revision}`,
                    body: {},
                    method: "DELETE",
                  })
                }
              >
                Delete case
              </button>
              <CommandState m={deleting} />
            </>
          )}
          {modal === "ledger" && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const corrected = { [correctionField]: String(f.get("value")) };
                m.mutate({
                  path: `${path}/ledger-overrides`,
                  body: {
                    ...expected,
                    observation_id: f.get("observation"),
                    corrected_fields: corrected,
                    reason: f.get("reason"),
                  },
                });
              }}
            >
              <label className="field">
                Observation
                <select name="observation" required>
                  {[
                    ...p.ledger.stages,
                    ...p.ledger.funding,
                    ...p.ledger.metrics,
                  ]
                    .filter((o) => o.id)
                    .map((o) => (
                      <option key={String(o.id)} value={String(o.id)}>
                        {String(
                          o.stage ?? o.measure ?? o.kind ?? "Observation",
                        )}{" "}
                        /{" "}
                        {String(
                          o.event_date ?? o.reference_period ?? "Undated",
                        )}{" "}
                        / {String(o.id).slice(0, 8)}
                      </option>
                    ))}
                </select>
              </label>
              <label className="field">
                Corrected field
                <select
                  value={correctionField}
                  onChange={(e) => setCorrectionField(e.target.value)}
                >
                  <option value="event_date">Event date</option>
                  <option value="reference_period">Reference period</option>
                  <option value="denominator">Denominator</option>
                  <option value="attributed_to">Attribution</option>
                  <option value="limitations">Limitations</option>
                </select>
              </label>
              <label className="field">
                Corrected value
                <input
                  key={correctionField}
                  name="value"
                  type={correctionField === "event_date" ? "date" : "text"}
                  required
                />
              </label>
              <p className="muted">
                Only mapping metadata can be corrected. Stage or value changes
                require source re-analysis.
              </p>
              <Field label="Reason for correction" name="reason" required />
              <button className="primary" disabled={m.isPending}>
                Save correction
              </button>
              <CommandState m={m} />
            </form>
          )}
        </Dialog>
      )}
    </div>
  );
}
function Relation({ value }: { value: string }) {
  return (
    <Badge
      tone={
        value === "SUPPORTS"
          ? "support"
          : value === "CONTRADICTS"
            ? "opposition"
            : "neutral"
      }
    >
      {value === "SUPPORTS" ? (
        <Check size={13} />
      ) : value === "CONTRADICTS" ? (
        <X size={13} />
      ) : (
        <AlertCircle size={13} />
      )}{" "}
      {pretty(value)}
    </Badge>
  );
}
function Dialog({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLElement>(null);
  const closeRef = useRef(onClose);
  useEffect(() => {
    closeRef.current = onClose;
  }, [onClose]);
  useEffect(() => {
    const before = document.activeElement as HTMLElement;
    const root = document.getElementById("root");
    const previousInert = root?.inert ?? false;
    const previousOverflow = document.body.style.overflow;
    if (root) root.inert = true;
    document.body.style.overflow = "hidden";
    const focus = dialog.current?.querySelector("button") as HTMLElement;
    focus?.focus();
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeRef.current();
      if (e.key === "Tab") {
        const items = Array.from(
          dialog.current?.querySelectorAll<HTMLElement>(
            'button,input,textarea,select,a[href],[tabindex="0"]',
          ) ?? [],
        ).filter((x) => !x.hasAttribute("disabled"));
        const first = items[0],
          last = items.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("keydown", esc);
      if (root) root.inert = previousInert;
      document.body.style.overflow = previousOverflow;
      before?.focus();
    };
  }, []);
  return createPortal(
    <div className="modal-backdrop">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        className="dialog"
        ref={dialog}
      >
        <div className="section-head">
          <h2 id="dialog-title">{title}</h2>
          <button aria-label="Close dialog" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        {children}
      </section>
    </div>,
    document.body,
  );
}
function ScopeForm({ c, onDone }: { c: CaseDetail; onDone: () => void }) {
  const [claims, setClaims] = useState<Claim[]>(
    c.payload.claims.length
      ? c.payload.claims
      : [
          {
            text: c.original_claim,
            subject: "",
            geography: "",
            period: "",
            stage: "UNKNOWN",
            measure: "",
          },
        ],
  );
  const m = useCommand(onDone);
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        m.mutate({
          path: `/cases/${c.id}/scope`,
          body: {
            expected_revision: c.revision,
            claims: claims.map(scopeInput),
          },
        });
      }}
    >
      <p>
        Split broad statements into atomic claims. Unknown scope stays visible
        in comparisons.
      </p>
      {claims.map((cl, i) => (
        <fieldset key={i}>
          <legend>Claim {i + 1}</legend>
          {(
            [
              "text",
              "subject",
              "geography",
              "period",
              "measure",
              "value",
              "unit",
              "denominator",
              "attribution",
            ] as const
          ).map((k) => (
            <label className="field" key={k}>
              {k === "text" ? "Claim wording" : pretty(k)}
              <input
                value={cl[k] ?? ""}
                required={["text", "subject", "geography", "period"].includes(
                  k,
                )}
                onChange={(e) =>
                  setClaims((old) =>
                    old.map((x, j) =>
                      j === i ? { ...x, [k]: e.target.value } : x,
                    ),
                  )
                }
              />
            </label>
          ))}
          <label className="field">
            Asserted stage
            <select
              value={cl.stage}
              onChange={(e) =>
                setClaims((old) =>
                  old.map((x, j) =>
                    j === i ? { ...x, stage: e.target.value } : x,
                  ),
                )
              }
            >
              {[
                "UNKNOWN",
                "ANNOUNCED",
                "APPROVED",
                "PROCURED",
                "UNDER_CONSTRUCTION",
                "PHYSICALLY_COMPLETED",
                "INAUGURATED",
                "OPERATIONAL",
              ].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label className="field">
            Currency
            <select
              value={cl.currency ?? ""}
              onChange={(e) =>
                setClaims((old) =>
                  old.map((x, j) =>
                    j === i
                      ? {
                          ...x,
                          currency: (e.target.value ||
                            undefined) as Claim["currency"],
                        }
                      : x,
                  ),
                )
              }
            >
              <option value="">Unknown / not monetary</option>
              {["INR", "USD", "EUR", "GBP"].map((x) => (
                <option key={x} value={x}>
                  {x}
                </option>
              ))}
            </select>
          </label>
          {claims.length > 1 && (
            <button
              type="button"
              onClick={() => setClaims((old) => old.filter((_, j) => j !== i))}
            >
              Remove claim
            </button>
          )}
        </fieldset>
      ))}
      <div className="form-actions">
        <button
          type="button"
          disabled={claims.length >= 3}
          onClick={() =>
            setClaims((old) => [
              ...old,
              {
                text: "",
                subject: "",
                geography: "",
                period: "",
                stage: "UNKNOWN",
                measure: "UNKNOWN",
              },
            ])
          }
        >
          Add atomic claim
        </button>
        <button className="primary" disabled={m.isPending}>
          Confirm scope
        </button>
      </div>
      <CommandState m={m} />
    </form>
  );
}
function SourceForm({ c, onDone }: { c: CaseDetail; onDone: () => void }) {
  const [kind, setKind] = useState("url");
  const m = useCommand(onDone);
  return (
    <>
      <div className="segmented">
        <button onClick={() => setKind("url")} aria-pressed={kind === "url"}>
          Source URL
        </button>
        <button onClick={() => setKind("pdf")} aria-pressed={kind === "pdf"}>
          Upload PDF
        </button>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          if (kind === "pdf") {
            f.set("expected_revision", String(c.revision));
            m.mutate({ path: `/cases/${c.id}/uploads`, body: f });
          } else {
            const ranges = String(f.get("pages") ?? "").trim();
            m.mutate({
              path: `/cases/${c.id}/sources`,
              body: {
                expected_revision: c.revision,
                url: f.get("url"),
                ...(ranges
                  ? {
                      page_ranges: ranges
                        .split(",")
                        .map((x) => x.split("-").map(Number))
                        .map((a) => (a.length === 1 ? [a[0], a[0]] : a)),
                    }
                  : {}),
              },
            });
          }
        }}
      >
        {kind === "url" ? (
          <>
            <Field label="Public source URL" name="url" type="url" required />
            <Field
              label="PDF page ranges (optional, e.g. 1-3, 8)"
              name="pages"
            />
          </>
        ) : (
          <label className="field">
            Original PDF
            <input name="file" type="file" accept="application/pdf" required />
          </label>
        )}
        <p className="muted">
          The original document and extracted text are preserved. Scanned or
          inaccessible records remain explicitly unavailable.
        </p>
        <button className="primary" disabled={m.isPending}>
          Acquire source
        </button>
        <CommandState m={m} />
      </form>
    </>
  );
}
function Sources({
  sources,
  onSelect,
}: {
  sources: Source[];
  onSelect: (source: Source) => void;
}) {
  return (
    <div className="sources-list">
      <PagedList
        label="Sources"
        items={sources}
        renderItem={(s) => (
          <button key={s.id} onClick={() => onSelect(s)}>
            <FileText size={17} />
            <div>
              {s.title}
              <small>{pretty(s.status)}</small>
            </div>
            <ChevronRight size={15} />
          </button>
        )}
      />
    </div>
  );
}
function Reader({
  evidence,
  sourceId,
  source,
  revision,
  readonly,
}: {
  evidence?: Evidence;
  sourceId?: string;
  source?: Source;
  revision: number;
  readonly: boolean;
}) {
  const read = useQuery({
    queryKey: ["source", sourceId],
    queryFn: () => api.get<Source>(`/sources/${sourceId}`),
    enabled: !!sourceId,
  });
  const m = useCommand();
  const [correct, setCorrect] = useState(false);
  if (!sourceId)
    return (
      <div className="reader-placeholder">
        <BookOpen size={32} />
        <h2>Read the original.</h2>
        <p>
          Select evidence to inspect the quoted passage in its source context.
        </p>
        <div className="reader-principle">
          A source passage supports a comparison. It does not certify ground
          reality.
        </div>
      </div>
    );
  const doc = read.data ?? source;
  const meta = doc?.metadata ?? doc?.metadata_json ?? {};
  return (
    <>
      {read.isPending ? (
        <Loading />
      ) : read.error ? (
        <ErrorNotice error={read.error} retry={() => read.refetch()} />
      ) : (
        <>
          <div className="reader-document">
            <Badge>{pretty(doc?.status)}</Badge>
            <h3>{doc?.title}</h3>
            <a href={doc?.url} target="_blank" rel="noreferrer">
              Original URL <ArrowUpRight size={13} />
            </a>
            {evidence?.anchor.page && (
              <p className="muted">Physical PDF page {evidence.anchor.page}</p>
            )}
            <div className="extraction-meta">
              {Object.entries(meta)
                .filter(([k]) =>
                  [
                    "total_pages",
                    "extracted_pages",
                    "extraction_version",
                    "source_type",
                    "date_provenance",
                  ].includes(k),
                )
                .map(([k, v]) => (
                  <span key={k}>
                    {pretty(k)}: {pretty(v)}
                  </span>
                ))}
            </div>
            {doc?.text ? (
              <AnchorText text={doc.text} anchor={evidence?.anchor} />
            ) : (
              <p className="notice">
                No readable extraction is available. This source cannot supply a
                decisive anchored comparison.
              </p>
            )}
            <a className="button" href={`/v1/sources/${sourceId}/download`}>
              <Download size={16} />
              Download original
            </a>
          </div>
        </>
      )}
      {evidence && (
        <div className="reader-analysis">
          <Relation
            value={String(evidence.override?.relation ?? evidence.relation)}
          />
          <blockquote>{evidence.quote}</blockquote>
          <p>{evidence.rationale}</p>
          <EvidenceComparison comparison={evidence.comparison ?? {}} />
          {!readonly && (
            <button onClick={() => setCorrect((x) => !x)}>
              Correct evidence relation
            </button>
          )}
          {correct && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                m.mutate({
                  path: `/evidence/${evidence.id}/relation`,
                  method: "PATCH",
                  body: {
                    expected_revision: revision,
                    relation: f.get("relation"),
                    reason: f.get("reason"),
                  },
                });
              }}
            >
              <label className="field">
                Relation
                <select name="relation" defaultValue={evidence.relation}>
                  {[
                    "SUPPORTS",
                    "CONTRADICTS",
                    "CONTEXT",
                    "INCOMPARABLE",
                    "INSUFFICIENT",
                  ].map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </select>
              </label>
              <Field name="reason" label="Reason for correction" required />
              <button className="primary" disabled={m.isPending}>
                Save correction
              </button>
              <CommandState m={m} />
            </form>
          )}
        </div>
      )}
    </>
  );
}
function Ledger({
  kind,
  entries,
  onCorrect,
}: {
  kind: string;
  entries: RecordData[];
  onCorrect?: () => void;
}) {
  const keys =
    kind === "stages"
      ? ["stage", "event_date", "quote"]
      : kind === "funding"
        ? ["kind", "value", "unit", "period", "quote"]
        : ["kind", "value", "unit", "period", "denominator", "quote"];
  return (
    <>
      <div className="section-head">
        <div>
          <h2>
            {kind === "stages"
              ? "Observed delivery stages"
              : kind === "funding"
                ? "Funding is not expenditure"
                : "Measure the same thing"}
          </h2>
          <p className="muted">
            Every observation retains its period, source and original
            expression.
          </p>
        </div>
        {onCorrect && entries.length > 0 && (
          <button onClick={onCorrect}>Correct observation</button>
        )}
      </div>
      {!entries.length ? (
        <Empty title="No observations recorded.">
          <p>Research or add a document to build this ledger.</p>
        </Empty>
      ) : (
        <div
          className="table-scroll"
          role="region"
          aria-label={`${kind} ledger`}
          tabIndex={0}
        >
          <table>
            <thead>
              <tr>
                {keys.map((k) => (
                  <th key={k}>{pretty(k)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map((x, i) => (
                <tr key={String(x.id ?? i)}>
                  {keys.map((k) => (
                    <td key={k}>{pretty(x[k])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
function Notes({ c, readonly }: { c: CaseDetail; readonly: boolean }) {
  const m = useCommand();
  return (
    <>
      <h2>Researcher's notes</h2>
      <p className="muted">
        Keep field observations and editorial judgment attributed separately
        from collected records.
      </p>
      <PagedList
        label="Notes"
        items={c.payload.notes}
        renderItem={(n, i) => (
          <details className="note" key={i}>
            <summary>
              {String(n.attribution ?? "Unattributed")} ·{" "}
              {date(n.created_at as string)}
            </summary>
            <p>{String(n.text)}</p>
            <small>
              {String(n.attribution ?? "Unattributed")} ·{" "}
              {date(n.created_at as string)}
            </small>
          </details>
        )}
      />
      {!readonly && (
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            m.mutate({
              path: `/cases/${c.id}/notes`,
              body: {
                expected_revision: c.revision,
                text: f.get("text"),
                attribution: f.get("attribution"),
                evidence_ids: String(f.get("citations") ?? "")
                  .split(",")
                  .map((x) => x.trim())
                  .filter(Boolean),
              },
            });
          }}
        >
          <label className="field">
            Note
            <textarea name="text" required rows={4} />
          </label>
          <Field label="Attribution" name="attribution" required />
          <Field
            label="Evidence IDs (optional, comma separated)"
            name="citations"
          />
          <button className="primary" disabled={m.isPending}>
            Save note
          </button>
          <CommandState m={m} />
        </form>
      )}
    </>
  );
}
function Conclusion({ c, readonly }: { c: CaseDetail; readonly: boolean }) {
  const m = useCommand();
  return (
    <>
      <h2>The qualified conclusion</h2>
      <p className="muted">
        A human assessment, bound to this revision. Describe both the collected
        evidence and what remains unresolved.
      </p>
      {readonly ? (
        <blockquote className="conclusion">
          {c.payload.conclusion || "No conclusion recorded."}
        </blockquote>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            m.mutate({
              path: `/cases/${c.id}/review-requests`,
              body: {
                expected_revision: c.revision,
                conclusion: f.get("conclusion"),
                citations: f.getAll("citation"),
              },
            });
          }}
        >
          <label className="field">
            Conclusion
            <textarea
              name="conclusion"
              defaultValue={c.payload.conclusion}
              required
              rows={7}
            />
          </label>
          <fieldset>
            <legend>Cited evidence</legend>
            {c.payload.evidence.map((e) => (
              <label className="check" key={e.id}>
                <input type="checkbox" name="citation" value={e.id} />
                <span>{e.quote.slice(0, 120)}</span>
              </label>
            ))}
          </fieldset>
          <button className="primary" disabled={m.isPending}>
            Submit frozen revision for review
          </button>
          <CommandState m={m} />
        </form>
      )}
      {c.review_requests.map((r, i) => (
        <Link className="review-link" key={i} to={`/reviews/${r.id}`}>
          Review revision {String(r.revision ?? c.revision)}{" "}
          <Badge>{pretty(r.status)}</Badge>
          <ChevronRight size={17} />
        </Link>
      ))}
    </>
  );
}
function History({ id, revision }: { id: string; revision: number }) {
  const history = useQuery({
    queryKey: ["history", id],
    queryFn: () => api.get<{ items: RecordData[] }>(`/cases/${id}/revisions`),
  });
  const [from, setFrom] = useState(Math.max(1, revision - 1));
  const diff = useQuery({
    queryKey: ["diff", id, from, revision],
    queryFn: () =>
      api.get<RecordData>(
        `/cases/${id}/revisions/${revision}/diff?from_revision=${from}`,
      ),
    enabled: revision > 1,
  });
  return (
    <>
      <h2>Immutable revision history</h2>
      {history.isPending ? (
        <Loading />
      ) : history.error ? (
        <ErrorNotice error={history.error} />
      ) : (
        <PagedList
          label="Revisions"
          items={history.data?.items ?? []}
          pageSize={5}
          renderItem={(r) => (
            <Link
              className="review-link"
              key={String(r.id ?? r.number)}
              to={`/cases/${id}/revisions/${r.number ?? r.revision}`}
            >
              Revision {String(r.number ?? r.revision)}
              <span className="muted">{date(r.created_at as string)}</span>
            </Link>
          )}
        />
      )}
      {revision > 1 && (
        <details className="event-history">
          <summary>Compare revisions</summary>
          <label className="field">
            Compare with revision
            <select
              value={from}
              onChange={(e) => setFrom(Number(e.target.value))}
            >
              {Array.from({ length: revision - 1 }, (_, i) => (
                <option key={i} value={i + 1}>
                  {i + 1}
                </option>
              ))}
            </select>
          </label>
          {diff.error ? (
            <ErrorNotice error={diff.error} />
          ) : (
            <RevisionChanges data={diff.data} />
          )}
        </details>
      )}
    </>
  );
}
function Activity({ run }: { run?: Run | null }) {
  const [eventFilter, setEventFilter] = useState("all");
  if (!run)
    return (
      <Empty title="Research has not started.">
        <p>Review a plan and start a bounded investigation.</p>
      </Empty>
    );
  return (
    <>
      <h2>Investigation activity</h2>
      {run.error && <p className="notice">{run.error}</p>}
      <div className="budget-grid">
        {Object.entries(run.budget ?? {}).map(([k, v]) => (
          <div key={k}>
            <span>{pretty(k)}</span>
            <strong>
              {String(run.usage?.[k] ?? 0)} / {v}
            </strong>
            <progress
              max={v}
              value={Number(run.usage?.[k] ?? 0)}
              aria-label={`${k} used`}
            />
          </div>
        ))}
      </div>
      <p className="muted">
        {run.usage?.cost_estimated
          ? "Costs are estimated; unknown provider outcomes retain reservations."
          : "Usage is recorded by the investigation service."}
      </p>
      {run.costs && (
        <section aria-label="Provider cost estimates">
          <h3>Provider cost estimates · USD</h3>
          <p>
            Configured-rate estimates, not verified invoices. Unknown outcomes
            keep their reservations.
          </p>
          <div className="budget-grid">
            {Object.entries(run.costs.providers).map(([provider, cost]) => (
              <div key={provider}>
                <span>{provider}</span>
                <strong>${cost.usd.toFixed(6)}</strong>
                <small>{cost.attempts} attempts</small>
                {provider !== "serpapi" && (
                  <small>
                    {cost.prompt_tokens} input / {cost.completion_tokens} output
                    tokens reported across {cost.reported_usage_calls} calls
                  </small>
                )}
              </div>
            ))}
          </div>
          <p className="muted">
            Uncertain reserved cost: $
            {run.costs.uncertain_reserved_usd.toFixed(6)}
          </p>
        </section>
      )}
      <details className="event-history">
        <summary>Run event history ({run.events?.length ?? 0})</summary>
        <label className="field">
          Show events
          <select
            value={eventFilter}
            onChange={(event) => setEventFilter(event.target.value)}
          >
            <option value="all">All events, newest first</option>
            <option value="errors">Errors and incomplete outcomes</option>
          </select>
        </label>
        <PagedList
          key={eventFilter}
          label="Events"
          pageSize={8}
          as="ol"
          items={(run.events ?? [])
            .filter(
              (event) =>
                eventFilter === "all" ||
                /ERROR|FAILED|PARTIAL|UNKNOWN|UNAVAILABLE|EXHAUSTED|CANCELLED/.test(
                  event.type.toUpperCase(),
                ),
            )
            .slice()
            .reverse()}
          renderItem={(e) => (
            <li key={e.seq}>
              <span className="event-dot" />
              <div>
                <strong>{pretty(e.type)}</strong>
                <p>
                  {String(
                    e.payload.message ??
                      e.payload.reason ??
                      e.payload.error ??
                      e.payload.query ??
                      e.payload.status ??
                      "Investigation checkpoint recorded.",
                  )}
                </p>
                {typeof e.payload.advice === "string" && (
                  <p>{e.payload.advice}</p>
                )}
                <small>{date(e.created_at)}</small>
              </div>
            </li>
          )}
        />
      </details>
    </>
  );
}
function Reviews() {
  const list = useQuery({
    queryKey: ["reviews"],
    queryFn: () => api.get<{ items: Review[] }>("/review-requests"),
  });
  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <p className="kicker">The second set of eyes</p>
          <h1>Editor review</h1>
          <p className="intro">
            Challenge the conclusion against its frozen evidence record.
          </p>
        </div>
      </div>
      {list.isPending ? (
        <Loading />
      ) : list.error ? (
        <ErrorNotice error={list.error} retry={() => list.refetch()} />
      ) : !list.data?.items.length ? (
        <Empty title="No revisions awaiting review.">
          <p>
            Researchers submit their qualified conclusions from the case
            workbench.
          </p>
        </Empty>
      ) : (
        <PagedList
          label="Reviews"
          items={list.data.items}
          pageSize={5}
          renderItem={(r) => (
            <Link className="case-row" key={r.id} to={`/reviews/${r.id}`}>
              <ClipboardCheck size={23} />
              <div className="case-text">
                <h2>
                  Case {r.case_id.slice(0, 8)} · Revision {r.revision}
                </h2>
                <p>{r.conclusion}</p>
              </div>
              <Badge>{pretty(r.status)}</Badge>
              <ChevronRight size={20} />
            </Link>
          )}
        />
      )}
    </div>
  );
}
function ReviewPage() {
  const [inspected, setInspected] = useState<Evidence | null>(null);
  const [reviewSection, setReviewSection] = useState("Conclusion");
  const { requestId } = useParams();
  const s = useSession();
  const read = useQuery({
    queryKey: ["review", requestId],
    queryFn: () =>
      api.get<Review & { snapshot?: Payload; request?: Review }>(
        `/review-requests/${requestId}`,
      ),
  });
  const m = useCommand();
  if (read.isPending) return <Loading />;
  if (read.error)
    return (
      <div className="page">
        <ErrorNotice error={read.error} retry={() => read.refetch()} />
      </div>
    );
  const raw = read.data!;
  const r = raw.request ?? raw;
  const p = raw.payload ?? raw.snapshot ?? raw.case?.payload;
  return (
    <div className="page">
      <Link className="back" to="/reviews">
        <ArrowLeft size={16} />
        Editor review
      </Link>
      <div className="page-heading">
        <div>
          <div className="case-meta">
            <Badge>{pretty(r.status)}</Badge>
            <span>Frozen revision {r.revision}</span>
          </div>
          <h1>Review case {r.case_id.slice(0, 8)}</h1>
          <p className="intro">
            This submission preserves the evidence and conclusion as reviewed.
            New case edits require a new review.
          </p>
        </div>
        <Link className="button" to={`/cases/${r.case_id}`}>
          Current case draft
        </Link>
      </div>
      <div className="review-layout">
        <section className="panel review-record">
          <div className="segmented" aria-label="Review sections">
            {["Conclusion", "Evidence", "Gaps"].map((section) => (
              <button
                key={section}
                aria-pressed={reviewSection === section}
                onClick={() => setReviewSection(section)}
              >
                {section}
              </button>
            ))}
          </div>
          {reviewSection === "Conclusion" && (
            <>
              <h2>Submitted conclusion</h2>
              <blockquote className="conclusion">
                {r.conclusion || p?.conclusion}
              </blockquote>
              <p className="muted">
                Inspect {p?.evidence.length ?? 0} evidence records and the gaps
                before recording a decision.
              </p>
            </>
          )}
          {reviewSection === "Evidence" && (
            <>
              <h2>Collected evidence</h2>
              <PagedList
                label="Review evidence"
                pageSize={2}
                items={(p?.evidence ?? [])
                  .slice()
                  .sort(
                    (a, b) =>
                      Number(b.relation === "CONTRADICTS") -
                      Number(a.relation === "CONTRADICTS"),
                  )}
                renderItem={(e) => (
                  <article className="evidence-card" key={e.id}>
                    <Relation value={e.relation} />
                    <blockquote className="record-preview">
                      {e.quote}
                    </blockquote>
                    <p className="record-preview">{e.rationale}</p>
                    <button onClick={() => setInspected(e)}>
                      Inspect cited source
                    </button>
                    <a href={`/v1/sources/${e.source_id}/download`}>
                      Download cited original
                    </a>
                  </article>
                )}
              />
            </>
          )}
          {reviewSection === "Gaps" && (
            <>
              <h2>Unresolved gaps</h2>
              <PagedList
                label="Review gaps"
                items={(p?.ledger?.gaps ?? []).filter((gap) => !gap.resolved)}
                renderItem={(g, i) => (
                  <p className="notice" key={i}>
                    {pretty(g.reason)} — {pretty(g.next_evidence_needed)}
                  </p>
                )}
              />
              {!(p?.ledger?.gaps ?? []).some((gap) => !gap.resolved) && (
                <p>
                  No unresolved gap records. This is not proof of complete
                  coverage.
                </p>
              )}
            </>
          )}
        </section>
        <section className="panel decision-panel">
          {inspected && (
            <Dialog
              title="Inspect reviewed source"
              onClose={() => setInspected(null)}
            >
              <Reader
                evidence={inspected}
                sourceId={inspected.source_id}
                source={p?.sources.find((x) => x.id === inspected.source_id)}
                revision={r.revision}
                readonly
              />
            </Dialog>
          )}
          <h2>Editorial decision</h2>
          {!["editor", "owner"].includes(s.role.toLowerCase()) ? (
            <p className="notice">
              An editor or owner must review this submission. Local development
              lets you switch identity in Workspace.
            </p>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                m.mutate({
                  path: `/review-requests/${requestId}/decisions`,
                  body: {
                    decision: f.get("decision"),
                    reason: f.get("reason"),
                    expected_revision: r.revision,
                  },
                });
              }}
            >
              <label className="field">
                Decision
                <select name="decision">
                  <option value="RETURN">Return for more work</option>
                  <option value="APPROVE">Approve qualified conclusion</option>
                </select>
              </label>
              <label className="field">
                Reason
                <textarea name="reason" required rows={5} />
              </label>
              <p className="muted">
                The reviewing identity must differ from the submitter. The
                server verifies current revision and permissions.
              </p>
              <button
                className="primary"
                disabled={m.isPending || r.status.toUpperCase() !== "OPEN"}
              >
                Record decision
              </button>
              <CommandState m={m} />
            </form>
          )}
        </section>
      </div>
    </div>
  );
}
function Workspace() {
  const s = useSession();
  const q = useQueryClient();
  const members = useQuery({
    queryKey: ["members", s.workspace.id],
    queryFn: () =>
      api.get<{ items: Member[] }>(`/workspaces/${s.workspace.id}/members`),
  });
  const m = useCommand();
  const switcher = useCommand(() => {
    q.clear();
    window.location.assign("/cases");
  });
  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <p className="kicker">Workspace controls</p>
          <h1>{s.workspace.name}</h1>
          <p className="intro">
            Manage who can research, review and administer the case record.
          </p>
        </div>
        <Badge>{pretty(s.role)}</Badge>
      </div>
      <div className="settings-grid">
        <section className="panel">
          <h2>Provider readiness</h2>
          <p className="muted">
            Credentials stay on the server. A configured connection is not a
            measured accuracy result.
          </p>
          {Object.entries(s.providers).map(([k, v]) => (
            <div className="readiness" key={k}>
              <span>
                {k === "serpapi"
                  ? "SerpApi discovery"
                  : `${pretty(k)} analysis`}
              </span>
              <Badge tone={v ? "support" : "warn"}>
                {v ? "Configured" : "Not configured"}
              </Badge>
            </div>
          ))}
          <p className="notice">
            Synthetic fixtures are available for reproducible evaluation. Their
            results are always labeled.
          </p>
        </section>
        <section className="panel">
          <h2>Session</h2>
          <p>
            {s.user.name} · {pretty(s.role)}
          </p>
          {s.mode === "development" && (
            <>
              <label className="field">
                Local development identity
                <select
                  aria-label="Local development identity"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value)
                      switcher.mutate({
                        path: "/auth/dev",
                        body: { user_id: e.target.value },
                      });
                  }}
                >
                  <option value="" disabled>
                    Switch identity
                  </option>
                  <option value="researcher">Researcher</option>
                  <option value="editor">Editor</option>
                  <option value="owner">Owner</option>
                </select>
              </label>
              <p className="muted">
                Identity switching is a local development facility.
              </p>
              <CommandState m={switcher} />
            </>
          )}
        </section>
        <section className="panel members">
          <h2>Memberships</h2>
          {members.isPending ? (
            <Loading />
          ) : members.error ? (
            <ErrorNotice error={members.error} />
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Member</th>
                    <th>Role</th>
                  </tr>
                </thead>
                <tbody>
                  {members.data?.items.map((x) => (
                    <tr key={x.user_id}>
                      <td>{x.name ?? x.user_id}</td>
                      <td>
                        {s.role.toLowerCase() === "owner" ? (
                          <select
                            aria-label={`Role for ${x.name ?? x.user_id}`}
                            value={x.role.toLowerCase()}
                            onChange={(e) =>
                              m.mutate({
                                path: `/workspaces/${s.workspace.id}/members/${x.user_id}`,
                                method: "PATCH",
                                body: { role: e.target.value },
                              })
                            }
                          >
                            {["researcher", "editor", "owner", "removed"].map(
                              (role) => (
                                <option key={role}>{role}</option>
                              ),
                            )}
                          </select>
                        ) : (
                          pretty(x.role)
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {s.role.toLowerCase() === "owner" && (
            <form
              className="inline-form"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                m.mutate({
                  path: `/workspaces/${s.workspace.id}/members`,
                  body: { user_id: f.get("user"), role: f.get("role") },
                });
              }}
            >
              <Field label="User ID" name="user" required />
              <label className="field">
                Role
                <select name="role">
                  <option>researcher</option>
                  <option>editor</option>
                  <option>owner</option>
                </select>
              </label>
              <button className="primary" disabled={m.isPending}>
                Add member
              </button>
            </form>
          )}
          <CommandState m={m} />
        </section>
      </div>
    </div>
  );
}

function RevisionChanges({ data }: { data?: RecordData }) {
  const changes = (data?.changes ?? {}) as Record<
    string,
    { before: unknown; after: unknown }
  >;
  const summarize = (value: unknown): ReactNode => {
    if (value === null || value === undefined)
      return <p className="muted">Not recorded</p>;
    if (typeof value === "string") return <p>{value || "Not recorded"}</p>;
    if (Array.isArray(value))
      return (
        <>
          <p className="muted">{value.length} records</p>
          <ul>
            {value.slice(0, 10).map((item, i) => (
              <li key={i}>
                {typeof item === "object" && item !== null
                  ? String(
                      item.text ??
                        item.title ??
                        item.quote ??
                        item.reason ??
                        item.conclusion ??
                        item.stage ??
                        item.kind ??
                        "Preserved record",
                    )
                  : String(item)}
              </li>
            ))}
          </ul>
        </>
      );
    return (
      <p className="muted">
        Structured record changed. Inspect the frozen revision for its complete
        evidence and observations.
      </p>
    );
  };
  return (
    <div className="revision-changes">
      {Object.keys(changes).length === 0 ? (
        <p className="muted">No changes between these revisions.</p>
      ) : (
        Object.entries(changes).map(([field, change]) => (
          <article key={field}>
            <h3>{pretty(field)}</h3>
            <div className="revision-columns">
              <section>
                <h4>Before</h4>
                {summarize(change.before)}
              </section>
              <section>
                <h4>Current revision</h4>
                {summarize(change.after)}
              </section>
            </div>
          </article>
        ))
      )}
    </div>
  );
}
