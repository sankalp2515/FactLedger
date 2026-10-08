import pytest
from product_core.domain.evidence import analyze, compare_quantities, finding, ledger, validate_candidate
from product_core.domain.lineage import source_families


def claim(**kwargs):
    return dict(
        id="c",
        subject="Hospital A",
        geography="District A",
        period="2026-09",
        stage="OPERATIONAL",
        measure="CAPACITY",
        value="200",
        unit="beds",
        **kwargs,
    )


def test_inauguration_does_not_prove_operation():
    c = claim()
    doc = {
        "id": "s",
        "text": "Hospital A was inaugurated.",
        "facts": [
            {
                "quote": "Hospital A was inaugurated.",
                "stage": "INAUGURATED",
                "subject": "Hospital A",
                "geography": "District A",
                "period": "2026-09",
            }
        ],
    }
    result = analyze(c, doc)
    assert result[0]["relation"] == "CONTEXT"
    assert finding(result, [])["finding"] == "INSUFFICIENT_EVIDENCE"


def test_missing_quote_cannot_be_decisive():
    assert (
        validate_candidate(
            claim(), {"id": "s", "text": "Actual text"}, {"quote": "Invented", "relation": "SUPPORTS"}
        )
        is None
    )


@pytest.mark.parametrize(
    "field,value", [("geography", "District B"), ("period", "2026-08"), ("denominator", "all households")]
)
def test_scope_mismatch_abstains(field, value):
    c = claim()
    c["denominator"] = "200 beds"
    fact = {**c, "quote": "Hospital A is operational.", "relation": "SUPPORTS"}
    fact[field] = value
    result = validate_candidate(c, {"id": "s", "text": fact["quote"]}, fact)
    assert result["relation"] == "INCOMPARABLE"


def test_decimal_money_conversion_and_measure_guard():
    a = {
        "value": "500",
        "unit": "crore",
        "currency": "INR",
        "measure": "EXPENDED",
        "period": "FY2025-26",
        "geography": "A",
    }
    b = {
        "value": "5000",
        "unit": "million",
        "currency": "INR",
        "measure": "EXPENDED",
        "period": "FY2025-26",
        "geography": "A",
    }
    assert compare_quantities(a, b)["equal"] is True
    b["measure"] = "ALLOCATED"
    assert compare_quantities(a, b)["comparable"] is False


def test_capacity_and_energy_not_compared():
    assert (
        compare_quantities({"value": "100", "unit": "MW"}, {"value": "100", "unit": "MWh"})["comparable"]
        is False
    )


def test_material_gap_downgrades_and_source_counts_do_not_vote():
    result = finding(
        [{"id": "a", "relation": "SUPPORTS"}, {"id": "b", "relation": "CONTRADICTS"}],
        [{"type": "DENOMINATOR", "material": True}],
    )
    assert result["finding"] == "INSUFFICIENT_EVIDENCE"
    assert result["opposing_ids"] == ["b"]


def test_ledger_preserves_exact_observation():
    e = {
        "id": "e",
        "claim_id": "c",
        "source_id": "s",
        "quote": "500 crore allocated.",
        "comparison": {
            "observed": {"measure": "ALLOCATED", "value": "500", "unit": "crore", "period": "FY2025-26"}
        },
    }
    result = ledger([e])
    assert result["funding"][0]["kind"] == "ALLOCATED"
    assert result["funding"][0]["evidence_ids"] == ["e"]


def test_exact_and_possible_source_dependencies_distinct():
    result = source_families(
        [
            {"id": "a", "content_hash": "same"},
            {"id": "b", "content_hash": "same"},
            {"id": "c", "content_hash": "other", "metadata": {"origin_url": "https://example.org/a"}},
        ]
    )
    assert result[0]["kind"] == "EXACT_DUPLICATE"
    assert result[0]["source_ids"] == ["a", "b"]


def test_model_cannot_promote_inauguration_by_changing_stage_mapping():
    c = claim()
    candidate = {**c, "quote": "Hospital A inaugurated with 200 beds.", "relation": "SUPPORTS"}
    e = validate_candidate(c, {"id": "s", "text": candidate["quote"]}, candidate)
    assert e["relation"] != "SUPPORTS"


