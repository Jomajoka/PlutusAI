from app.scenario.resolution import resolve_product_name


def make_products():
    return [{"id": "p1", "name": "Widget"}, {"id": "p2", "name": "Gadget"}]


def test_exact_match_case_insensitive():
    result = resolve_product_name("widget", make_products())
    assert result == {"id": "p1", "name": "Widget"}


def test_fuzzy_match_single_close_candidate():
    result = resolve_product_name("Widgets", make_products())
    assert result is not None
    assert result["name"] == "Widget"


def test_no_match_returns_none():
    result = resolve_product_name("Thingamajig", make_products())
    assert result is None


def test_ambiguous_match_returns_none_rather_than_guessing():
    products = [{"id": "p1", "name": "Widget A"}, {"id": "p2", "name": "Widget B"}]
    result = resolve_product_name("Widget", products)
    assert result is None


def test_empty_guess_returns_none():
    assert resolve_product_name(None, make_products()) is None
    assert resolve_product_name("", make_products()) is None


def test_no_known_products_returns_none():
    assert resolve_product_name("Widget", []) is None
