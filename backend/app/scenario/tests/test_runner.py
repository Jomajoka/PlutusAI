import pytest

from app.scenario.runner import clamp_magnitude, run_scenario


def test_clamp_magnitude_rejects_nonsensical_negative():
    assert clamp_magnitude(-5.0) == -0.95


def test_clamp_magnitude_rejects_absurd_positive():
    assert clamp_magnitude(10.0) == 5.0


def test_clamp_magnitude_leaves_sane_values_alone():
    assert clamp_magnitude(0.1) == 0.1


def make_product(unit_cost=4.0, unit_price=10.0):
    return {"id": "p1", "name": "Widget", "unit_cost": unit_cost, "unit_price": unit_price}


def test_price_lever_with_magnitude_runs_single_simulation():
    records = [{"period": "Q1", "revenue": 1000.0, "units_sold": 100.0}]
    outcome = run_scenario("price", 0.1, make_product(), records)
    assert outcome.kind == "single"
    assert outcome.is_elasticity_estimated is False  # only 1 period -> fallback
    assert outcome.confidence == "low"
    assert outcome.single.new_price == pytest.approx(11.0)


def test_price_lever_without_magnitude_runs_sweep():
    records = [{"period": "Q1", "revenue": 1000.0, "units_sold": 100.0}]
    outcome = run_scenario("price", None, make_product(), records)
    assert outcome.kind == "sweep"
    assert len(outcome.sweep.points) == 13  # -0.3 to 0.3 step 0.05
    assert outcome.sweep.optimum is not None


def test_sourcing_lever_without_magnitude_asks_for_clarification():
    records = [{"period": "Q1", "revenue": 1000.0, "units_sold": 100.0}]
    outcome = run_scenario("sourcing", None, make_product(), records)
    assert outcome.kind == "needs_magnitude"
    assert outcome.message is not None


def test_sourcing_lever_with_magnitude_hand_computed():
    records = [{"period": "Q1", "revenue": 1000.0, "units_sold": 100.0}]
    # 20% cheaper sourcing: cost 4 -> 3.2, hand-computed delta_profit +80.
    outcome = run_scenario("sourcing", -0.2, make_product(), records)
    assert outcome.kind == "single"
    assert outcome.confidence == "high"
    assert outcome.single.new_cost_per_unit == pytest.approx(3.2)
    assert outcome.single.delta_profit == pytest.approx(80.0)


def test_magnitude_is_clamped_before_use():
    records = [{"period": "Q1", "revenue": 1000.0, "units_sold": 100.0}]
    outcome = run_scenario("sourcing", -5.0, make_product(), records)
    assert outcome.single.new_cost_per_unit == pytest.approx(4.0 * (1 - 0.95))


def test_falls_back_to_product_unit_price_when_no_usable_history():
    records = [{"period": "Q1"}]  # missing revenue/units_sold
    outcome = run_scenario("price", 0.1, make_product(unit_price=20.0), records)
    assert outcome.kind == "single"
    assert outcome.single.old_price == 20.0
    assert outcome.single.old_units_sold == 0.0


def test_no_usable_baseline_at_all_returns_none():
    outcome = run_scenario("price", 0.1, make_product(unit_price=None), [])
    assert outcome is None


def test_unknown_lever_returns_none():
    records = [{"period": "Q1", "revenue": 1000.0, "units_sold": 100.0}]
    assert run_scenario("discount_coupon", 0.1, make_product(), records) is None


def test_derives_cost_from_financial_records_when_product_unit_cost_is_null():
    # Regression test: products.unit_cost is never actually populated by the
    # ingestion pipeline (only unit_price is tracked at the product level,
    # see app/extraction/grouping.py) -- cost lived only in cost_breakdown
    # per financial record. Before the fix, cost_per_unit silently fell back
    # to 0.0 here, making every sourcing/price scenario ignore cost entirely.
    product = {"id": "p1", "name": "Latte", "unit_cost": None, "unit_price": None}
    records = [
        {"period": "Q4 2024", "revenue": 6300.0, "units_sold": 1400.0, "cost_breakdown": {"total_cost": 2100.0}},
    ]
    outcome = run_scenario("sourcing", -0.2, product, records)
    assert outcome.single.old_cost_per_unit == pytest.approx(1.5)  # 2100 / 1400
    assert outcome.single.new_cost_per_unit == pytest.approx(1.2)
    assert outcome.single.delta_profit > 0  # cheaper sourcing must increase profit


def test_latest_baseline_picks_true_latest_period_not_lexically_latest():
    # Regression test: a plain string sort of periods would put "Q1 2024"
    # ahead of "Q2 2023" (groups by quarter digit first, year second),
    # picking the wrong period as "latest" for a multi-year product.
    product = {"id": "p1", "name": "Latte", "unit_cost": None, "unit_price": None}
    records = [
        {"period": "Q1 2024", "revenue": 100.0, "units_sold": 10.0},  # price 10, truly latest
        {"period": "Q2 2023", "revenue": 200.0, "units_sold": 10.0},  # price 20, lexically "latest"
    ]
    outcome = run_scenario("price", 0.0, product, records)
    assert outcome.single.old_price == pytest.approx(10.0)
