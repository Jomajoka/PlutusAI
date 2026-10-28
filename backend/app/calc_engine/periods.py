"""Parse the free-text `period` strings our schema stores (e.g. "Q1 2024",
"January 2024", "2024-01", "2024") into a normalized (year, sub_period) pair.

Deterministic, no LLM. `period` is stored as plain text (see minimal-schema
decisions in docs/PROGRESS.md) rather than a structured date, since different
businesses report on different cadences -- this is the one place that
structure gets reconstructed, and only when it parses cleanly. A period that
doesn't match a known shape returns None rather than guessing, so callers
(seasonality, inflation context) can simply skip it instead of building on a
wrong guess.
"""

import calendar
import re
from dataclasses import dataclass

_MONTHS = {
    "jan": "Jan", "january": "Jan",
    "feb": "Feb", "february": "Feb",
    "mar": "Mar", "march": "Mar",
    "apr": "Apr", "april": "Apr",
    "may": "May",
    "jun": "Jun", "june": "Jun",
    "jul": "Jul", "july": "Jul",
    "aug": "Aug", "august": "Aug",
    "sep": "Sep", "sept": "Sep", "september": "Sep",
    "oct": "Oct", "october": "Oct",
    "nov": "Nov", "november": "Nov",
    "dec": "Dec", "december": "Dec",
}

_QUARTER_RE = re.compile(r"^q([1-4])\s+(\d{4})$")
_ISO_YEAR_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")
_MONTH_YEAR_RE = re.compile(r"^([a-zA-Z]+)\s+(\d{4})$")
_YEAR_ONLY_RE = re.compile(r"^(\d{4})$")

_ISO_MONTH_TO_LABEL = {
    "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
    "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
    "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
}


_MONTH_NUM = {label: i + 1 for i, label in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
)}
_QUARTER_MONTHS = {"Q1": (1, 3), "Q2": (4, 6), "Q3": (7, 9), "Q4": (10, 12)}


@dataclass
class ParsedPeriod:
    year: int
    sub_period: str | None  # e.g. "Q1", "Mar", or None for a year-only period


def parse_period(period: str) -> ParsedPeriod | None:
    text = (period or "").strip().lower()
    if not text:
        return None

    match = _QUARTER_RE.match(text)
    if match:
        return ParsedPeriod(year=int(match.group(2)), sub_period=f"Q{match.group(1)}")

    match = _ISO_YEAR_MONTH_RE.match(text)
    if match:
        label = _ISO_MONTH_TO_LABEL.get(match.group(2))
        return ParsedPeriod(year=int(match.group(1)), sub_period=label) if label else None

    match = _MONTH_YEAR_RE.match(text)
    if match:
        label = _MONTHS.get(match.group(1))
        return ParsedPeriod(year=int(match.group(2)), sub_period=label) if label else None

    match = _YEAR_ONLY_RE.match(text)
    if match:
        return ParsedPeriod(year=int(match.group(1)), sub_period=None)

    return None


def period_date_range(parsed: ParsedPeriod) -> tuple[str, str]:
    """The (start_date, end_date) ISO range a period covers, used to query a
    date-indexed external series (e.g. FRED's monthly CPI) for the same
    window. For a quarter/year this spans multiple months -- an
    approximation by construction, since our schema doesn't store exact
    dates, only loose period labels.
    """
    year = parsed.year
    if parsed.sub_period is None:
        start_month, end_month = 1, 12
    elif parsed.sub_period in _QUARTER_MONTHS:
        start_month, end_month = _QUARTER_MONTHS[parsed.sub_period]
    else:
        start_month = end_month = _MONTH_NUM[parsed.sub_period]

    end_day = calendar.monthrange(year, end_month)[1]
    return f"{year:04d}-{start_month:02d}-01", f"{year:04d}-{end_month:02d}-{end_day:02d}"


def period_sort_key(period: str) -> tuple:
    """Chronological sort key for a period string -- NOT a plain string
    sort. "Q1 2024" < "Q2 2023" as text would group by quarter digit first
    and year second, scrambling any multi-year sequence (this exact bug has
    hit both the dashboard trend chart and a scenario's "latest period"
    lookup -- one shared helper now, instead of three copies drifting).
    Periods that don't parse sort after every real one, by their own text,
    rather than crashing or guessing a date for them.
    """
    parsed = parse_period(period)
    if parsed is None:
        return (1, period or "")
    start, _ = period_date_range(parsed)
    return (0, start)
