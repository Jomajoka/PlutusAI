from app.extraction.candidates import Candidate
from app.extraction.fast_path import resolve_deterministic


def make_candidate(
    context_text: str = "",
    nearest_period_text: str | None = "Q1 2024",
    value: float = 4000.0,
    line_text: str = "Revenue: $4,000",
):
    return Candidate(
        field_guess="revenue",
        keyword_matched="revenue",
        raw_value_text="$4,000",
        value=value,
        line_text=line_text,
        context_text=context_text,
        nearest_period_text=nearest_period_text,
    )


def test_resolves_known_product_and_tracked_period_without_llm():
    candidate = make_candidate(context_text="Latte", nearest_period_text="Q1 2024")
    resolved, remaining = resolve_deterministic([candidate], ["Latte", "Pastry Box"])
    assert remaining == []
    assert len(resolved) == 1
    assert resolved[0].product_name == "Latte"
    assert resolved[0].period == "Q1 2024"
    assert resolved[0].verified is True


def test_resolves_even_when_period_heading_is_far_above_in_the_document():
    # Simulates a period stated once, applying to several products listed
    # below it -- the period isn't in the local context window at all, only
    # tracked via nearest_period_text.
    candidate = make_candidate(context_text="Pastry Box", nearest_period_text="Q1 2023")
    resolved, _ = resolve_deterministic([candidate], ["Pastry Box"])
    assert resolved[0].period == "Q1 2023"


def test_falls_through_to_llm_for_a_brand_new_product():
    candidate = make_candidate(context_text="Specialty Soda", nearest_period_text="Q1 2024")
    resolved, remaining = resolve_deterministic([candidate], ["Latte", "Pastry Box"])
    assert resolved == []
    assert remaining == [candidate]


def test_falls_through_when_no_period_has_been_seen_yet():
    candidate = make_candidate(context_text="Latte", nearest_period_text=None)
    resolved, remaining = resolve_deterministic([candidate], ["Latte"])
    assert resolved == []
    assert remaining == [candidate]


def test_falls_through_with_no_known_products_at_all():
    candidate = make_candidate(context_text="Latte", nearest_period_text="Q1 2024")
    resolved, remaining = resolve_deterministic([candidate], [])
    assert resolved == []
    assert remaining == [candidate]


def test_product_match_is_case_insensitive():
    candidate = make_candidate(context_text="latte", nearest_period_text="Q1 2024")
    resolved, _ = resolve_deterministic([candidate], ["Latte"])
    assert resolved[0].product_name == "Latte"  # canonical casing from known list, not the raw line
