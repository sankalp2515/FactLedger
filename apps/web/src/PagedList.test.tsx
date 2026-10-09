import { afterEach, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { PagedList } from "./PagedList";
afterEach(cleanup);

it("keeps long records bounded and makes every item reachable", () => {
  render(
    <PagedList
      label="Evidence"
      items={[1, 2, 3, 4, 5]}
      pageSize={2}
      renderItem={(item) => <p key={item}>Record {item}</p>}
    />,
  );
  expect(screen.getByText("Record 1")).toBeInTheDocument();
  expect(screen.queryByText("Record 3")).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Previous Evidence" }),
  ).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Next Evidence" }));
  expect(screen.getByText("Record 3")).toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent("3–4 of 5");
  fireEvent.click(screen.getByRole("button", { name: "Next Evidence" }));
  expect(screen.getByText("Record 5")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Next Evidence" })).toBeDisabled();
});

it("keeps a valid page when records shrink and exposes all records on small lists", () => {
  const view = render(
    <PagedList
      label="Sources"
      items={[1, 2, 3]}
      pageSize={2}
      renderItem={(item) => <p key={item}>Source {item}</p>}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Next Sources" }));
  view.rerender(
    <PagedList
      label="Sources"
      items={[1]}
      pageSize={2}
      renderItem={(item) => <p key={item}>Source {item}</p>}
    />,
  );
  expect(screen.getByText("Source 1")).toBeInTheDocument();
  expect(
    screen.queryByRole("navigation", { name: "Sources pagination" }),
  ).not.toBeInTheDocument();
});
