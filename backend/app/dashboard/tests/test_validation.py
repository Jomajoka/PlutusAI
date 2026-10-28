import pytest

from app.dashboard.validation import build_backtest_summary


def test_groups_records_by_product_and_backtests_each():
    products = [
        {"id": "p1", "name": "Widget", "unit_cost": 4.0},
        {"id": "p2", "name": "Gadget", "unit_cost": 2.0},
    ]
    records = [
        # Widget: history with real price variation (Q1-Q3), another real
        # price change into held-out Q4 -- something to actually backtest.
        {"product_id": "p1", "period": "Q1", "revenue": 1000.0, "units_sold": 100.0},    # price 10
        {"product_id": "p1", "period": "Q2", "revenue": 833.33, "units_sold": 69.44},    # price 12
        {"product_id": "p1", "period": "Q3", "revenue": 952.38, "units_sold": 90.70},    # price 10.5
        {"product_id": "p1", "period": "Q4", "revenue": 909.09, "units_sold": 82.64},    # price 11 (actual)
        # Gadget: no price change anywhere -- nothing to backtest.
        {"product_id": "p2", "period": "Q1", "revenue": 300.0, "units_sold": 30.0},
        {"product_id": "p2", "period": "Q2", "revenue": 300.0, "units_sold": 30.0},
    ]
    results = build_backtest_summary(products, records)
    assert len(results) == 1
    assert results[0]["product_name"] == "Widget"
    assert results[0]["held_out_period"] == "Q4"
    assert results[0]["actual_units_sold"] == 82.64
    assert results[0]["predicted_units_sold"] > 0
    assert isinstance(results[0]["error_pct"], float)
    assert results[0]["confidence"] in ("low", "medium", "high")


def test_empty_input_returns_empty_list():
    assert build_backtest_summary([], []) == []


def test_product_with_no_records_is_skipped():
    products = [{"id": "p1", "name": "Widget", "unit_cost": 4.0}]
    assert build_backtest_summary(products, []) == []
