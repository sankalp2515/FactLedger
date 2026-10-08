import pytest
from product_core.domain.evidence import analyze
from product_core.investigation.fixtures import CASES, fixture_document


@pytest.mark.parametrize("number", range(1, 10))
def test_announcement_approval_capacity_counts_never_prove_delivery(number):
    subject, stage, measure, value, unit, *_ = CASES[number - 1]
    claim = {
        "id": "c",
        "subject": subject,
        "geography": "District A",
        "period": "2026-09",
        "stage": stage,
        "measure": measure,
        "value": value,
        "unit": unit,
        "attribution": "Synthetic public authority",
    }
    if number == 2:
        claim["currency"] = "INR"
    if number == 3:
        claim["denominator"] = "entire 80 km corridor"
    document = fixture_document(number)
    evidence = analyze(claim, {"id": "s", "text": document.text, "facts": document.metadata["facts"]})
    assert evidence
    assert evidence[0]["relation"] not in {"SUPPORTS", "CONTRADICTS"}


def test_new_operating_record_supports_only_its_matching_period():
    document = fixture_document(10)
    claim = {
        "id": "c",
        "subject": "Hospital J",
        "geography": "District A",
        "period": "2026-09",
        "stage": "OPERATIONAL",
        "measure": "CAPACITY",
        "value": "200",
        "unit": "beds",
        "attribution": "Synthetic public authority",
    }
    current = analyze(claim, {"id": "s", "text": document.text, "facts": document.metadata["facts"]})
    assert current[0]["relation"] == "SUPPORTS"
    claim["period"] = "2026-08"
    old = analyze(claim, {"id": "s", "text": document.text, "facts": document.metadata["facts"]})
    assert old[0]["relation"] == "INCOMPARABLE"
