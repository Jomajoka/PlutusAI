from dataclasses import dataclass, field

from app.llm.structuring import StructuredRecord

# unit_price is a product-level attribute (products.unit_price), not a
# per-period financial_records field, so it's grouped separately.
_FINANCIAL_RECORD_FIELDS = {"revenue", "units_sold", "cost"}


@dataclass
class FinancialRow:
    product_name: str
    period: str | None
    revenue: float | None = None
    units_sold: float | None = None
    cost_breakdown: dict | None = None


def group_records(
    records: list[StructuredRecord],
) -> tuple[list[FinancialRow], dict[str, float]]:
    """Merge one-field-per-record structured output into one row per
    (product_name, period) for financial_records, plus a separate
    product_name -> unit_price map (a product-level attribute, not
    period-level).
    """
    rows_by_key: dict[tuple[str, str | None], FinancialRow] = {}
    unit_prices: dict[str, float] = {}

    for record in records:
        if record.field == "unit_price":
            unit_prices[record.product_name] = record.value
            continue

        if record.field not in _FINANCIAL_RECORD_FIELDS:
            continue

        key = (record.product_name, record.period)
        if key not in rows_by_key:
            rows_by_key[key] = FinancialRow(
                product_name=record.product_name, period=record.period
            )
        row = rows_by_key[key]

        if record.field == "revenue":
            row.revenue = record.value
        elif record.field == "units_sold":
            row.units_sold = record.value
        elif record.field == "cost":
            row.cost_breakdown = {"total_cost": record.value}

    return list(rows_by_key.values()), unit_prices
