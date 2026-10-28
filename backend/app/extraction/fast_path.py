"""Resolve the unambiguous common case -- a candidate whose context clearly
names BOTH an already-known product and a parseable period -- without
involving the LLM at all. This is a direct extension of the project's
deterministic-first extraction philosophy: it only ever uses exact matches
against real data (an existing product name, a real period format), never a
guess, so there's no new risk of a wrong value. Anything it can't confidently
resolve (a brand-new product, an unparseable period, a genuine ambiguity)
falls through to the LLM structuring step, which remains the safety net --
this only shrinks what gets sent there, it never replaces it.
"""

from app.extraction.candidates import Candidate
from app.llm.structuring import StructuredRecord


def _find_known_product(context_lines: list[str], known_product_names: list[str]) -> str | None:
    lookup = {name.strip().lower(): name for name in known_product_names if name}
    # Closest preceding line wins -- reversed() checks nearest-to-farthest.
    # Deliberately local (not tracked document-wide like the period is):
    # products are typically re-headed before every block of their own
    # fields, so a stale "last known product from way earlier" would be a
    # real misattribution risk in a multi-product document, unlike a period
    # heading which legitimately applies to everything below it.
    for line in reversed(context_lines):
        match = lookup.get(line.strip().lower())
        if match:
            return match
    return None


def resolve_deterministic(
    candidates: list[Candidate], known_product_names: list[str]
) -> tuple[list[StructuredRecord], list[Candidate]]:
    resolved: list[StructuredRecord] = []
    remaining: list[Candidate] = []

    for candidate in candidates:
        context_lines = [line for line in candidate.context_text.split("\n") if line.strip()]
        product_name = _find_known_product(context_lines, known_product_names)
        period = candidate.nearest_period_text

        if product_name is not None and period is not None:
            resolved.append(
                StructuredRecord(
                    field=candidate.field_guess,
                    value=candidate.value,
                    product_name=product_name,
                    period=period,
                    source_line=candidate.line_text,
                    verified=True,
                )
            )
        else:
            remaining.append(candidate)

    return resolved, remaining
