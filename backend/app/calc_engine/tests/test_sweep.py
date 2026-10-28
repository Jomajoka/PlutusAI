import pytest

from app.calc_engine.sweep import sweep_price_change


def test_sweep_covers_full_range_at_given_step():
    result = sweep_price_change(
        current_price=10.0, current_units_sold=100.0, cost_per_unit=4.0,
        elasticity=-1.0, min_pct=-0.5, max_pct=0.5, step_pct=0.05,
    )
    assert len(result.points) == 21
    assert result.points[0].new_price == pytest.approx(5.0)   # -50%
    assert result.points[-1].new_price == pytest.approx(15.0)  # +50%


def test_sweep_finds_the_hand_computed_optimum():
    # profit(pct) = 600 + 400*pct - 1000*pct^2 for this setup (elasticity -1)
    # -> maximized at pct=0.2, profit=640, hand-derived above.
    result = sweep_price_change(
        current_price=10.0, current_units_sold=100.0, cost_per_unit=4.0,
        elasticity=-1.0, min_pct=-0.5, max_pct=0.5, step_pct=0.05,
    )
    optimum_pct = (result.optimum.new_price - 10.0) / 10.0
    assert optimum_pct == pytest.approx(0.2, abs=1e-6)
    assert result.optimum.new_profit == pytest.approx(640.0, abs=1e-6)


def test_optimum_is_the_best_point_among_all_points():
    result = sweep_price_change(
        current_price=10.0, current_units_sold=100.0, cost_per_unit=4.0,
        elasticity=-1.0,
    )
    assert all(p.new_profit <= result.optimum.new_profit for p in result.points)
    assert result.optimum in result.points
