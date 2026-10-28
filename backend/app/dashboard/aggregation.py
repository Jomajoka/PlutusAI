"""Pure, deterministic aggregation of raw financial_records/products rows
into chart-ready shapes. No LLM involved -- this is plain arithmetic, and the
chart template for each shape is fixed, never chosen by a model.
"""


def build_dashboard_summary(products: list[dict], financial_records: list[dict]) -> dict:
    product_names = {p["id"]: p.get("name") or "General" for p in products}

    total_revenue = 0.0
    total_units_sold = 0.0
    total_margin = 0.0
    revenue_by_period_product: dict[tuple[str, str], float] = {}
    revenue_by_product: dict[str, float] = {}
    margin_by_product: dict[str, float] = {}

    for record in financial_records:
        product_name = product_names.get(record.get("product_id"), "General")
        period = record.get("period") or "Unknown"
        revenue = record.get("revenue") or 0.0
        units_sold = record.get("units_sold") or 0.0
        cost = (record.get("cost_breakdown") or {}).get("total_cost") or 0.0
        margin = revenue - cost

        total_revenue += revenue
        total_units_sold += units_sold
        total_margin += margin

        key = (period, product_name)
        revenue_by_period_product[key] = revenue_by_period_product.get(key, 0.0) + revenue
        revenue_by_product[product_name] = revenue_by_product.get(product_name, 0.0) + revenue
        margin_by_product[product_name] = margin_by_product.get(product_name, 0.0) + margin

    revenue_trend = [
        {"period": period, "product_name": product_name, "revenue": revenue}
        for (period, product_name), revenue in sorted(revenue_by_period_product.items())
    ]
    product_mix = [
        {"product_name": name, "revenue": revenue}
        for name, revenue in sorted(revenue_by_product.items())
    ]
    margin_rows = [
        {"product_name": name, "margin": margin}
        for name, margin in sorted(margin_by_product.items())
    ]

    return {
        "kpis": {
            "total_revenue": total_revenue,
            "total_units_sold": total_units_sold,
            "total_margin": total_margin,
        },
        "revenue_trend": revenue_trend,
        "product_mix": product_mix,
        "margin_by_product": margin_rows,
    }
