import { expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { BudgetFields, validBudget } from "./BudgetFields";

it("allows a bounded live budget and rejects blank or excessive limits", () => {
  const budget = {
    searches: 2,
    documents: 4,
    rounds: 1,
    tokens: 60000,
    seconds: 180,
    usd: 0.25,
  };
  const change = vi.fn();
  render(<BudgetFields budget={budget} onChange={change} />);
  fireEvent.change(screen.getByLabelText("USD estimate limit"), {
    target: { value: "0.1" },
  });
  expect(change).toHaveBeenCalledWith({ ...budget, usd: 0.1 });
  expect(validBudget(budget)).toBe(true);
  expect(validBudget({ ...budget, usd: 0 })).toBe(false);
  expect(validBudget({ ...budget, searches: 13 })).toBe(false);
  expect(validBudget({ ...budget, tokens: 100.5 })).toBe(false);
});
