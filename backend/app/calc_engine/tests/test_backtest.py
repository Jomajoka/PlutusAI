import pytest

from app.calc_engine.backtest import backtest


def test_backtest_exact_match_when_held_out_follows_the_same_power_law():
    # First 3 periods are the same perfect power-law fixture as the
    # elasticity test (exact elasticity -2). Held-out period 4 follows the
    # same law (price 5->6, pct +0.2), so the prediction should match exactly.
    records = [
        {"period": "P1", "revenue": 1000.0, "units_sold": 100.0},  # price 10
        {"period": "P2", "revenue": 500.0, "units_sold": 25.0},    # price 20
        {"period": "P3", "revenue": 2000.0, "units_sold": 400.0},  # price 5
        {"period": "P4", "revenue": 1440.0, "units_sold": 240.0},  # price 6
    ]
    result = backtest(records, cost_per_unit=2.0)
    assert result is not None
    assert result.held_out_period == "P4"
    assert result.is_elasticity_estimated is True
    assert result.elasticity_used == pytest.approx(-2.0, abs=1e-6)
    assert result.predicted_units_sold == pytest.approx(240.0, abs=1e-6)
    assert result.actual_units_sold == 240.0
    assert result.predicted_revenue == pytest.approx(1440.0, abs=1e-6)
    assert result.error_pct == pytest.approx(0.0, abs=1e-6)


def test_backtest_falls_back_to_default_elasticity_with_thin_history():
    records = [
        {"period": "P1", "revenue": 1000.0, "units_sold": 100.0},  # price 10
        {"period": "P2", "revenue": 780.0, "units_sold": 65.0},    # price 12
    ]
    result = backtest(records, cost_per_unit=2.0)
    assert result is not None
    assert result.is_elasticity_estimated is False
    assert result.predicted_units_sold == pytest.approx(70.0, abs=1e-6)
    assert result.error_pct == pytest.approx((70.0 - 65.0) / 65.0, abs=1e-6)


def test_backtest_returns_none_with_fewer_than_two_periods():
    assert backtest([{"period": "P1", "revenue": 1000.0, "units_sold": 100.0}], cost_per_unit=2.0) is None
    assert backtest([], cost_per_unit=2.0) is None


def test_backtest_returns_none_when_no_real_price_change():
    records = [
        {"period": "P1", "revenue": 1000.0, "units_sold": 100.0},  # price 10
        {"period": "P2", "revenue": 1100.0, "units_sold": 110.0},  # price still 10
    ]
    assert backtest(records, cost_per_unit=2.0) is None