def test_model_cannot_invent_a_numeric_value_inside_valid_quote():
    c = claim()
    candidate = {**c, "quote": "Hospital A operational with 20 beds.", "relation": "SUPPORTS"}
    e = validate_candidate(c, {"id": "s", "text": candidate["quote"]}, candidate)
    assert e["relation"] == "INSUFFICIENT"


def test_unknown_claim_attribution_does_not_invalidate_attributed_record():
    left = {"value": "200", "unit": "beds", "measure": "CAPACITY", "period": "2026-09"}
    right = dict(left, attribution="Hospital authority")
    result = compare_quantities(left, right)
    assert result["comparable"] is True
    assert result["operands"][1]["attribution"] == "Hospital authority"


def test_valid_operational_record_resolves_earlier_inauguration_gap():
    c = claim()
    old = {
        **c,
        "quote": "Hospital A inaugurated with 200 beds.",
        "stage": "INAUGURATED",
        "relation": "SUPPORTS",
    }
    new = {**c, "quote": "Hospital A operational with 200 beds.", "relation": "SUPPORTS"}
    evidence = [
        validate_candidate(c, {"id": "old", "text": old["quote"]}, old),
        validate_candidate(c, {"id": "new", "text": new["quote"]}, new),
    ]
    gaps = ledger(evidence)["gaps"]
    assert finding(evidence, gaps)["finding"] == "SUPPORTED_BY_COLLECTED_EVIDENCE"
    opposing = {
        **c,
        "quote": "Hospital A operational with 20 beds.",
        "value": "20",
        "relation": "CONTRADICTS",
    }
    evidence.append(validate_candidate(c, {"id": "opposing", "text": opposing["quote"]}, opposing))
    assert finding(evidence, gaps)["finding"] == "MIXED_EVIDENCE"


def test_unrecognized_measure_cannot_be_decisive_without_definition():
    c = claim()
    c.pop("stage")
    c["measure"] = "UNDEFINED_OUTCOME"
    candidate = dict(c, quote="Hospital A delivered 200 undefined outcomes.", relation="SUPPORTS")
    e = validate_candidate(c, {"id": "s", "text": candidate["quote"]}, candidate)
    assert e["relation"] == "INSUFFICIENT"


def test_pdf_quote_crossing_physical_pages_is_not_an_anchor():
    c = {"id": "c", "subject": "Hospital A"}
    text = "Hospital A\nis operational"
    document = {
        "id": "s",
        "text": text,
        "metadata": {
            "pages": [{"page": 1, "start": 0, "end": 10}, {"page": 2, "start": 11, "end": len(text)}]
        },
    }
    assert (
        validate_candidate(c, document, {"quote": text, "subject": "Hospital A", "relation": "SUPPORTS"})
        is None
    )


@pytest.mark.parametrize("period", ["2025-09-30", "2025-09", "FY2024-25"])
def test_later_operation_cannot_be_backdated_by_parroting_claim_period(period):
    c = claim()
    c["period"] = period
    candidate = {
        **c,
        "quote": "Hospital A operational with 200 beds from 2026-01-01.",
        "event_date": "2026-01-01",
        "relation": "SUPPORTS",
    }
    e = validate_candidate(c, {"id": "s", "text": candidate["quote"]}, candidate)
    assert e["relation"] == "INCOMPARABLE"
    assert "event_after_reference_period" in e["comparison"]["gaps"]


def test_unknown_current_period_does_not_create_current_operation_finding():
    c = claim()
    c["period"] = "currently"
    candidate = {**c, "quote": "Hospital A operational with 200 beds.", "relation": "SUPPORTS"}
    assert (
        validate_candidate(c, {"id": "s", "text": candidate["quote"]}, candidate)["relation"]
        == "INSUFFICIENT"
    )


def test_obvious_negation_cannot_be_labeled_support_by_model():
    c = claim()
    candidate = {**c, "quote": "Hospital A is not yet operational with 200 beds.", "relation": "SUPPORTS"}
    e = validate_candidate(c, {"id": "s", "text": candidate["quote"]}, candidate)
    assert e["relation"] == "CONTRADICTS"
