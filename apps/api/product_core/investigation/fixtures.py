"""Explicitly fictional ten-case deterministic offline fixture records."""

from .acquisition import AcquiredDocument

CASES = [
    ("Hospital A", "OPERATIONAL", "CAPACITY", "200", "beds", "INAUGURATED", "CAPACITY", "200", "beds"),
    ("Programme B", None, "EXPENDED", "500", "crore", None, "ALLOCATED", "500", "crore"),
    ("Corridor C", "OPERATIONAL", "LENGTH", "80", "km", "OPERATIONAL", "LENGTH", "20", "km"),
    ("Block D", None, "SERVICE_FREQUENCY", "10000", "households", None, "CONNECTIONS", "10000", "households"),
    (
        "School E",
        "OPERATIONAL",
        "ENROLLMENT",
        "800",
        "students",
        "PHYSICALLY_COMPLETED",
        "CAPACITY",
        "800",
        "seats",
    ),
    ("Scheme F", None, "OCCUPIED", "2000", "families", None, "APPROVED_BENEFICIARIES", "2000", "families"),
    ("Initiative G", None, "JOBS_CREATED", "5000", "persons", None, "PLACED", "5000", "offers"),
    ("Project H", "OPERATIONAL", "CAPACITY", "100", "MW", "APPROVED", "CAPACITY", "100", "MW"),
    (
        "Programme I",
        None,
        "PAID_BENEFICIARIES",
        "100000",
        "persons",
        None,
        "REGISTERED",
        "100000",
        "accounts",
    ),
    ("Hospital J", "OPERATIONAL", "CAPACITY", "200", "beds", "OPERATIONAL", "CAPACITY", "200", "beds"),
]


def fixture_document(number: int) -> AcquiredDocument:
    if not 1 <= number <= 10:
        raise ValueError("UNKNOWN_FIXTURE")
    subject, _, _, _, _, stage, measure, value, unit = CASES[number - 1]
    text = f"SYNTHETIC UC-{number:02}: {subject} record for District A during 2026-09 reports {stage or measure}: {value} {unit}. This fictional fixture is not a real public record."
    fact = {
        "quote": text,
        "subject": subject,
        "geography": "District A",
        "period": "2026-09",
        "stage": stage,
        "measure": measure,
        "value": value,
        "unit": unit,
        "relation": "SUPPORTS",
        "attribution": "Synthetic public authority",
        "event_date": "2026-09-30",
    }
    if measure in {"ALLOCATED", "EXPENDED"}:
        fact["currency"] = "INR"
    return AcquiredDocument(
        f"Synthetic UC-{number:02} record",
        text,
        text.encode(),
        "text/plain",
        {
            "synthetic": True,
            "fixture_case": f"UC-{number:02}",
            "source_type": "synthetic",
            "extraction_version": "fixture-v1",
            "facts": [fact],
            "publication_date": "2026-10-01",
            "event_date": "2026-09-30",
            "date_provenance": "synthetic",
        },
    )


def fixture_for_claim(claim: dict) -> AcquiredDocument:
    # Scope remains user-owned. A fixture gives contextual, never invented live evidence.
    measure = claim.get("measure", "")
    stage = claim.get("stage", "")
    number = next(
        (i for i, row in enumerate(CASES, 1) if row[0].lower() in str(claim.get("subject", "")).lower()), None
    )
    if number is None:
        number = next(
            (i for i, row in enumerate(CASES, 1) if row[2] == measure), 1 if stage == "OPERATIONAL" else 2
        )
    return fixture_document(number)
