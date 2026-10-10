/** Preserve incomplete outcomes, while making recovery understandable to researchers. */
export function RunStatusNotice({ error }: { error: string }) {
  const budget = error.startsWith("BUDGET_EXHAUSTED:")
    ? error.split(":")[1]
    : null;
  const resource: Record<string, string> = {
    tokens: "token",
    searches: "search",
    documents: "document",
    rounds: "research-round",
    seconds: "time",
    usd: "estimated cost",
  };
  const rateLimited = error.includes("PROVIDER_HTTP_429");
  const title = budget
    ? `Investigation stopped at the ${resource[budget] ?? "configured"} limit`
    : rateLimited
      ? "The provider reached its rate limit"
      : "Investigation needs attention";
  const advice = budget
    ? "Collected records are preserved. Review the partial results, narrow the claim or source set, then start a new investigation."
    : rateLimited
      ? "Collected records are preserved. Wait for the provider's limit to reset, then start a new investigation. An explicitly rejected request does not consume the run's token or cost allowance."
      : "Collected records are preserved. Review the activity details and provider configuration before starting another investigation.";
  return (
    <div className="notice" role="status">
      <strong>{title}</strong>
      <p>{advice}</p>
      <details>
        <summary>Technical details</summary>
        <code>{error}</code>
      </details>
    </div>
  );
}
