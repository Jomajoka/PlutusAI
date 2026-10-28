from app.calc_engine.periods import ParsedPeriod, parse_period, period_date_range, period_sort_key


def test_parses_quarter_and_year():
    result = parse_period("Q1 2024")
    assert result.year == 2024
    assert result.sub_period == "Q1"


def test_parses_quarter_case_insensitively():
    result = parse_period("q4 2023")
    assert result.year == 2023
    assert result.sub_period == "Q4"


def test_parses_full_month_name_and_year():
    result = parse_period("January 2024")
    assert result.year == 2024
    assert result.sub_period == "Jan"


def test_parses_abbreviated_month_and_year():
    result = parse_period("Mar 2024")
    assert result.year == 2024
    assert result.sub_period == "Mar"


def test_parses_iso_year_month():
    result = parse_period("2024-03")
    assert result.year == 2024
    assert result.sub_period == "Mar"


def test_parses_year_only_with_no_sub_period():
    result = parse_period("2024")
    assert result.year == 2024
    assert result.sub_period is None


def test_unparseable_period_returns_none():
    assert parse_period("Fiscal period A") is None
    assert parse_period("") is None
    assert parse_period(None) is None


def test_unknown_iso_month_returns_none():
    assert parse_period("2024-13") is None


def test_date_range_for_quarter_spans_its_three_months():
    start, end = period_date_range(ParsedPeriod(year=2024, sub_period="Q1"))
    assert start == "2024-01-01"
    assert end == "2024-03-31"


def test_date_range_for_single_month():
    start, end = period_date_range(ParsedPeriod(year=2024, sub_period="Feb"))
    assert start == "2024-02-01"
    assert end == "2024-02-29"  # 2024 is a leap year


def test_date_range_for_year_only_spans_whole_year():
    start, end = period_date_range(ParsedPeriod(year=2023, sub_period=None))
    assert start == "2023-01-01"
    assert end == "2023-12-31"


def test_period_sort_key_orders_chronologically_across_years():
    periods = ["Q1 2024", "Q2 2023", "Q1 2023", "Q4 2023"]
    assert sorted(periods, key=period_sort_key) == ["Q1 2023", "Q2 2023", "Q4 2023", "Q1 2024"]


def test_period_sort_key_puts_unparseable_periods_last():
    periods = ["Q1 2024", "Fiscal A"]
    assert sorted(periods, key=period_sort_key) == ["Q1 2024", "Fiscal A"]
