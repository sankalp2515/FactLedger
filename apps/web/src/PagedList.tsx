import { useState, useRef, type ReactNode } from "react";

export function PagedList<T>({
  items,
  label,
  pageSize = 2,
  renderItem,
  as = "div",
}: {
  items: readonly T[];
  label: string;
  pageSize?: number;
  renderItem: (item: T, index: number) => ReactNode;
  as?: "div" | "ol";
}) {
  const [page, setPage] = useState(0);
  const container = useRef<HTMLDivElement>(null);
  const turnPage = (next: number) => {
    setPage(next);
    container.current?.scrollIntoView?.({ block: "start" });
  };
  const pages = Math.max(1, Math.ceil(items.length / pageSize));
  const current = Math.min(page, pages - 1);
  const start = current * pageSize;
  const List = as;
  return (
    <div className="record-page" ref={container}>
      <List className={as === "ol" ? "activity" : "paged-items"}>
        {items
          .slice(start, start + pageSize)
          .map((item, index) => renderItem(item, start + index))}
      </List>
      {pages > 1 && (
        <nav className="pagination" aria-label={`${label} pagination`}>
          <button
            type="button"
            aria-label={`Previous ${label}`}
            disabled={current === 0}
            onClick={() => turnPage(current - 1)}
          >
            Previous
          </button>
          <span role="status" aria-live="polite">
            {start + 1}–{Math.min(start + pageSize, items.length)} of{" "}
            {items.length}
          </span>
          <button
            type="button"
            aria-label={`Next ${label}`}
            disabled={current === pages - 1}
            onClick={() => turnPage(current + 1)}
          >
            Next
          </button>
        </nav>
      )}
    </div>
  );
}
