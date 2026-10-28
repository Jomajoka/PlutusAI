import pytest

from app.calc_engine.elasticity import DEFAULT_ELASTICITY, estimate_elasticity


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
