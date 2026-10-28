"""LLM narrates an already-computed result. It gets a small summary dict,
never the raw sweep array, and is told to keep the "simplified estimate"
framing visible -- per the proof-of-concept accuracy bar in docs/PROGRESS.md.
This is the last step; nothing downstream depends on its output being
well-formed, so unlike structuring there's no validation gate -- a narration
failure just means no narration, not bad data.
"""

import json

from app.llm.client import complete_json

_SYSTEM_PROMPT = """You explain the result of a business what-if simulation \
to a small business owner, in 2-3 plain sentences. You are given only the \
already-computed numbers -- never invent or adjust any of them. Mention \
that this is a simplified estimate (e.g. based on a constant elasticity \
assumption), not a guarantee. If a "confidence" field is given ("low", \
"medium", or "high"), reflect it honestly in your wording -- e.g. for "low" \
say the business doesn't have enough price history yet to estimate this \
well, for "high" you can speak a bit more confidently about the direction \
of the result. Never claim more certainty than the confidence field \
supports. Respond with strict JSON: {"narration": "<text>"}
"""


def build_narration_messages(summary: dict) -> list[dict]:
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(summary)},
    ]


def narrate_scenario(summary: dict, models: list[str] | None = None) -> str | None:
    try:
        messages = build_narration_messages(summary)
        llm_output = complete_json(messages, models=models)
        narration = llm_output.get("narration")
        return narration if isinstance(narration, str) and narration.strip() else None
    except Exception:
        return None
