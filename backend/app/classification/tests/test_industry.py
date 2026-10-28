from app.classification.industry import INDUSTRY_CATEGORIES, validate_industry


def test_valid_category_passes_through():
    assert validate_industry({"industry": "Retail"}) == "Retail"


def test_every_listed_category_is_accepted():
    for category in INDUSTRY_CATEGORIES:
        assert validate_industry({"industry": category}) == category


def test_invented_category_is_rejected():
    assert validate_industry({"industry": "Space Tourism"}) is None


def test_null_is_passed_through_as_none():
    assert validate_industry({"industry": None}) is None


def test_missing_field_becomes_none():
    assert validate_industry({}) is None
