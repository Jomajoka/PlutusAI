import json
from dataclasses import dataclass, field

from app.extraction.candidates import Candidate
from app.llm.client import complete_json

_SYSTEM_PROMPT = """You are a data structuring assistant. You will be given a \
list of (field, value, source_line, context_lines) candidates that were \
ALREADY extracted deterministically from a business document -- you did not \
find these numbers and must not invent, adjust, or add any new ones.

Your only job: for each candidate, decide which product it belongs to (using \
the provided list of known product names, or "General" if none fit or none \
were given) and which reporting period it belongs to (e.g. "Q1 2024"). Use \
context_lines (the lines immediately preceding source_line in the original \
document, such as a product heading or period label) to make this \
assignment -- do not default to "General"/omit the period just because the \
number itself doesn't contain a product or period name. If a candidate \
clearly isn't a real financial figure (e.g. a page number, a year by \
itself), omit it. When you echo source_line back, copy it EXACTLY as given \
-- never copy from context_lines instead.

You may also note anything in the document that seems relevant but doesn't \
fit (e.g. mentions of competitors or market context) in a separate "notes" \
list -- do not put these in "records".

Respond with strict JSON only, in this exact shape:
{
  "records": [
    {"field": "revenue", "value": 1234000.0, "product_name": "General", "period": "Q1 2024", "source_line": "<copy the exact source_line from the candidate>"}
  ],
  "notes": [
    {"category": "competitor", "text": "<short note>"}
  ]
}
"""


@dataclass
class StructuredRecord:
    field: str
    value: float
    product_name: str
    period: str | None
    source_line: str
    verified: bool


@dataclass
class StructuringResult:
    records: list[StructuredRecord] = field(default_factory=list)
    unverified_records: list[StructuredRecord] = field(default_factory=list)
    notes: list[dict] = field(default_factory=list)


def build_messages(candidates: list[Candidate], known_product_names: list[str]) -> list[dict]:
    candidate_payload = [
        {
            "field": c.field_guess,
            "value": c.value,
            "source_line": c.line_text,
            "context_lines": c.context_text,
        }
        for c in candidates
    ]
    user_payload = {
        "known_product_names": known_product_names,
        "candidates": candidate_payload,
    }
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload)},
    ]


def _matches_a_candidate(record: dict, candidates: list[Candidate]) -> bool:
    """Deterministic validation: a structured record is only trusted if its
    field+value+source_line match one of the original deterministically-
    extracted candidates. This is what stops the LLM from silently inventing
    or altering a number during the structuring step.
    """
    for c in candidates:
        if (
            record.get("field") == c.field_guess
            and record.get("source_line") == c.line_text
            and _values_close(record.get("value"), c.value)
        ):
            return True
    return False


def _values_close(a, b, rel_tol: float = 1e-6) -> bool:
    try:
        return abs(float(a) - float(b)) <= rel_tol * max(abs(float(b)), 1.0)
    except (TypeError, ValueError):
        return False


def validate_structured_output(
    candidates: list[Candidate], llm_output: dict
) -> StructuringResult:
    """Pure, network-free validation of an LLM structuring response against
    the original candidates. Split out from structure_candidates() so it can
    be unit tested with mocked LLM output.
    """
    result = StructuringResult()

    for raw_record in llm_output.get("records", []):
        try:
            record = StructuredRecord(
                field=raw_record["field"],
                value=float(raw_record["value"]),
                product_name=raw_record.get("product_name") or "General",
                period=raw_record.get("period"),
                source_line=raw_record.get("source_line", ""),
                verified=_matches_a_candidate(raw_record, candidates),
            )
        except (KeyError, TypeError, ValueError):
            continue

        if record.verified:
            result.records.append(record)
        else:
            result.unverified_records.append(record)

    for raw_note in llm_output.get("notes", []):
        if isinstance(raw_note, dict) and raw_note.get("text"):
            result.notes.append(
                {"category": raw_note.get("category"), "text": raw_note["text"]}
            )

    return result


def structure_candidates(
    candidates: list[Candidate],
    known_product_names: list[str],
    models: list[str] | None = None,
) -> StructuringResult:
    messages = build_messages(candidates, known_product_names)
    llm_output = complete_json(messages, models=models)
    return validate_structured_output(candidates, llm_output)
