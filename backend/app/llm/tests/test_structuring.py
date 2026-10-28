from app.extraction.candidates import Candidate
from app.llm.structuring import validate_structured_output


def make_candidate(field_guess="revenue", value=1_234_000.0, line="Revenue: $1,234,000"):
    return Candidate(
        field_guess=field_guess,
        keyword_matched="revenue",
        raw_value_text="$1,234,000",
        value=value,
        line_text=line,
    )


def test_matching_record_is_verified():
    candidates = [make_candidate()]
    llm_output = {
        "records": [
            {
                "field": "revenue",
                "value": 1_234_000.0,
                "product_name": "Widget",
                "period": "Q1 2024",
                "source_line": "Revenue: $1,234,000",
            }
        ]
    }
    result = validate_structured_output(candidates, llm_output)
    assert len(result.records) == 1
    assert result.records[0].verified is True
    assert result.records[0].product_name == "Widget"


def test_record_with_altered_value_is_rejected_as_unverified():
    """The core guarantee: if the LLM returns a number that doesn't match any
    deterministically-extracted candidate (e.g. it 'corrected' or invented a
    value), it must NOT be silently trusted."""
    candidates = [make_candidate(value=1_234_000.0)]
    llm_output = {
        "records": [
            {
                "field": "revenue",
                "value": 9_999_999.0,  # does not match the real candidate
                "product_name": "Widget",
                "period": "Q1 2024",
                "source_line": "Revenue: $1,234,000",
            }
        ]
    }
    result = validate_structured_output(candidates, llm_output)
    assert result.records == []
    assert len(result.unverified_records) == 1


def test_record_with_mismatched_source_line_is_rejected():
    candidates = [make_candidate()]
    llm_output = {
        "records": [
            {
                "field": "revenue",
                "value": 1_234_000.0,
                "product_name": "Widget",
                "period": "Q1 2024",
                "source_line": "This line was never extracted",
            }
        ]
    }
    result = validate_structured_output(candidates, llm_output)
    assert result.records == []
    assert len(result.unverified_records) == 1


def test_record_missing_required_field_is_skipped_entirely():
    candidates = [make_candidate()]
    llm_output = {"records": [{"field": "revenue"}]}  # no value, no source_line
    result = validate_structured_output(candidates, llm_output)
    assert result.records == []
    assert result.unverified_records == []


def test_missing_product_name_defaults_to_general():
    candidates = [make_candidate()]
    llm_output = {
        "records": [
            {
                "field": "revenue",
                "value": 1_234_000.0,
                "period": "Q1 2024",
                "source_line": "Revenue: $1,234,000",
            }
        ]
    }
    result = validate_structured_output(candidates, llm_output)
    assert result.records[0].product_name == "General"


def test_notes_are_passed_through_separately_from_records():
    llm_output = {
        "records": [],
        "notes": [{"category": "competitor", "text": "Competitor X launched a cheaper product."}],
    }
    result = validate_structured_output([], llm_output)
    assert result.records == []
    assert result.notes == [
        {"category": "competitor", "text": "Competitor X launched a cheaper product."}
    ]


def test_note_without_text_is_ignored():
    llm_output = {"records": [], "notes": [{"category": "competitor"}]}
    result = validate_structured_output([], llm_output)
    assert result.notes == []


def test_floating_point_rounding_still_matches():
    """LLM might echo a value with slightly different float formatting --
    this must still count as a match, not a rejection."""
    candidates = [make_candidate(value=1234000.0)]
    llm_output = {
        "records": [
            {
                "field": "revenue",
                "value": 1234000.0000001,
                "product_name": "Widget",
                "period": "Q1 2024",
                "source_line": "Revenue: $1,234,000",
            }
        ]
    }
    result = validate_structured_output(candidates, llm_output)
    assert len(result.records) == 1
