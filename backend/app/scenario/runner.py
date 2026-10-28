"""Decide what to compute, deterministically. The LLM only supplies
{lever, product_name, magnitude} (Checkpoint 5 parsing step) -- this module
decides whether that calls for a single simulation or a sweep, clamps
nonsensical magnitudes, and runs the already-tested Checkpoint 4 functions.
No LLM involved here; this is the "division of labor" boundary.
"""

from dataclasses import dataclass

from app.calc_engine.elasticity import confidence_label, estimate_elasticity
from app.calc_engine.periods import period_sort_key
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


def _implied_cost_per_unit(record: dict) -> float | None:
    cost_breakdown = record.get("cost_breakdown") or {}
    total_cost = cost_breakdown.get("total_cost")
    units = record.get("units_sold")
    if not total_cost or not units:
        return None
    return total_cost / units


def _latest_baseline(product: dict, financial_records: list[dict]) -> tuple[float, float, float] | None:
    """Current (price, units_sold, cost_per_unit) baseline: prefer the most
    recent period's actuals for all three -- cost_per_unit is derived the
    same way price already is (financial_records has cost_breakdown and
    units_sold per period, but no direct per-unit figure), since
    products.unit_cost is never actually populated by ingestion (only
    unit_price is tracked at the product level). Falls back to the
    product's stored unit_cost/unit_price only if history has nothing usable.
    """
    sorted_records = sorted(
        financial_records, key=lambda r: period_sort_key(r.get("period") or ""), reverse=True
    )

    price = None
    units = None
    for record in sorted_records:
        candidate_price = _implied_price(record)
        candidate_units = record.get("units_sold")
        if candidate_price and candidate_units:
            price, units = candidate_price, candidate_units
            break

    if price is None:
        price = product.get("unit_price")
        units = 0.0
        if not price:
            return None

    cost_per_unit = None
    for record in sorted_records:
        candidate_cost = _implied_cost_per_unit(record)
        if candidate_cost is not None:
            cost_per_unit = candidate_cost
            break
    if cost_per_unit is None:
        cost_per_unit = product.get("unit_cost") or 0.0

    return price, units, cost_per_unit


@dataclass
class ScenarioOutcome:
    kind: str  # "single" | "sweep" | "needs_magnitude"
    lever: str
    elasticity_used: float | None
    is_elasticity_estimated: bool | None
    confidence: str | None = None
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
    current_price, current_units, cost_per_unit = baseline

    if lever == "price":
        estimate = estimate_elasticity(financial_records)
        if magnitude is None:
            sweep = sweep_price_change(
                current_price, current_units, cost_per_unit, estimate.elasticity,
                _DEFAULT_SWEEP_MIN, _DEFAULT_SWEEP_MAX, _DEFAULT_SWEEP_STEP,
            )
            return ScenarioOutcome(
                kind="sweep", lever=lever, elasticity_used=estimate.elasticity,
                is_elasticity_estimated=estimate.is_estimated, confidence=confidence_label(estimate),
                sweep=sweep,
            )

        clamped = clamp_magnitude(magnitude)
        single = simulate_price_change(
            current_price, current_units, cost_per_unit, clamped, estimate.elasticity
        )
        return ScenarioOutcome(
            kind="single", lever=lever, elasticity_used=estimate.elasticity,
            is_elasticity_estimated=estimate.is_estimated, confidence=confidence_label(estimate),
            single=single,
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
            kind="single", lever=lever, elasticity_used=None, is_elasticity_estimated=None,
            confidence="high", single=single,
        )

    return None
