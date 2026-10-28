"""Estimate a product's own price elasticity of demand from its historical
financial_records, rather than guessing or asking the LLM. Real statistics,
not an LLM estimate -- see Checkpoint 4 depth additions in docs/PROGRESS.md.

We don't store price per period directly (products.unit_price is a single
current value), but financial_records already has revenue and units_sold per
period, so the *implied* average price for a period is revenue/units_sold.
That's enough to fit elasticity via log-log regression across periods where
the implied price actually varied.
"""

import math
from dataclasses import dataclass

# Used when there isn't enough historical price variation to fit a real
# regression. A typical assumption for small-business products -- explicitly
# surfaced to the caller (`is_estimated=False`) rather than hidden.
DEFAULT_ELASTICITY = -1.5

# Need at least this many distinct (price, units) points to fit a line at all.
_MIN_POINTS = 3


@dataclass
class ElasticityEstimate:
    elasticity: float
    is_estimated: bool
    points_used: int


def _implied_price(record: dict) -> float | None:
    revenue = record.get("revenue")
    units = record.get("units_sold")
    if not revenue or not units:
        return None
    return revenue / units


def estimate_elasticity(financial_records: list[dict]) -> ElasticityEstimate:
    """Fit elasticity = slope of log(units) vs log(price) across a product's
    historical periods. Falls back to DEFAULT_ELASTICITY if there isn't
    enough data or price variation to fit a meaningful line.
    """
    points: list[tuple[float, float]] = []
    for record in financial_records:
        price = _implied_price(record)
        units = record.get("units_sold")
        if price is None or not units or price <= 0 or units <= 0:
            continue
        points.append((math.log(price), math.log(units)))

    distinct_prices = {round(p, 6) for p, _ in points}
    if len(points) < _MIN_POINTS or len(distinct_prices) < 2:
        return ElasticityEstimate(
            elasticity=DEFAULT_ELASTICITY, is_estimated=False, points_used=len(points)
        )

    x_vals = [p for p, _ in points]
    y_vals = [u for _, u in points]
    x_mean = sum(x_vals) / len(x_vals)
    y_mean = sum(y_vals) / len(y_vals)

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
    denominator = sum((x - x_mean) ** 2 for x in x_vals)

    if denominator == 0:
        return ElasticityEstimate(
            elasticity=DEFAULT_ELASTICITY, is_estimated=False, points_used=len(points)
        )

    slope = numerator / denominator
    return ElasticityEstimate(elasticity=slope, is_estimated=True, points_used=len(points))
