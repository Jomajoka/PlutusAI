# Canonical schema field -> synonym keywords to look for in raw text.
# Deterministic-first extraction: these are what we match on BEFORE any LLM
# involvement. The LLM later only maps already-matched candidates to a field
# and product/period — it never reads free text to find numbers itself.

FIELD_KEYWORDS: dict[str, list[str]] = {
    "revenue": [
        "revenue",
        "net revenue",
        "total revenue",
        "sales",
        "net sales",
        "turnover",
    ],
    "cost": [
        "cost of goods sold",
        "cogs",
        "cost of sales",
        "direct costs",
        "unit cost",
        "cost per unit",
    ],
    "units_sold": [
        "units sold",
        "units",
        "quantity sold",
        "orders",
        "volume sold",
    ],
    "unit_price": [
        "unit price",
        "price per unit",
        "selling price",
        "average price",
    ],
}
