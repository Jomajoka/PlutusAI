from app.extraction.candidates import extract_candidates, parse_number


def test_parse_number_plain():
    assert parse_number("1234") == 1234.0


def test_parse_number_with_dollar_and_commas():
    assert parse_number("$1,234,000") == 1_234_000.0


def test_parse_number_with_decimal():
    assert parse_number("1234.56") == 1234.56


def test_parse_number_million_suffix():
    assert parse_number("1.2M") == 1_200_000.0
    assert parse_number("1.2 million") == 1_200_000.0


def test_parse_number_thousand_suffix():
    assert parse_number("450K") == 450_000.0


def test_parse_number_parenthesized_negative():
    assert parse_number("(500)") == -500.0


def test_parse_number_percent():
    assert parse_number("45%") == 45.0


def test_parse_number_no_digits_returns_none():
    assert parse_number("N/A") is None


def test_extract_revenue_candidate():
    text = "Total revenue: $1,234,000 for the quarter."
    candidates = extract_candidates(text)
    revenue_candidates = [c for c in candidates if c.field_guess == "revenue"]
    assert len(revenue_candidates) == 1
    assert revenue_candidates[0].value == 1_234_000.0


def test_extract_multiple_fields_from_multiline_text():
    text = """
    Revenue: $500,000
    COGS: $200,000
    Units sold: 1,000
    Unit price: $50
    """
    candidates = extract_candidates(text)
    fields_found = {c.field_guess for c in candidates}
    assert fields_found == {"revenue", "cost", "units_sold", "unit_price"}


def test_extract_ignores_lines_without_keywords():
    text = "This quarter was great. We hired 5 new employees."
    candidates = extract_candidates(text)
    assert candidates == []


def test_extract_ignores_keyword_with_no_number_nearby():
    text = "Revenue grew significantly compared to last year."
    candidates = extract_candidates(text)
    assert candidates == []


def test_extract_handles_turnover_synonym():
    text = "Turnover for the year was $2.5 million."
    candidates = extract_candidates(text)
    assert any(c.field_guess == "revenue" and c.value == 2_500_000.0 for c in candidates)


def test_extract_captures_source_line_for_confirmation_ui():
    text = "Net sales: $75,000 driven by strong Q3 performance."
    candidates = extract_candidates(text)
    assert candidates[0].line_text == "Net sales: $75,000 driven by strong Q3 performance."


def test_nearest_period_tracked_across_whole_document_not_just_local_window():
    text = """
    Q1 2023
    Latte
    Revenue: $4,000
    Units sold: 1,000
    Cost of goods sold: $1,500

    Pastry Box
    Revenue: $5,000
    Units sold: 500
    Cost of goods sold: $2,000
    """
    candidates = extract_candidates(text)
    # Pastry Box's fields are several lines past the "Q1 2023" heading --
    # well outside the local context window -- but should still carry it.
    pastry_candidates = [c for c in candidates if "5,000" in c.line_text or "500" in c.line_text or "2,000" in c.line_text]
    assert pastry_candidates
    assert all(c.nearest_period_text == "Q1 2023" for c in pastry_candidates)


def test_nearest_period_updates_to_a_later_heading():
    text = """
    Q1 2023
    Revenue: $100

    Q2 2023
    Revenue: $200
    """
    candidates = extract_candidates(text)
    assert candidates[0].nearest_period_text == "Q1 2023"
    assert candidates[1].nearest_period_text == "Q2 2023"


def test_nearest_period_is_none_before_any_period_heading_seen():
    text = "Revenue: $100\nQ1 2023\nRevenue: $200"
    candidates = extract_candidates(text)
    assert candidates[0].nearest_period_text is None
    assert candidates[1].nearest_period_text == "Q1 2023"
