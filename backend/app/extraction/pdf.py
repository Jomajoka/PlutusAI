import io
import re

from pypdf import PdfReader

from app.extraction.keywords import FIELD_KEYWORDS

_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def extract_pages_text(pdf_bytes: bytes) -> list[str]:
    """Extract raw text per page. No LLM involved -- just PDF parsing."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return [page.extract_text() or "" for page in reader.pages]


def score_page(text: str) -> float:
    """Deterministic relevance score for a page of text: rewards pages with
    financial keywords (from the same FIELD_KEYWORDS used for extraction) and
    numbers near them. Used to shortlist pages out of a long report before
    anything is sent to the LLM.
    """
    lower = text.lower()
    keyword_hits = sum(
        1
        for keywords in FIELD_KEYWORDS.values()
        for keyword in keywords
        if keyword in lower
    )
    number_hits = len(_NUMBER_RE.findall(text))
    return keyword_hits * 2 + number_hits * 0.5


def select_relevant_pages(pages: list[str], max_pages: int = 15) -> list[str]:
    """Pick the highest-scoring pages, but return them in original document
    order so periods/context still read naturally when concatenated.
    """
    if len(pages) <= max_pages:
        return pages

    ranked_indices = sorted(
        range(len(pages)), key=lambda i: score_page(pages[i]), reverse=True
    )
    top_indices = sorted(ranked_indices[:max_pages])
    return [pages[i] for i in top_indices]
