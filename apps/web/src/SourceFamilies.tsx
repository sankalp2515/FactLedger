import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type { Source, RecordData } from "./contracts";
export function SourceFamilies({
  caseId,
  revision,
  readonly,
  sources,
  edges,
}: {
  caseId: string;
  revision: number;
  readonly: boolean;
  sources: Source[];
  edges: RecordData[];
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const query = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({
      id,
      status,
      reason,
    }: {
      id: string;
      status: string;
      reason: string;
    }) =>
      api.command(
        `/lineage/${id}`,
        { case_id: caseId, expected_revision: revision, status, reason },
        "PATCH",
      ),
    onSuccess: () => {
      query.invalidateQueries();
      setEditing(null);
    },
  });
  return (
    <section>
      <h2>Source families</h2>
      <p className="muted">
        Repeated reporting can share an originating record. Source counts do not
        establish a finding.
      </p>
      {edges.length === 0 ? (
        <div className="empty">
          <h3>No source relationships recorded.</h3>
          <p>
            Independent sourcing has not been established simply because no
            dependency was found.
          </p>
        </div>
      ) : (
        edges.map((edge, i) => {
          const edgeId = String(edge.id ?? i);
          const ids = Array.isArray(edge.source_ids)
            ? edge.source_ids.map(String)
            : [
                String(edge.from_source_id ?? ""),
                String(edge.to_source_id ?? ""),
              ];
          return (
            <article className="source-family" key={edgeId}>
              <div className="family-heading">
                <h3>
                  {String(edge.kind ?? "Source relationship")
                    .replaceAll("_", " ")
                    .toLowerCase()}
                </h3>
                <span className="badge">
                  {String(edge.status ?? edge.confidence ?? "Proposed")
                    .replaceAll("_", " ")
                    .toLowerCase()}
                </span>
              </div>
              <ul>
                {ids.map((id) => (
                  <li key={id}>
                    {sources.find((s) => s.id === id)?.title ?? id}
                  </li>
                ))}
              </ul>
              <p>
                {String(
                  edge.reason ??
                    "Content relationship recorded; inspect each source independently.",
                )}
              </p>
              {!readonly && !!edge.id && (
                <button onClick={() => setEditing(edgeId)}>
                  Correct source relationship
                </button>
              )}
              {editing === edgeId && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    mutation.mutate({
                      id: edgeId,
                      status: String(f.get("status")),
                      reason: String(f.get("reason")),
                    });
                  }}
                >
                  <label className="field">
                    Relationship status
                    <select name="status">
                      <option value="POSSIBLE">Possible dependence</option>
                      <option value="HUMAN_CONFIRMED">Human confirmed</option>
                      <option value="REJECTED">Rejected</option>
                    </select>
                  </label>
                  <label className="field">
                    Reason
                    <textarea name="reason" required minLength={3} />
                  </label>
                  <button className="primary" disabled={mutation.isPending}>
                    Save relationship correction
                  </button>
                  {mutation.error && (
                    <p role="alert" className="error">
                      {mutation.error.message}
                    </p>
                  )}
                </form>
              )}
            </article>
          );
        })
      )}
    </section>
  );
}
