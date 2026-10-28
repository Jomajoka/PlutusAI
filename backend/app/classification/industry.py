"""Classify a business into one of a fixed, closed set of industry
categories, from its name and product names. Deliberately a closed-set
classification task, not open generation -- the LLM can only pick a label
from `INDUSTRY_CATEGORIES` (or decline), it can never invent a category that
doesn't exist. Used to look up a static benchmark-margin range (see
app/dashboard/benchmarks.py); if the LLM can't confidently classify, the
caller skips the benchmark feature entirely rather than guessing.
"""

import json

from app.llm.client import complete_json

INDUSTRY_CATEGORIES = [
    "Retail",
    "Food & Beverage",
    "E-commerce",
    "Professional Services",
    "Healthcare & Wellness",
    "Manufacturing",
    "Construction & Trades",
    "Technology & Software",
    "Hospitality & Tourism",
    "Creative & Media",
]

_SYSTEM_PROMPT = f"""You classify a small business into an industry category \
from its name and the products/services it sells. You must pick EXACTLY one \
of these categories, copied verbatim, or null if none clearly fits or you \
are not confident:
{json.dumps(INDUSTRY_CATEGORIES)}

Never invent a category that isn't in this list. If genuinely unsure, \
respond with null rather than guessing. Respond with strict JSON: \
{{"industry": "<one of the categories above, or null>"}}
"""


def build_messages(business_name: str, product_names: list[str]) -> list[dict]:
    user_payload = {"business_name": business_name, "product_names": product_names}
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload)},
    ]


def validate_industry(llm_output: dict) -> str | None:
    industry = llm_output.get("industry")
    return industry if industry in INDUSTRY_CATEGORIES else None


def classify_industry(
    business_name: str, product_names: list[str], models: list[str] | None = None
) -> str | None:
    try:
        messages = build_messages(business_name, product_names)
        llm_output = complete_json(messages, models=models)
        return validate_industry(llm_output)
    except Exception:
        return None
