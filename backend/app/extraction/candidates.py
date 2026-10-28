import re
from dataclasses import dataclass

from app.calc_engine.periods import parse_period
from app.extraction.keywords import FIELD_KEYWORDS

# Matches numbers like: $1,234,000  1.2M  (500)  45%  1234.56
_NUMBER_RE = re.compile(
    r"\(?\$?-?\d[\d,]*(?:\.\d+)?\)?\s*(?:million|billion|thousand|[kmb%])?",
    re.IGNORECASE,
)

_SUFFIX_MULTIPLIERS = {
    "k": 1_000,
    "thousand": 1_000,
    "m": 1_000_000,
    "million": 1_000_000,
    "b": 1_000_000_000,
    "billion": 1_000_000_000,
}

# How far past the end of a keyword match we'll look for a number on the same line.
_SEARCH_WINDOW = 60

# How many preceding non-blank lines to carry as context (e.g. a product
# heading or period label above the matched line) for the LLM to use when
# assigning product/period -- it never affects what counts as a valid match.
# 4 rather than 3 so a 3rd field under a typical 2-line (period + product)
# heading block still has both headings in view.
_CONTEXT_LINES = 4


@dataclass
class Candidate:
    field_guess: str
    keyword_matched: str
    raw_value_text: str
    value: float
    line_text: str
    context_text: str = ""
    # The most recent line before this one that parses as a real period
    # (e.g. "Q1 2024"), tracked across the WHOLE document, not just the
    # nearby context window -- a period heading is often stated once and
    # applies to several products listed below it, so a fixed lookback
    # window would miss it for the 2nd+ product under that heading. This is
    # purely syntactic (no business-specific knowledge needed), so tracking
    # it unbounded is just as safe as the local window, only less limited.
    nearest_period_text: str | None = None


def parse_number(raw: str) -> float | None:
    """Parse a matched number token into a float, handling $, commas, %,
    parenthesized negatives, and K/M/B (or million/billion/thousand) suffixes.
    Returns None if the token has no digits to parse.
    """
    text = raw.strip()
    is_negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")

    suffix_multiplier = 1
    lower = text.lower()
    for suffix, multiplier in _SUFFIX_MULTIPLIERS.items():
        if lower.endswith(suffix):
            suffix_multiplier = multiplier
            text = text[: -len(suffix)]
            lower = text.lower()
            break

    cleaned = text.replace("$", "").replace(",", "").replace("%", "").strip()
    if not cleaned or not re.search(r"\d", cleaned):
        return None

    try:
        value = float(cleaned) * suffix_multiplier
    except ValueError:
        return None

    return -value if is_negative else value


def extract_candidates(text: str) -> list[Candidate]:
    """Deterministic, LLM-free extraction: find lines containing a known
    financial keyword, then look for a number on that same line near the
    keyword. This is the ONLY place numbers get pulled from raw text —
    everything downstream (LLM structuring) works off these candidates,
    never off the raw text itself.
    """
    candidates: list[Candidate] = []
    recent_lines: list[str] = []
    current_period: str | None = None

    for line in text.splitlines():
        if not line.strip():
            continue
        stripped = line.strip()
        if parse_period(stripped) is not None:
            current_period = stripped
        lower_line = line.lower()

        for field, keywords in FIELD_KEYWORDS.items():
            # Sort longest-first so "total revenue" is tried before "revenue"
            # on the same line, and stop after the first match for this
            # field on this line (avoids double-counting one number under
            # two overlapping synonyms, e.g. "revenue" + "total revenue").
            for keyword in sorted(keywords, key=len, reverse=True):
                idx = lower_line.find(keyword)
                if idx == -1:
                    continue

                search_start = idx + len(keyword)
                window = line[search_start : search_start + _SEARCH_WINDOW]
                match = _NUMBER_RE.search(window)
                if not match:
                    continue

                value = parse_number(match.group())
                if value is None:
                    continue

                candidates.append(
                    Candidate(
                        field_guess=field,
                        keyword_matched=keyword,
                        raw_value_text=match.group().strip(),
                        value=value,
                        line_text=line.strip(),
                        context_text="\n".join(recent_lines[-_CONTEXT_LINES:]),
                        nearest_period_text=current_period,
                    )
                )
                break

        recent_lines.append(stripped)

    return candidates
