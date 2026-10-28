import io

from fpdf import FPDF

from app.extraction.pdf import extract_pages_text, score_page, select_relevant_pages


def _make_pdf_bytes(pages_text: list[str]) -> bytes:
    pdf = FPDF()
    for text in pages_text:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 10, text)
    return bytes(pdf.output())


def test_score_page_rewards_keyword_and_number_density():
    financial = "Total revenue: $1,234,000. Units sold: 5,000."
    irrelevant = "This page intentionally left blank for formatting purposes."
    assert score_page(financial) > score_page(irrelevant)


def test_score_page_zero_for_text_with_no_keywords_or_numbers():
    assert score_page("No financial content on this page at all.") == 0


def test_select_relevant_pages_returns_all_if_under_limit():
    pages = ["revenue: $100", "irrelevant filler text"]
    assert select_relevant_pages(pages, max_pages=5) == pages


def test_select_relevant_pages_keeps_top_scoring_pages():
    pages = [
        "Table of contents, nothing financial here.",
        "Total revenue: $1,234,000. Units sold: 5,000. Cost of goods sold: $400,000.",
        "Appendix: legal disclaimers and boilerplate.",
    ]
    selected = select_relevant_pages(pages, max_pages=1)
    assert selected == [pages[1]]


def test_select_relevant_pages_preserves_original_document_order():
    pages = [
        "Revenue: $100,000 for Q1.",
        "Irrelevant filler page.",
        "Revenue: $200,000 for Q2.",
    ]
    selected = select_relevant_pages(pages, max_pages=2)
    # Both financial pages should be kept, in original order (0 before 2),
    # not re-ordered by score.
    assert selected == [pages[0], pages[2]]


def test_extract_pages_text_reads_a_real_pdf():
    pdf_bytes = _make_pdf_bytes(
        ["Total revenue: 1234000 dollars for Q1 2024.", "Second page content."]
    )
    pages = extract_pages_text(pdf_bytes)
    assert len(pages) == 2
    assert "revenue" in pages[0].lower()
    assert "1234000" in pages[0]
    assert "second page" in pages[1].lower()
