"""LLM parses a natural-language what-if question into structured params
ONLY -- {lever, product_name, magnitude}. It never picks a chart, never
computes a result, and never resolves product_name itself (see
resolution.py). This is the narrowest, safest thing we can ask it to do.
"""

from dataclasses import dataclass

from app.llm.client import complete_json

_SYSTEM_PROMPT = """You are a query-parsing assistant for a business \
what-if tool. Parse the user's question into strict JSON, in this exact \
shape:
{"lever": "price" | "sourcing" | null, "product_name": "<string or null>", "magnitude": <float or null>}

Rules:
- "lever" is "price" for questions about changing a selling price, "sourcing" \
for questions about changing suppliers/cost, or null if neither applies.
- "product_name" should be copied from the user's question, matched as \
closely as possible to one of the known product names given to you -- but \
do NOT invent a product name that isn't implied by the question.
- "magnitude" is the signed fractional change implied (e.g. "increase by \
10%" -> 0.10, "20% cheaper" -> -0.20). If the user gave no specific amount \
(e.g. just "increase the price"), set magnitude to null -- do not guess a \
number.
- Never compute any result, chart, or recommendation. Only parse.
"""


@dataclass
class ParsedScenarioQuery:
    lever: str | None
    product_name: str | None
    magnitude: float | None


def build_messages(query: str, known_product_names: list[str]) -> list[dict]:
    import json

    user_payload = {"known_product_names": known_product_names, "question": query}
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload)},
    ]


def validate_parsed_query(llm_output: dict) -> ParsedScenarioQuery:
    lever = llm_output.get("lever")
    if lever not in ("price", "sourcing"):
        lever = None

    product_name = llm_output.get("product_name")
    if not isinstance(product_name, str) or not product_name.strip():
        product_name = None

    magnitude = llm_output.get("magnitude")
    if not isinstance(magnitude, (int, float)):
        magnitude = None

    return ParsedScenarioQuery(lever=lever, product_name=product_name, magnitude=magnitude)


def parse_scenario_query(
    query: str, known_product_names: list[str], models: list[str] | None = None
) -> ParsedScenarioQuery:
    messages = build_messages(query, known_product_names)
    llm_output = complete_json(messages, models=models)
    return validate_parsed_query(llm_output)
