import pytest

from app.calc_engine.elasticity import DEFAULT_ELASTICITY, ElasticityEstimate, confidence_label, estimate_elasticity


def test_perfect_power_law_recovers_exact_elasticity():
    # Constructed so Q = 100 * (P/10)^-2 exactly -- implied prices 10, 20, 5.
    records = [
        {"revenue": 1000.0, "units_sold": 100.0},  # price 10
        {"revenue": 500.0, "units_sold": 25.0},    # price 20
        {"revenue": 2000.0, "units_sold": 400.0},  # price 5
    ]
    result = estimate_elasticity(records)
    assert result.is_estimated is True
    assert result.points_used == 3
    assert result.elasticity == pytest.approx(-2.0, abs=1e-6)
    assert result.r_squared == pytest.approx(1.0, abs=1e-6)


def test_confidence_label_high_for_good_fit_with_enough_points():
    records = [
        {"revenue": 1000.0, "units_sold": 100.0},
        {"revenue": 500.0, "units_sold": 25.0},
        {"revenue": 2000.0, "units_sold": 400.0},
        {"revenue": 1500.0, "units_sold": 56.25},
    ]
    result = estimate_elasticity(records)
    assert confidence_label(result) == "high"


def test_confidence_label_medium_for_estimated_but_few_points():
    result = ElasticityEstimate(elasticity=-1.8, is_estimated=True, points_used=3, r_squared=0.95)
    assert confidence_label(result) == "medium"


def test_positive_slope_falls_back_to_default_instead_of_a_backwards_prediction():
    # Regression test: units_sold varying mostly due to seasonality at a
    # near-constant price, plus one real price increase, can confound the
    # regression into a positive slope -- which would mean "raising price
    # increases demand," backwards for a normal good. Must fall back rather
    # than hand back a confidently-wrong, backwards prediction.
    records = [
        {"revenue": 4000.0, "units_sold": 1000.0},  # price 4.0
        {"revenue": 4000.0, "units_sold": 1000.0},  # price 4.0
        {"revenue": 5600.0, "units_sold": 1400.0},  # price 4.0, seasonal spike
        {"revenue": 4000.0, "units_sold": 1000.0},  # price 4.0
        {"revenue": 6300.0, "units_sold": 1400.0},  # price 4.5, the one real change
    ]
    result = estimate_elasticity(records)
    assert result.is_estimated is False
    assert result.elasticity == DEFAULT_ELASTICITY


def test_confidence_label_low_when_not_estimated():
    result = ElasticityEstimate(elasticity=DEFAULT_ELASTICITY, is_estimated=False, points_used=1, r_squared=None)
    assert confidence_label(result) == "low"


def test_falls_back_to_default_with_too_few_points():
    records = [{"revenue": 1000.0, "units_sold": 100.0}]
    result = estimate_elasticity(records)
    assert result.is_estimated is False
    assert result.elasticity == DEFAULT_ELASTICITY


def test_falls_back_to_default_with_no_price_variation():
    # Same implied price every period -- nothing to regress against.
    records = [
        {"revenue": 1000.0, "units_sold": 100.0},
        {"revenue": 1000.0, "units_sold": 100.0},
        {"revenue": 1000.0, "units_sold": 100.0},
    ]
    result = estimate_elasticity(records)
    assert result.is_estimated is False
    assert result.elasticity == DEFAULT_ELASTICITY


def test_ignores_records_missing_revenue_or_units():
    records = [
        {"revenue": 1000.0, "units_sold": 100.0},
        {"revenue": None, "units_sold": 50.0},
        {"revenue": 500.0, "units_sold": None},
        {"revenue": 500.0, "units_sold": 25.0},
        {"revenue": 2000.0, "units_sold": 400.0},
    ]
    result = estimate_elasticity(records)
    assert result.points_used == 3
    assert result.is_estimated is True


def test_empty_history_falls_back_to_default():
    result = estimate_elasticity([])
    assert result.is_estimated is False
    assert result.elasticity == DEFAULT_ELASTICITY
