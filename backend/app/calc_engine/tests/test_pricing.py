import pytest

from app.calc_engine.pricing import simulate_price_change, simulate_sourcing_change


def test_price_increase_with_elastic_demand_hand_computed():
    # price $10->$11 (+10%), elasticity -2 -> units 100->80, hand-computed above.
    result = simulate_price_change(
        current_price=10.0, current_units_sold=100.0, cost_per_unit=4.0,
        price_change_pct=0.10, elasticity=-2.0,
    )
    assert result.new_price == pytest.approx(11.0)
    assert result.new_units_sold == pytest.approx(80.0)
    assert result.old_revenue == pytest.approx(1000.0)
    assert result.new_revenue == pytest.approx(880.0)
    assert result.old_profit == pytest.approx(600.0)
    assert result.new_profit == pytest.approx(560.0)
    assert result.delta_profit == pytest.approx(-40.0)


def test_zero_elasticity_means_units_unchanged():
    result = simulate_price_change(
        current_price=10.0, current_units_sold=100.0, cost_per_unit=4.0,
        price_change_pct=0.10, elasticity=0.0,
    )
    assert result.new_units_sold == pytest.approx(100.0)
    assert result.new_revenue == pytest.approx(1100.0)
    assert result.delta_profit == pytest.approx(100.0)


def test_price_decrease_with_elastic_demand_hand_computed():
    # price $20->$16 (-20%), elasticity -1.5 -> units 50->65, hand-computed above.
    result = simulate_price_change(
        current_price=20.0, current_units_sold=50.0, cost_per_unit=8.0,
        price_change_pct=-0.20, elasticity=-1.5,
    )
    assert result.new_price == pytest.approx(16.0)
    assert result.new_units_sold == pytest.approx(65.0)
    assert result.new_revenue == pytest.approx(1040.0)
    assert result.new_profit == pytest.approx(520.0)
    assert result.delta_profit == pytest.approx(-80.0)


def test_units_sold_never_goes_negative():
    # Doubling price with elasticity -2 would mathematically imply -100%
    # units (fully wiped out, then some) -- must clamp at zero, not go negative.
    result = simulate_price_change(
        current_price=10.0, current_units_sold=10.0, cost_per_unit=5.0,
        price_change_pct=1.0, elasticity=-2.0,
    )
    assert result.new_units_sold == 0.0
    assert result.new_revenue == 0.0
    assert result.new_profit == 0.0
    assert result.delta_profit == pytest.approx(-50.0)


def test_elasticity_used_is_echoed_back_for_transparency():
    result = simulate_price_change(
        current_price=10.0, current_units_sold=100.0, cost_per_unit=4.0,
        price_change_pct=0.10, elasticity=-1.3,
    )
    assert result.elasticity_used == -1.3


def test_sourcing_change_hand_computed():
    # price $15, units 100, cost $5->$3 -> hand-computed above.
    result = simulate_sourcing_change(
        price=15.0, units_sold=100.0, old_cost_per_unit=5.0, new_cost_per_unit=3.0,
    )
    assert result.revenue == pytest.approx(1500.0)
    assert result.old_profit == pytest.approx(1000.0)
    assert result.new_profit == pytest.approx(1200.0)
    assert result.delta_profit == pytest.approx(200.0)


def test_sourcing_change_to_more_expensive_supplier_reduces_profit():
    result = simulate_sourcing_change(
        price=15.0, units_sold=100.0, old_cost_per_unit=5.0, new_cost_per_unit=8.0,
    )
    assert result.delta_profit == pytest.approx(-300.0)


def test_sourcing_change_holds_price_and_units_constant():
    result = simulate_sourcing_change(
        price=15.0, units_sold=100.0, old_cost_per_unit=5.0, new_cost_per_unit=3.0,
    )
    assert result.units_sold == 100.0
