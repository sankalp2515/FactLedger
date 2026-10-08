import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("score", Path(__file__).parents[1] / "score.py")
score_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score_module)
score = score_module.score


def test_wrong_decisive_and_abstention_reported_separately():
    result = score(
        [
            {"id": "a", "label": "SUPPORTS", "prediction": "SUPPORTS"},
            {"id": "b", "label": "CONTEXT", "prediction": "SUPPORTS"},
            {"id": "c", "label": "CONTRADICTS", "prediction": "INSUFFICIENT"},
        ]
    )
    assert result["decisive_precision"] == 0.5
    assert result["decisive_coverage"] == 2 / 3
    assert result["abstention_rate"] == 1 / 3
    assert result["correct_decisive"] == 1


def test_empty_and_no_decisive_never_claim_perfect_precision():
    assert score([])["decisive_precision"] is None
    assert score([{"id": "a", "label": "CONTEXT", "prediction": "CONTEXT"}])["decisive_precision"] is None


def test_missing_prediction_and_invalid_label_fail():
    import pytest

    with pytest.raises(ValueError):
        score([{"id": "a", "label": "SUPPORTS"}])
    with pytest.raises(ValueError):
        score([{"id": "a", "label": "TRUE", "prediction": "SUPPORTS"}])


def test_duplicate_pair_rejected():
    import pytest

    with pytest.raises(ValueError):
        score([{"id": "a", "label": "SUPPORTS", "prediction": "SUPPORTS"}] * 2)
