"""Compare a business's own computed margin % against a typical range for
its industry. The ranges are a small, hand-curated static table -- general
public knowledge, not live data -- explicitly a rough reference, not a
precise benchmark. No LLM involved here; industry classification (a separate,
closed-set LLM task, see app/classification/industry.py) happens before this
and this module only does the lookup + comparison once a category is known.
"""

from dataclasses import dataclass

# (low, high) typical gross-margin % range for the category. Deliberately
# wide bands and explicitly a rough reference -- see module docstring.
INDUSTRY_MARGIN_BENCHMARKS: dict[str, tuple[float, float]] = {
    "Retail": (20.0, 35.0),
    "Food & Beverage": (25.0, 40.0),
    "E-commerce": (35.0, 55.0),
    "Professional Services": (50.0, 70.0),
    "Healthcare & Wellness": (30.0, 50.0),
    "Manufacturing": (20.0, 35.0),
    "Construction & Trades": (15.0, 25.0),
    "Technology & Software": (60.0, 80.0),
    "Hospitality & Tourism": (20.0, 35.0),
    "Creative & Media": (40.0, 60.0),
}


@dataclass
class BenchmarkComparison:
    industry: str
    business_margin_pct: float
    benchmark_low_pct: float
    benchmark_high_pct: float
    position: str  # "below" | "within" | "above"


def compare_to_benchmark(industry: str | None, business_margin_pct: float) -> BenchmarkComparison | None:
    """Returns None if `industry` isn't a category we have a benchmark for --
    callers should skip the feature entirely in that case, not fall back to
    a generic range.
    """
    if industry not in INDUSTRY_MARGIN_BENCHMARKS:
        return None

    low, high = INDUSTRY_MARGIN_BENCHMARKS[industry]
    if business_margin_pct < low:
        position = "below"
    elif business_margin_pct > high:
        position = "above"
    else:
        position = "within"

    return BenchmarkComparison(
        industry=industry,
        business_margin_pct=business_margin_pct,
        benchmark_low_pct=low,
        benchmark_high_pct=high,
        position=position,
    )
