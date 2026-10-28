import json
import re

import httpx

from app.config import settings

_TIMEOUT_SECONDS = 30


class LLMUnavailableError(Exception):
    """Raised when every model in the fallback chain failed."""


def _strip_code_fence(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text


def complete_json(messages: list[dict], models: list[str] | None = None) -> dict:
    """Call OpenRouter with a fallback chain of free models, returning parsed
    JSON. Tries each model in order; moves to the next on any failure
    (network error, non-2xx, or unparseable JSON). Raises LLMUnavailableError
    only if every model in the chain fails.
    """
    model_chain = models or settings.llm_structuring_models
    if not model_chain:
        raise LLMUnavailableError("No LLM models configured")

    last_error: Exception | None = None

    for model in model_chain:
        try:
            with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
                resp = client.post(
                    settings.llm_base_url,
                    headers={
                        "Authorization": f"Bearer {settings.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "response_format": {"type": "json_object"},
                    },
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                return json.loads(_strip_code_fence(content))
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
            last_error = exc
            continue

    raise LLMUnavailableError(
        f"All models in fallback chain failed: {model_chain}"
    ) from last_error
