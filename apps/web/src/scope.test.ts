import { expect, it } from "vitest";
import { scopeInput } from "./scope";

it("resubmits editable scope without server revision metadata", () => {
  const claim = {
    id: "old",
    version: 2,
    text: "Operational",
    subject: "Hospital",
    geography: "District",
    period: "2026-09",
    stage: "OPERATIONAL",
    measure: "",
  };
  expect(scopeInput(claim)).toEqual({
    text: "Operational",
    subject: "Hospital",
    geography: "District",
    period: "2026-09",
    stage: "OPERATIONAL",
    measure: "",
  });
});
