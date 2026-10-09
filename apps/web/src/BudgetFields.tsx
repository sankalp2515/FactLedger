const limits = {
  searches: ["Search limit", 1, 12, 1],
  documents: ["Document limit", 1, 30, 1],
  rounds: ["Round limit", 1, 3, 1],
  tokens: ["Token limit", 100, 60000, 1],
  seconds: ["Time limit (seconds)", 10, 600, 1],
  usd: ["USD estimate limit", 0.001, 2, 0.001],
} as const;

export function validBudget(budget: Record<string, number>) {
  return Object.entries(limits).every(([key, [, min, max]]) => {
    const value = budget[key];
    return (
      Number.isFinite(value) &&
      value >= min &&
      value <= max &&
      (key === "usd" || Number.isInteger(value))
    );
  });
}

export function BudgetFields({
  budget,
  onChange,
}: {
  budget: Record<string, number>;
  onChange: (budget: Record<string, number>) => void;
}) {
  return (
    <fieldset>
      <legend>Investigation limits</legend>
      <div className="budget-grid">
        {Object.entries(limits).map(([key, [label, min, max, step]]) => (
          <label className="field" key={key}>
            {label}
            <input
              type="number"
              min={min}
              max={max}
              step={step}
              required
              value={Number.isFinite(budget[key]) ? budget[key] : ""}
              onChange={(event) =>
                onChange({
                  ...budget,
                  [key]:
                    event.target.value === ""
                      ? NaN
                      : Number(event.target.value),
                })
              }
            />
          </label>
        ))}
      </div>
      <p className="muted">
        USD is a configured-rate estimate, not a provider invoice. Runs stop at
        the first exhausted limit.
      </p>
    </fieldset>
  );
}
