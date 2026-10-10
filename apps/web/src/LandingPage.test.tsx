import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("explains the product and offers workspace access without creating a session", () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(
    screen.getByRole("heading", {
      level: 1,
      name: "Every claim deserves an evidence trail.",
    }),
  ).toBeInTheDocument();
  expect(
    screen.getAllByRole("link", { name: "Open workspace" })[0],
  ).toHaveAttribute("href", "/cases");
  expect(fetch).not.toHaveBeenCalled();
});

it("shows how changing the asserted stage changes the evidence comparison", () => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Operational" }));
  expect(screen.getByText("Operation is not established")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Inaugurated" }));
  expect(screen.getByText("The stages match")).toBeInTheDocument();
  expect(
    screen.getByText("Illustrative comparison · synthetic record"),
  ).toBeInTheDocument();
});
