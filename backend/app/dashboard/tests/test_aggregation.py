from app.dashboard.aggregation import build_dashboard_summary


def make_products():
    return [
        {"id": "p1", "name": "Widget"},
        {"id": "p2", "name": "Gadget"},
    ]


def test_kpis_sum_across_all_records():
    products = make_products()
    records = [
        {"product_id": "p1", "period": "Q1", "revenue": 500.0, "units_sold": 10.0, "cost_breakdown": {"total_cost": 200.0}},
        {"product_id": "p2", "period": "Q1", "revenue": 300.0, "units_sold": 5.0, "cost_breakdown": {"total_cost": 100.0}},
    ]
    result = build_dashboard_summary(products, records)
    assert result["kpis"] == {
        "total_revenue": 800.0,
        "total_units_sold": 15.0,
        "total_margin": 500.0,
    }


def test_revenue_trend_grouped_by_period_and_product():
    products = make_products()
    records = [
        {"product_id": "p1", "period": "Q1", "revenue": 500.0},
        {"product_id": "p1", "period": "Q2", "revenue": 600.0},
        {"product_id": "p2", "period": "Q1", "revenue": 300.0},
    ]
    result = build_dashboard_summary(products, records)
    assert result["revenue_trend"] == [
        {"period": "Q1", "product_name": "Gadget", "revenue": 300.0},
        {"period": "Q1", "product_name": "Widget", "revenue": 500.0},
        {"period": "Q2", "product_name": "Widget", "revenue": 600.0},
    ]


def test_revenue_trend_is_sorted_chronologically_not_lexically_across_years():
    # A plain string sort would put "Q1 2024" before "Q2 2023" (groups by
    # quarter digit first), scrambling a multi-year trend -- regression
    # test for that bug.
    products = [{"id": "p1", "name": "Widget"}]
    records = [
        {"product_id": "p1", "period": "Q2 2023", "revenue": 100.0},
        {"product_id": "p1", "period": "Q1 2024", "revenue": 200.0},
        {"product_id": "p1", "period": "Q1 2023", "revenue": 50.0},
    ]
    result = build_dashboard_summary(products, records)
    periods_in_order = [row["period"] for row in result["revenue_trend"]]
    assert periods_in_order == ["Q1 2023", "Q2 2023", "Q1 2024"]


def test_product_mix_sums_revenue_across_periods():
    products = make_products()
    records = [
        {"product_id": "p1", "period": "Q1", "revenue": 500.0},
        {"product_id": "p1", "period": "Q2", "revenue": 100.0},
    ]
    result = build_dashboard_summary(products, records)
    assert result["product_mix"] == [{"product_name": "Widget", "revenue": 600.0}]


def test_margin_is_revenue_minus_cost_and_can_be_negative():
    products = make_products()
    records = [
        {"product_id": "p1", "period": "Q1", "revenue": 500.0, "cost_breakdown": {"total_cost": 800.0}},
    ]
    result = build_dashboard_summary(products, records)
    assert result["margin_by_product"] == [{"product_name": "Widget", "margin": -300.0}]


def test_missing_optional_fields_default_to_zero_not_error():
    products = make_products()
    records = [{"product_id": "p1", "period": "Q1"}]
    result = build_dashboard_summary(products, records)
    assert result["kpis"]["total_revenue"] == 0.0
    assert result["kpis"]["total_margin"] == 0.0


def test_missing_period_groups_under_unknown():
    products = make_products()
    records = [{"product_id": "p1", "revenue": 100.0}]
    result = build_dashboard_summary(products, records)
    assert result["revenue_trend"] == [{"period": "Unknown", "product_name": "Widget", "revenue": 100.0}]


def test_unknown_product_id_falls_back_to_general():
    records = [{"product_id": "does-not-exist", "period": "Q1", "revenue": 50.0}]
    result = build_dashboard_summary([], records)
    assert result["product_mix"] == [{"product_name": "General", "revenue": 50.0}]


def test_no_records_returns_empty_aggregates():
    result = build_dashboard_summary(make_products(), [])
    assert result["kpis"] == {"total_revenue": 0.0, "total_units_sold": 0.0, "total_margin": 0.0}
    assert result["revenue_trend"] == []
    assert result["product_mix"] == []
    assert result["margin_by_product"] == []
