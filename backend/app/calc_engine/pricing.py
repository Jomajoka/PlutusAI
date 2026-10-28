"""Pure, deterministic what-if simulations. No LLM involved -- these are the
functions the LLM will later call with parsed parameters (Checkpoint 5), but
the math itself is plain Python, unit-tested against hand-computed fixtures.

Naive/simplified by design (proof-of-concept accuracy bar, not production-
grade): assumes a constant per-unit cost and a single elasticity value,
rather than modeling real-world demand curves. Assumptions are surfaced to
the caller explicitly (e.g. `elasticity_used`), never hidden.
"""

from dataclasses import dataclass


@dataclass
class PriceChangeResult:
    old_price: float
    new_price: float
    old_units_sold: float
    new_units_sold: float
    old_revenue: float
    new_revenue: float
    old_profit: float
    new_profit: float
    delta_profit: float
    elasticity_used: float


def simulate_price_change(
    current_price: float,
    current_units_sold: float,
    cost_per_unit: float,
    price_change_pct: float,
    elasticity: float,
) -> PriceChangeResult:
    """Simulate the effect of changing price by `price_change_pct` (e.g. 0.10
    for +10%, -0.10 for -10%), using a constant-elasticity demand response:
    %change in units = elasticity * %change in price. `elasticity` is
    typically negative (demand falls as price rises).
    """
    new_price = current_price * (1 + price_change_pct)
    new_units_sold = current_units_sold * (1 + elasticity * price_change_pct)
    new_units_sold = max(new_units_sold, 0.0)

    old_revenue = current_price * current_units_sold
    new_revenue = new_price * new_units_sold
    old_profit = old_revenue - cost_per_unit * current_units_sold
    new_profit = new_revenue - cost_per_unit * new_units_sold

    return PriceChangeResult(
        old_price=current_price,
        new_price=new_price,
        old_units_sold=current_units_sold,
        new_units_sold=new_units_sold,
        old_revenue=old_revenue,
        new_revenue=new_revenue,
        old_profit=old_profit,
        new_profit=new_profit,
        delta_profit=new_profit - old_profit,
        elasticity_used=elasticity,
    )


@dataclass
class SourcingChangeResult:
    old_cost_per_unit: float
    new_cost_per_unit: float
    units_sold: float
    revenue: float
    old_profit: float
    new_profit: float
    delta_profit: float


def simulate_sourcing_change(
    price: float,
    units_sold: float,
    old_cost_per_unit: float,
    new_cost_per_unit: float,
) -> SourcingChangeResult:
    """Simulate switching supplier/sourcing (a pure cost change). Price and
    units sold are held constant -- a sourcing change isn't assumed to shift
    demand on its own, only cost. Combine with simulate_price_change if a
    price change is also being considered.
    """
    revenue = price * units_sold
    old_profit = revenue - old_cost_per_unit * units_sold
    new_profit = revenue - new_cost_per_unit * units_sold

    return SourcingChangeResult(
        old_cost_per_unit=old_cost_per_unit,
        new_cost_per_unit=new_cost_per_unit,
        units_sold=units_sold,
        revenue=revenue,
        old_profit=old_profit,
        new_profit=new_profit,
        delta_profit=new_profit - old_profit,
    )
