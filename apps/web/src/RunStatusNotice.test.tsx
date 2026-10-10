import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { RunStatusNotice } from "./RunStatusNotice";

afterEach(cleanup);

it("explains a token stop and keeps the technical code in collapsed details", () => {
  render(<RunStatusNotice error="BUDGET_EXHAUSTED:tokens" />);
  expect(screen.getByRole("status")).toHaveTextContent(/token limit/i);
  expect(screen.getByRole("status")).toHaveTextContent(/collected records/i);
  const code = screen.getByText("BUDGET_EXHAUSTED:tokens");
  expect(code.closest("details")).not.toHaveAttribute("open");
  expect(screen.getByText(/start a new investigation/i)).toBeInTheDocument();
});

it("distinguishes provider rate limits from the application token budget", () => {
  render(<RunStatusNotice error="ModelError:MODEL_PROVIDER_HTTP_429" />);
  expect(screen.getByRole("status")).toHaveTextContent(/provider.*rate limit/i);
  expect(screen.getByRole("status")).toHaveTextContent(/wait/i);
  expect(screen.getByRole("status")).not.toHaveTextContent(/token limit/i);
});
