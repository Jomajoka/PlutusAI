"""Back-test the calc engine against a product's own real history: hold out
the latest period, estimate elasticity from everything before it, predict
what should have happened given the real price change into that period, and
compare to what actually happened. Genuine model validation, not an LLM
claim -- see Checkpoint 4 depth additions in docs/PROGRESS.md.
"""

from dataclasses import dataclass

from app.calc_engine.elasticity import estimate_elasticity
from app.calc_engine.pricing import simulate_price_change


@dataclass
class BacktestResult:
    held_out_period: str
    elasticity_used: float
    is_elasticity_estimated: bool
    predicted_units_sold: float
    actual_units_sold: float
    predicted_revenue: float
    actual_revenue: float
    error_pct: float


def _implied_price(record: dict) -> float | None:
    revenue = record.get("revenue")
    units = record.get("units_sold")
    if not revenue or not units:
        return None
    return revenue / units


def backtest(financial_records: list[dict], cost_per_unit: float) -> BacktestResult | None:
    """financial_records must be sorted oldest-to-newest by period. Returns
    None if there isn't a real price change between the second-to-last and
    the held-out (latest) period -- nothing to validate against.
    """
    if len(financial_records) < 2:
        return None

    *history, held_out = financial_records
    previous = history[-1]

    previous_price = _implied_price(previous)
    held_out_price = _implied_price(held_out)
    previous_units = previous.get("units_sold")
    held_out_units = held_out.get("units_sold")
    held_out_revenue = held_out.get("revenue")

    if not previous_price or not held_out_price or not previous_units or not held_out_units:
        return None
    if previous_price == held_out_price:
        return None  # no real price change to validate a prediction against

    price_change_pct = (held_out_price - previous_price) / previous_price
    estimate = estimate_elasticity(history)

    prediction = simulate_price_change(
        current_price=previous_price,
        current_units_sold=previous_units,
        cost_per_unit=cost_per_unit,
        price_change_pct=price_change_pct,
        elasticity=estimate.elasticity,
    )

    error_pct = (
        (prediction.new_units_sold - held_out_units) / held_out_units
        if held_out_units
        else 0.0
    )

    return BacktestResult(
        held_out_period=held_out.get("period") or "Unknown",
        elasticity_used=estimate.elasticity,
        is_elasticity_estimated=estimate.is_estimated,
        predicted_units_sold=prediction.new_units_sold,
        actual_units_sold=held_out_units,
        predicted_revenue=prediction.new_revenue,
        actual_revenue=held_out_revenue or 0.0,
        error_pct=error_pct,
    )
