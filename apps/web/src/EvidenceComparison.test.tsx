import { it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EvidenceComparison } from "./EvidenceComparison";
it("explains claim and observed stages as readable comparisons without exposing transport JSON", () => {
  const { container } = render(
    <EvidenceComparison
      comparison={{
        claim: {
          stage: "OPERATIONAL",
          geography: "District A",
          period: "2026-09",
          value: "200",
          unit: "beds",
          measure: "CAPACITY",
        },
        observed: {
          stage: "INAUGURATED",
          geography: "District A",
          period: "2026-09",
          value: "200",
          unit: "beds",
          measure: "CAPACITY",
        },
        quantity: {
          comparable: true,
          equal: true,
          left_normalized: "200",
          right_normalized: "200",
          operands: [{ value: "200" }, { value: "200" }],
        },
        gaps: ["stage", "attribution"],
      }}
    />,
  );
  expect(screen.getByText("Claim")).toBeInTheDocument();
  expect(screen.getByText("Collected record")).toBeInTheDocument();
  expect(screen.getByText("Operational")).toBeInTheDocument();
  expect(screen.getByText("Inaugurated")).toBeInTheDocument();
  expect(
    screen.getByText("Unresolved: delivery stage, attribution"),
  ).toBeInTheDocument();
  expect(container.textContent).not.toContain("left_normalized");
  expect(container.textContent).not.toContain("{");
});
