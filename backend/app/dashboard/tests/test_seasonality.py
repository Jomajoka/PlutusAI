from app.dashboard.seasonality import build_seasonality_summary


def make_products():
    return [{"id": "p1", "name": "Widget"}]


def test_flags_a_consistently_strong_quarter():
    records = [
        {"product_id": "p1", "period": "Q1 2023", "revenue": 100.0},
        {"product_id": "p1", "period": "Q2 2023", "revenue": 100.0},
        {"product_id": "p1", "period": "Q3 2023", "revenue": 100.0},
        {"product_id": "p1", "period": "Q4 2023", "revenue": 200.0},
        {"product_id": "p1", "period": "Q1 2024", "revenue": 100.0},
        {"product_id": "p1", "period": "Q4 2024", "revenue": 200.0},
    ]
    results = build_seasonality_summary(make_products(), records)
    q4 = next(r for r in results if r["sub_period"] == "Q4")
    assert q4["product_name"] == "Widget"
    assert q4["deviation_pct"] > 0.15
    assert q4["periods_used"] == 2


def test_no_insight_with_too_few_periods():
    records = [
        {"product_id": "p1", "period": "Q1 2023", "revenue": 100.0},
        {"product_id": "p1", "period": "Q4 2023", "revenue": 200.0},
    ]
    assert build_seasonality_summary(make_products(), records) == []


def test_no_insight_with_only_one_distinct_sub_period():
    records = [
        {"product_id": "p1", "period": "Q1 2021", "revenue": 100.0},
        {"product_id": "p1", "period": "Q1 2022", "revenue": 110.0},
        {"product_id": "p1", "period": "Q1 2023", "revenue": 90.0},
        {"product_id": "p1", "period": "Q1 2024", "revenue": 105.0},
    ]
    assert build_seasonality_summary(make_products(), records) == []


def test_unparseable_periods_are_ignored_not_guessed():
    records = [
        {"product_id": "p1", "period": "Fiscal A", "revenue": 999.0},
        {"product_id": "p1", "period": "Q1 2023", "revenue": 100.0},
        {"product_id": "p1", "period": "Q2 2023", "revenue": 100.0},
        {"product_id": "p1", "period": "Q4 2023", "revenue": 200.0},
        {"product_id": "p1", "period": "Q4 2024", "revenue": 200.0},
    ]
    results = build_seasonality_summary(make_products(), records)
    assert all(r["periods_used"] <= 2 for r in results)


def test_no_flagged_sub_period_when_deviation_is_small():
    records = [
        {"product_id": "p1", "period": "Q1 2023", "revenue": 100.0},
        {"product_id": "p1", "period": "Q2 2023", "revenue": 102.0},
        {"product_id": "p1", "period": "Q1 2024", "revenue": 98.0},
        {"product_id": "p1", "period": "Q2 2024", "revenue": 100.0},
    ]
    assert build_seasonality_summary(make_products(), records) == []
