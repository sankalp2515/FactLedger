import { it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "./App";
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("offers hosted sign-in when authentication is required", async () => {
  vi.stubGlobal("fetch", async () =>
    Response.json(
      { code: "AUTH_REQUIRED", message: "Sign in" },
      { status: 401 },
    ),
  );
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(
    await screen.findByRole("link", { name: "Sign in to your newsroom" }),
  ).toHaveAttribute("href", "/v1/auth/login");
  expect(
    screen.queryByRole("button", { name: "Enter local research workspace" }),
  ).not.toBeInTheDocument();
});
it("shows the empty library and creates a case through the server", async () => {
  let created = false;
  vi.stubGlobal("fetch", async (url: string, init?: RequestInit) => {
    if (url === "/v1/session")
      return Response.json({
        user: { id: "researcher", name: "Researcher" },
        workspace: { id: "w", name: "Newsroom" },
        role: "researcher",
        csrf_token: "token",
        mode: "development",
        providers: { serpapi: false },
      });
    if (url === "/v1/cases" && init?.method === "POST") {
      created = JSON.parse(String(init.body)).title === "Water supply";
      return Response.json({ id: "c", title: "Water supply", revision: 1 });
    }
    if (url.startsWith("/v1/cases?"))
      return Response.json({ items: [], next_cursor: null });
    return Response.json({
      id: "c",
      title: "Water supply",
      original_claim: "Daily service",
      revision: 1,
      state: "DRAFT",
      tags: [],
      payload: {
        claims: [],
        sources: [],
        evidence: [],
        ledger: { stages: [], funding: [], metrics: [], derived: [], gaps: [] },
        notes: [],
        projects: [],
        lineage: [],
        conclusion: "",
      },
      latest_run: null,
      review_requests: [],
    });
  });
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={["/cases"]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(
    await screen.findByText("Your next investigation starts here."),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("link", { name: "New case" }));
  fireEvent.change(screen.getByLabelText("Case title"), {
    target: { value: "Water supply" },
  });
  fireEvent.change(screen.getByLabelText("Original claim"), {
    target: { value: "Daily service" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create case" }));
  await waitFor(() => expect(created).toBe(true));
  expect(
    await screen.findByRole("heading", { name: "Water supply" }),
  ).toBeInTheDocument();
});
it("exposes an unavailable API with a retry action instead of a fixture result", async () => {
  vi.stubGlobal(
    "fetch",
    async () =>
      new Response('{"detail":"Service temporarily unavailable"}', {
        status: 503,
      }),
  );
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Service temporarily unavailable",
  );
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
});
it("keeps progressive fixture results separate and shows scope conflicts when integrating", async () => {
  const payload = {
    claims: [],
    sources: [],
    evidence: [],
    ledger: { stages: [], funding: [], metrics: [], derived: [], gaps: [] },
    notes: [],
    projects: [],
    lineage: [],
    conclusion: "",
  };
  const run = {
    id: "r",
    case_id: "c",
    base_revision: 1,
    state: "COMPLETED",
    mode: "fixture",
    plan: {},
    budget: {},
    usage: {},
    results: payload,
    events: [],
  };
  let sentRevision = 0;
  vi.stubGlobal("fetch", async (url: string, init?: RequestInit) => {
    if (url === "/v1/session")
      return Response.json({
        user: { id: "researcher", name: "Researcher" },
        workspace: { id: "w", name: "Newsroom" },
        role: "researcher",
        csrf_token: "token",
        mode: "development",
        providers: { serpapi: false },
      });
    if (url === "/v1/runs/r/integrate") {
      sentRevision = JSON.parse(String(init?.body)).expected_revision;
      return Response.json(
        {
          code: "SCOPE_CHANGED",
          message: "These results belong to an earlier claim scope.",
        },
        { status: 409 },
      );
    }
    if (url === "/v1/runs/r") return Response.json(run);
    return Response.json({
      id: "c",
      title: "Current draft",
      original_claim: "Changed claim",
      revision: 3,
      state: "DRAFT",
      tags: [],
      payload,
      latest_run: run,
      review_requests: [],
    });
  });
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={["/cases/c/runs/r"]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(await screen.findByText("Synthetic fixture")).toBeInTheDocument();
  expect(
    screen.getByText("Run-owned results · not integrated"),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Integrate results" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "earlier claim scope",
  );
  expect(sentRevision).toBe(3);
  expect(
    screen.getByText("Run-owned results · not integrated"),
  ).toBeInTheDocument();
});
it("returns to the current draft after successful explicit integration", async () => {
  const payload = {
    claims: [],
    sources: [],
    evidence: [],
    ledger: { stages: [], funding: [], metrics: [], derived: [], gaps: [] },
    notes: [],
    projects: [],
    lineage: [],
    conclusion: "",
  };
  const run = {
    id: "r",
    case_id: "c",
    base_revision: 1,
    state: "COMPLETED",
    mode: "fixture",
    plan: {},
    budget: {},
    usage: {},
    results: payload,
    events: [],
  };
  let integrated = false;
  vi.stubGlobal("fetch", async (url: string) => {
    if (url === "/v1/session")
      return Response.json({
        user: { id: "researcher", name: "Researcher" },
        workspace: { id: "w", name: "Newsroom" },
        role: "researcher",
        csrf_token: "token",
        mode: "development",
        providers: { serpapi: false },
      });
    if (url === "/v1/runs/r/integrate") integrated = true;
    if (url === "/v1/runs/r") return Response.json(run);
    return Response.json({
      id: "c",
      title: "Current draft",
      original_claim: "Claim",
      revision: integrated ? 4 : 3,
      state: "READY_FOR_REVIEW",
      tags: [],
      payload,
      latest_run: {
        ...run,
        checkpoint: integrated ? { integrated_revision: 4 } : {},
      },
      review_requests: [],
    });
  });
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={["/cases/c/runs/r"]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Integrate results" }),
  );
  await waitFor(() =>
    expect(screen.queryByText("Run-owned results · not integrated")).toBeNull(),
  );
  expect(
    screen.queryByRole("button", { name: "Integrate results" }),
  ).toBeNull();
});
it("lets an editor inspect frozen cited evidence without showing research correction actions", async () => {
  const evidence = {
    id: "e",
    claim_id: "cl",
    source_id: "s",
    relation: "CONTEXT",
    quote: "The hospital was inaugurated.",
    anchor: { start: 0, end: 29 },
    rationale: "Inauguration does not establish operation.",
    comparison: {
      claim: { stage: "OPERATIONAL" },
      observed: { stage: "INAUGURATED" },
      gaps: ["stage"],
    },
  };
  vi.stubGlobal("fetch", async (url: string) => {
    if (url === "/v1/session")
      return Response.json({
        user: { id: "editor", name: "Editor" },
        workspace: { id: "w", name: "Newsroom" },
        role: "editor",
        csrf_token: "token",
        mode: "development",
        providers: { serpapi: false },
      });
    if (url === "/v1/sources/s")
      return Response.json({
        id: "s",
        title: "Original record",
        url: "https://example.org",
        status: "ACQUIRED",
        text: "The hospital was inaugurated.",
        metadata: {},
      });
    return Response.json({
      id: "review",
      case_id: "c",
      revision: 3,
      current_revision: 3,
      status: "OPEN",
      conclusion: "Operation remains unestablished.",
      payload: {
        claims: [],
        sources: [
          {
            id: "s",
            title: "Original record",
            status: "ACQUIRED",
            url: "https://example.org",
          },
        ],
        evidence: [evidence],
        ledger: { stages: [], funding: [], metrics: [], derived: [], gaps: [] },
        notes: [],
        projects: [],
        lineage: [],
        conclusion: "",
      },
    });
  });
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={["/reviews/review"]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Inspect cited source" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Original record" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Correct evidence relation" }),
  ).toBeNull();
  expect(
    screen.getByRole("button", { name: "Record decision" }),
  ).toBeInTheDocument();
  expect(screen.queryByText(/"stage"/)).toBeNull();
});
