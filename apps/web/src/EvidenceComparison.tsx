import type { RecordData } from "./contracts";
const sentence = (value: unknown) => {
  if (value === null || value === undefined || value === "") return "Unknown";
  const text = String(value).replaceAll("_", " ").toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
};
const name = (key: string) =>
  ({
    stage: "Delivery stage",
    measure: "Measure",
    geography: "Geography",
    period: "Period",
    denominator: "Denominator",
    attribution: "Attribution",
    value: "Quantity",
  })[key] ?? sentence(key);
export function EvidenceComparison({ comparison }: { comparison: RecordData }) {
  const claim = (comparison.claim ?? {}) as RecordData;
  const observed = (comparison.observed ?? {}) as RecordData;
  const gaps = Array.isArray(comparison.gaps)
    ? Array.from(new Set(comparison.gaps.map(String)))
    : [];
  const keys = [
    "stage",
    "measure",
    "value",
    "geography",
    "period",
    "denominator",
    "attribution",
  ].filter(
    (key) =>
      (claim[key] !== undefined && claim[key] !== null) ||
      (observed[key] !== undefined && observed[key] !== null),
  );
  const display = (record: RecordData, key: string) =>
    key === "value"
      ? `${record.value ?? "Unknown"} ${record.unit ?? ""}`.trim()
      : ["stage", "measure"].includes(key)
        ? sentence(record[key])
        : String(record[key] ?? "Unknown");
  if (!keys.length)
    return (
      <div className="comparison-summary">
        Scope comparison is not available for this record.
      </div>
    );
  return (
    <div className="comparison-summary">
      <div className="comparison-row comparison-labels">
        <span />
        <span>Claim</span>
        <span>Collected record</span>
      </div>
      {keys.map((key) => (
        <div
          className={`comparison-row ${gaps.includes(key) ? "has-gap" : ""}`}
          key={key}
        >
          <span>{name(key)}</span>
          <span>{display(claim, key)}</span>
          <span>{display(observed, key)}</span>
        </div>
      ))}
      {gaps.length > 0 && (
        <div className="comparison-gaps">
          Unresolved: {gaps.map((key) => name(key).toLowerCase()).join(", ")}
        </div>
      )}
    </div>
  );
}
