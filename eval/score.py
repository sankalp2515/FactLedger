"""Score evidence-pair relations without confusing abstention with correctness."""

import argparse
import json
from math import sqrt
from pathlib import Path

RELATIONS = {"SUPPORTS", "CONTRADICTS", "CONTEXT", "INCOMPARABLE", "INSUFFICIENT"}
DECISIVE = {"SUPPORTS", "CONTRADICTS"}


def score(rows: list[dict]) -> dict:
    seen = set()
    correct = decisive = abstentions = exact = 0
    confusion = {label: dict.fromkeys(sorted(RELATIONS), 0) for label in sorted(RELATIONS)}
    use_cases = {}
    for row in rows:
        identity = row.get("id")
        if not identity or identity in seen:
            raise ValueError("Every evidence pair needs a unique id")
        seen.add(identity)
        label, prediction = row.get("label"), row.get("prediction")
        if label not in RELATIONS or prediction not in RELATIONS:
            raise ValueError(f"Invalid or missing relation for pair {identity}")
        confusion[label][prediction] += 1
        use_case = row.get("use_case", "unspecified")
        use_cases[use_case] = use_cases.get(use_case, 0) + 1
        decisive += prediction in DECISIVE
        correct += prediction in DECISIVE and prediction == label
        abstentions += prediction == "INSUFFICIENT"
        exact += prediction == label
    total = len(rows)
    interval = None
    if decisive:
        fraction, z = correct / decisive, 1.959963984540054
        denominator = 1 + z * z / decisive
        center = (fraction + z * z / (2 * decisive)) / denominator
        margin = (
            z * sqrt(fraction * (1 - fraction) / decisive + z * z / (4 * decisive * decisive)) / denominator
        )
        interval = [max(0, center - margin), min(1, center + margin)]
    return {
        "pairs": total,
        "decisive_predictions": decisive,
        "correct_decisive": correct,
        "decisive_precision": correct / decisive if decisive else None,
        "decisive_coverage": decisive / total if total else None,
        "abstention_rate": abstentions / total if total else None,
        "exact_relation_accuracy": exact / total if total else None,
        "decisive_precision_95pct_wilson_interval": interval,
        "relation_confusion_rows_label_columns_prediction": confusion,
        "use_case_counts": use_cases,
        "interpretation": "Only independently adjudicated labels support an external quality claim.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pairs", type=Path, help="JSONL with id, label and prediction")
    args = parser.parse_args()
    rows = [
        json.loads(line) for line in args.pairs.read_text(encoding="utf-8-sig").splitlines() if line.strip()
    ]
    report = score(rows)
    origins = sorted({row.get("label_origin", "unspecified") for row in rows})
    report["label_origins"] = origins
    report["independent_quality_gate_eligible"] = bool(rows) and origins == ["independent-adjudicated"]
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
