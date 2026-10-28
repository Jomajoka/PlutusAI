from app.scenario.parsing import validate_parsed_query


def test_valid_output_passes_through():
    result = validate_parsed_query({"lever": "price", "product_name": "Widget", "magnitude": 0.1})
    assert result.lever == "price"
    assert result.product_name == "Widget"
    assert result.magnitude == 0.1


def test_invalid_lever_becomes_none():
    result = validate_parsed_query({"lever": "discount_coupon", "product_name": "Widget", "magnitude": 0.1})
    assert result.lever is None


def test_missing_magnitude_stays_none_not_zero():
    result = validate_parsed_query({"lever": "price", "product_name": "Widget", "magnitude": None})
    assert result.magnitude is None


def test_non_numeric_magnitude_becomes_none():
    result = validate_parsed_query({"lever": "price", "product_name": "Widget", "magnitude": "a lot"})
    assert result.magnitude is None


def test_blank_product_name_becomes_none():
    result = validate_parsed_query({"lever": "price", "product_name": "   ", "magnitude": 0.1})
    assert result.product_name is None


def test_empty_llm_output_is_handled_gracefully():
    result = validate_parsed_query({})
    assert result.lever is None
    assert result.product_name is None
    assert result.magnitude is None
