"""Group raw financial_records by product and run the Checkpoint 4 backtest
for each one -- deterministic model-accuracy check, no LLM involved. Mirrors
aggregation.py's role: pure grouping/shaping, the actual math lives in
app/calc_engine.
"""

from app.calc_engine.backtest import backtest
from app.calc_engine.elasticity import confidence_label, estimate_elasticity
from app.calc_engine.periods import parse_period, period_date_range
from app.external.fred import fetch_cpi_change_pct


def _inflation_pct_over_window(previous_period: str, held_out_period: str) -> float | None:
    """General CPI inflation spanning from the start of `previous_period` to
    the end of `held_out_period` -- supplementary context only, so any
    failure (unparseable periods, FRED unavailable) just means no context,
    never an error.
    """
    previous_parsed = parse_period(previous_period)
    held_out_parsed = parse_period(held_out_period)
    if previous_parsed is None or held_out_parsed is None:
        return None

    start, _ = period_date_range(previous_parsed)
    _, end = period_date_range(held_out_parsed)
    return fetch_cpi_change_pct(start, end)


def build_backtest_summary(products: list[dict], financial_records: list[dict]) -> list[dict]:
    records_by_product: dict[str, list[dict]] = {}
    for record in financial_records:
        product_id = record.get("product_id")
        records_by_product.setdefault(product_id, []).append(record)

    results = []
    for product in products:
        records = sorted(
            records_by_product.get(product["id"], []), key=lambda r: r.get("period") or ""
        )
        result = backtest(records, product.get("unit_cost") or 0.0)
        if result is None:
            continue

        # Confidence of the *held-out* prediction is judged from only the
        # history available at prediction time (everything before the held-
        # out period), same as what backtest() itself used internally.
        confidence = confidence_label(estimate_elasticity(records[:-1]))
        previous_period = records[-2].get("period") or ""
        inflation_pct = _inflation_pct_over_window(previous_period, result.held_out_period)

        results.append(
            {
                "product_name": product.get("name") or "General",
                "held_out_period": result.held_out_period,
                "predicted_units_sold": result.predicted_units_sold,
                "actual_units_sold": result.actual_units_sold,
                "predicted_revenue": result.predicted_revenue,
                "actual_revenue": result.actual_revenue,
                "error_pct": result.error_pct,
                "is_elasticity_estimated": result.is_elasticity_estimated,
                "confidence": confidence,
                "inflation_pct": inflation_pct,
            }
        )

    return results
