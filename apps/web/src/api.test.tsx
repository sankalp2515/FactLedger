import { describe, it, expect, vi, afterEach } from "vitest";
import { ApiClient, ApiError } from "./api";
import { render, screen } from "@testing-library/react";
import { AnchorText } from "./AnchorText";
afterEach(() => vi.unstubAllGlobals());
describe("authenticated API commands", () => {
  it("sends cookie credentials and CSRF for mutations without exposing token in URL", async () => {
    let request: RequestInit | undefined;
    let url = "";
    vi.stubGlobal("fetch", async (u: string, i: RequestInit) => {
      url = u;
      request = i;
      return new Response('{"revision":2}', { status: 200 });
    });
    const client = new ApiClient();
    client.csrf = "private-token";
    expect(
      await client.command("/cases/c/scope", {
        expected_revision: 1,
        claims: [],
      }),
    ).toEqual({ revision: 2 });
    expect(request?.credentials).toBe("same-origin");
    expect(new Headers(request?.headers).get("X-CSRF-Token")).toBe(
      "private-token",
    );
    expect(url).toBe("/v1/cases/c/scope");
  });
  it("preserves revision-conflict code and message for actionable recovery", async () => {
    vi.stubGlobal(
      "fetch",
      async () =>
        new Response(
          '{"detail":{"code":"SCOPE_CHANGED","message":"Claim scope changed"}}',
          { status: 409 },
        ),
    );
    await expect(
      new ApiClient().command("/runs/r/integrate", {}),
    ).rejects.toMatchObject({
      status: 409,
      code: "SCOPE_CHANGED",
      message: "Claim scope changed",
    });
  });
  it("does not disguise unauthorized reads as empty successful data", async () => {
    vi.stubGlobal(
      "fetch",
      async () =>
        new Response('{"detail":"Session required"}', { status: 401 }),
    );
    await expect(new ApiClient().get("/cases")).rejects.toBeInstanceOf(
      ApiError,
    );
  });
});
describe("original source reader", () => {
  it("highlights only the exact anchored characters and renders hostile markup as text", () => {
    render(
      <AnchorText
        text={"Before <script>bad</script> after"}
        anchor={{ start: 7, end: 27 }}
      />,
    );
    expect(screen.getByText("<script>bad</script>").tagName).toBe("MARK");
    expect(document.querySelector("script")).toBeNull();
    expect(screen.getByText(/Before/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Jump to quotation" }),
    ).toBeInTheDocument();
  });
  it("keeps invalid anchors unhighlighted instead of inventing a quote", () => {
    const { container } = render(
      <AnchorText text="Original text" anchor={{ start: 100, end: 110 }} />,
    );
    expect(container.querySelector("mark")).toBeNull();
    expect(screen.getByText("Original text")).toBeInTheDocument();
  });
});
