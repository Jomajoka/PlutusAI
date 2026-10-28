"""Sweep a price change across a range and find the profit-maximizing point.
Reframes the product from "answer one question" to "recommend the best
move" -- see Checkpoint 4 depth additions in docs/PROGRESS.md. Pure Python,
built on simulate_price_change(); no LLM involved.
"""

from dataclasses import dataclass

from app.calc_engine.pricing import PriceChangeResult, simulate_price_change


@dataclass
class SweepResult:
    points: list[PriceChangeResult]
    optimum: PriceChangeResult


def sweep_price_change(
    current_price: float,
    current_units_sold: float,
    cost_per_unit: float,
    elasticity: float,
    min_pct: float = -0.5,
    max_pct: float = 0.5,
    step_pct: float = 0.05,
) -> SweepResult:
    """Simulate price changes from min_pct to max_pct (inclusive) in step_pct
    increments, and return every point plus whichever maximizes new_profit.
    """
    points: list[PriceChangeResult] = []
    pct = min_pct
    # Float-safe iteration: step by integer counts rather than repeated
    # addition, which can drift and skip/duplicate the end point.
    steps = round((max_pct - min_pct) / step_pct)
    for i in range(steps + 1):
        pct = min_pct + i * step_pct
        points.append(
            simulate_price_change(
                current_price, current_units_sold, cost_per_unit, pct, elasticity
            )
        )

    optimum = max(points, key=lambda p: p.new_profit)
    return SweepResult(points=points, optimum=optimum)
