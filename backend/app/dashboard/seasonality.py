"""Detect recurring per-sub-period revenue patterns (e.g. "Q4 runs high") from
a product's own history. Pure statistics, no LLM -- and no pattern is forced:
a product without enough history or without more than one distinct sub-period
represented just yields no insight, rather than a guess dressed up as a trend.
"""

from app.calc_engine.periods import parse_period

# Need a reasonable number of data points, spanning more than one sub-period,
# before a "typically higher/lower" claim means anything.
_MIN_PERIODS = 4
_MIN_DISTINCT_SUB_PERIODS = 2
_DEVIATION_THRESHOLD = 0.15


def build_seasonality_summary(products: list[dict], financial_records: list[dict]) -> list[dict]:
    records_by_product: dict[str, list[dict]] = {}
    for record in financial_records:
        records_by_product.setdefault(record.get("product_id"), []).append(record)

    insights = []
    for product in products:
        records = records_by_product.get(product["id"], [])

        parsed_revenue: list[tuple[str, float]] = []
        for record in records:
            parsed = parse_period(record.get("period") or "")
            revenue = record.get("revenue")
            if parsed is None or parsed.sub_period is None or revenue is None:
                continue
            parsed_revenue.append((parsed.sub_period, revenue))

        if len(parsed_revenue) < _MIN_PERIODS:
            continue

        distinct_sub_periods = {sub for sub, _ in parsed_revenue}
        if len(distinct_sub_periods) < _MIN_DISTINCT_SUB_PERIODS:
            continue

        overall_mean = sum(revenue for _, revenue in parsed_revenue) / len(parsed_revenue)
        if overall_mean <= 0:
            continue

        by_sub_period: dict[str, list[float]] = {}
        for sub, revenue in parsed_revenue:
            by_sub_period.setdefault(sub, []).append(revenue)

        for sub, values in by_sub_period.items():
            avg = sum(values) / len(values)
            deviation_pct = (avg - overall_mean) / overall_mean
            if abs(deviation_pct) >= _DEVIATION_THRESHOLD:
                insights.append(
                    {
                        "product_name": product.get("name") or "General",
                        "sub_period": sub,
                        "deviation_pct": deviation_pct,
                        "periods_used": len(values),
                    }
                )

    insights.sort(key=lambda row: abs(row["deviation_pct"]), reverse=True)
    return insights
