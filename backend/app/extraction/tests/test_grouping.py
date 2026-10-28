from app.extraction.grouping import group_records
from app.llm.structuring import StructuredRecord


def make_record(field, value, product_name="General", period="Q1 2024"):
    return StructuredRecord(
        field=field,
        value=value,
        product_name=product_name,
        period=period,
        source_line=f"{field}: {value}",
        verified=True,
    )


def test_revenue_and_units_for_same_product_period_merge_into_one_row():
    records = [
        make_record("revenue", 500_000.0),
        make_record("units_sold", 1_000.0),
    ]
    rows, unit_prices = group_records(records)
    assert len(rows) == 1
    assert rows[0].revenue == 500_000.0
    assert rows[0].units_sold == 1_000.0
    assert unit_prices == {}


def test_different_periods_produce_separate_rows():
    records = [
        make_record("revenue", 500_000.0, period="Q1 2024"),
        make_record("revenue", 600_000.0, period="Q2 2024"),
    ]
    rows, _ = group_records(records)
    assert len(rows) == 2
    periods = {r.period for r in rows}
    assert periods == {"Q1 2024", "Q2 2024"}


def test_different_products_produce_separate_rows():
    records = [
        make_record("revenue", 500_000.0, product_name="Widget"),
        make_record("revenue", 300_000.0, product_name="Gadget"),
    ]
    rows, _ = group_records(records)
    assert len(rows) == 2
    products = {r.product_name for r in rows}
    assert products == {"Widget", "Gadget"}


def test_cost_goes_into_cost_breakdown_dict():
    records = [make_record("cost", 200_000.0)]
    rows, _ = group_records(records)
    assert rows[0].cost_breakdown == {"total_cost": 200_000.0}


def test_unit_price_is_separated_from_financial_rows():
    records = [
        make_record("revenue", 500_000.0, product_name="Widget"),
        make_record("unit_price", 49.99, product_name="Widget"),
    ]
    rows, unit_prices = group_records(records)
    assert len(rows) == 1
    assert rows[0].revenue == 500_000.0
    assert unit_prices == {"Widget": 49.99}


def test_missing_fields_stay_none_not_zero():
    records = [make_record("revenue", 500_000.0)]
    rows, _ = group_records(records)
    assert rows[0].units_sold is None
    assert rows[0].cost_breakdown is None
