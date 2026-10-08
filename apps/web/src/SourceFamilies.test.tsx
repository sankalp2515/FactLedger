import { it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SourceFamilies } from "./SourceFamilies";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
it("labels proposed source dependence and keeps duplicated source counts out of conclusions", () => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <SourceFamilies
        caseId="c"
        revision={2}
        readonly
        sources={[
          {
            id: "a",
            title: "Original order",
            url: "https://example.org/order",
            status: "ACQUIRED",
          },
          {
            id: "b",
            title: "Repeated reporting",
            url: "https://example.org/news",
            status: "ACQUIRED",
          },
        ]}
        edges={[
          {
            id: "e",
            kind: "POSSIBLE_DEPENDENCE",
            source_ids: ["a", "b"],
            status: "POSSIBLE",
            reason: "Attributed origin",
          },
        ]}
      />
    </QueryClientProvider>,
  );
  expect(screen.getByText("Original order")).toBeInTheDocument();
  expect(screen.getByText("Repeated reporting")).toBeInTheDocument();
  expect(screen.getByText(/possible dependence/i)).toBeInTheDocument();
  expect(
    screen.getByText(/Source counts do not establish a finding/),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Correct source relationship" }),
  ).toBeNull();
});
