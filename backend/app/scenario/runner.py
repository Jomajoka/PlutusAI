"""Decide what to compute, deterministically. The LLM only supplies
{lever, product_name, magnitude} (Checkpoint 5 parsing step) -- this module
decides whether that calls for a single simulation or a sweep, clamps
nonsensical magnitudes, and runs the already-tested Checkpoint 4 functions.
No LLM involved here; this is the "division of labor" boundary.
"""

from dataclasses import dataclass

from app.calc_engine.elasticity import estimate_elasticity
from app.calc_engine.pricing import PriceChangeResult, SourcingChangeResult, simulate_price_change, simulate_sourcing_change
from app.calc_engine.sweep import SweepResult, sweep_price_change

# A price change outside this range isn't a sane what-if (e.g. -500%, which
# implies negative price) -- clamp rather than let it blow up downstream.
_MIN_MAGNITUDE = -0.95
_MAX_MAGNITUDE = 5.0

_DEFAULT_SWEEP_MIN = -0.3
_DEFAULT_SWEEP_MAX = 0.3
_DEFAULT_SWEEP_STEP = 0.05


def clamp_magnitude(magnitude: float) -> float:
    return max(_MIN_MAGNITUDE, min(_MAX_MAGNITUDE, magnitude))


def _implied_price(record: dict) -> float | None:
    revenue = record.get("revenue")
    units = record.get("units_sold")
    if not revenue or not units:
        return None
    return revenue / units


def _latest_baseline(product: dict, financial_records: list[dict]) -> tuple[float, float] | None:
    """Current (price, units_sold) baseline: prefer the most recent period's
    actuals, falling back to the product's stored unit_price if no history
    has both revenue and units_sold.
    """
    for record in sorted(financial_records, key=lambda r: r.get("period") or "", reverse=True):
        price = _implied_price(record)
        units = record.get("units_sold")
        if price and units:
            return price, units

    price = product.get("unit_price")
    return (price, 0.0) if price else None


@dataclass
class ScenarioOutcome:
    kind: str  # "single" | "sweep" | "needs_magnitude"
    lever: str
    elasticity_used: float | None
    is_elasticity_estimated: bool | None
    single: PriceChangeResult | SourcingChangeResult | None = None
    sweep: SweepResult | None = None
    message: str | None = None


def run_scenario(
    lever: str,
    magnitude: float | None,
    product: dict,
    financial_records: list[dict],
) -> ScenarioOutcome | None:
    """Returns None if there isn't enough data (no price/units baseline) to
    simulate anything for this product.
    """
    baseline = _latest_baseline(product, financial_records)
    if baseline is None:
        return None
    current_price, current_units = baseline
    cost_per_unit = product.get("unit_cost") or 0.0

    if lever == "price":
        estimate = estimate_elasticity(financial_records)
        if magnitude is None:
            sweep = sweep_price_change(
                current_price, current_units, cost_per_unit, estimate.elasticity,
                _DEFAULT_SWEEP_MIN, _DEFAULT_SWEEP_MAX, _DEFAULT_SWEEP_STEP,
            )
            return ScenarioOutcome(
                kind="sweep", lever=lever, elasticity_used=estimate.elasticity,
                is_elasticity_estimated=estimate.is_estimated, sweep=sweep,
            )

        clamped = clamp_magnitude(magnitude)
        single = simulate_price_change(
            current_price, current_units, cost_per_unit, clamped, estimate.elasticity
        )
        return ScenarioOutcome(
            kind="single", lever=lever, elasticity_used=estimate.elasticity,
            is_elasticity_estimated=estimate.is_estimated, single=single,
        )

    if lever == "sourcing":
        if magnitude is None:
            return ScenarioOutcome(
                kind="needs_magnitude", lever=lever, elasticity_used=None, is_elasticity_estimated=None,
                message="How much cheaper or more expensive is the new sourcing option? (e.g. '20% cheaper')",
            )
        clamped = clamp_magnitude(magnitude)
        new_cost = cost_per_unit * (1 + clamped)
        single = simulate_sourcing_change(current_price, current_units, cost_per_unit, new_cost)
        return ScenarioOutcome(
            kind="single", lever=lever, elasticity_used=None, is_elasticity_estimated=None, single=single
        )

    return None
