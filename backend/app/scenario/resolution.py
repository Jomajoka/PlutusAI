"""Resolve the LLM's product-name guess against the business's real products.
Deterministic -- exact match, then fuzzy match. The LLM is given the real
product list as grounding context, but matching it is never the LLM's job:
if nothing or more than one thing matches well enough, we ask the user to
clarify rather than guess.
"""

from difflib import SequenceMatcher

_FUZZY_CUTOFF = 0.6
# How much clearer the best match must be than the runner-up to trust it
# over asking the user to clarify.
_MIN_LEAD = 0.15


def resolve_product_name(guess: str | None, known_products: list[dict]) -> dict | None:
    """Returns the matched product dict, or None if there's no confident,
    unambiguous match (caller should treat None as "ask the user to clarify").
    """
    if not guess or not known_products:
        return None

    for product in known_products:
        if (product.get("name") or "").lower() == guess.lower():
            return product

    scored = sorted(
        (
            (SequenceMatcher(None, guess.lower(), (p.get("name") or "").lower()).ratio(), p)
            for p in known_products
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )
    candidates = [pair for pair in scored if pair[0] >= _FUZZY_CUTOFF]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0][1]

    best_score, best_product = candidates[0]
    runner_up_score = candidates[1][0]
    if best_score - runner_up_score >= _MIN_LEAD:
        return best_product
    return None  # too close to call -- ask the user to clarify
