from fastapi import APIRouter, Depends, HTTPException
from httpx import HTTPStatusError
from pydantic import BaseModel

from app.api.deps import get_user_token
from app.db import supabase_rest
from app.llm.client import LLMUnavailableError
from app.scenario.narration import narrate_scenario
from app.scenario.parsing import parse_scenario_query
from app.scenario.resolution import resolve_product_name
from app.scenario.runner import run_scenario

router = APIRouter(prefix="/scenario", tags=["scenario"])


class ScenarioRequest(BaseModel):
    business_id: str
    query: str


@router.post("/query")
async def scenario_query(body: ScenarioRequest, token: str = Depends(get_user_token)):
    try:
        products = await supabase_rest.list_rows(
            "products", token, filters={"business_id": f"eq.{body.business_id}"}
        )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    if not products:
        return {"status": "needs_clarification", "message": "This business has no products yet."}

    known_names = [p.get("name") or "" for p in products]
    try:
        parsed = parse_scenario_query(body.query, known_names)
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if parsed.lever is None:
        return {
            "status": "needs_clarification",
            "message": (
                "I can only simulate price changes or sourcing/cost changes right now "
                "(e.g. \"raise the price of Widget by 10%\" or \"what if my supplier cost "
                "for Widget drops 15%\"). I can't directly simulate a change in units sold, "
                "since that's an outcome of a price or cost change, not something you set "
                "directly."
            ),
        }

    product = resolve_product_name(parsed.product_name, products)
    if product is None:
        return {
            "status": "needs_clarification",
            "message": f"Which product did you mean? Options: {', '.join(known_names)}",
        }

    try:
        financial_records = await supabase_rest.list_rows(
            "financial_records", token, filters={"product_id": f"eq.{product['id']}"}
        )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    outcome = run_scenario(parsed.lever, parsed.magnitude, product, financial_records)
    if outcome is None:
        return {
            "status": "needs_clarification",
            "message": f"Not enough saved data for {product.get('name')} to simulate this yet.",
        }

    if outcome.kind == "needs_magnitude":
        return {"status": "needs_clarification", "message": outcome.message}

    if outcome.kind == "single":
        s = outcome.single
        summary = {
            "product_name": product.get("name"),
            "lever": outcome.lever,
            "old_profit": s.old_profit if hasattr(s, "old_profit") else None,
            "new_profit": s.new_profit,
            "delta_profit": s.delta_profit,
            "elasticity_used": outcome.elasticity_used,
            "is_elasticity_estimated": outcome.is_elasticity_estimated,
            "confidence": outcome.confidence,
        }
        narration = narrate_scenario(summary)
        return {
            "status": "ok",
            "kind": "single",
            "lever": outcome.lever,
            "product_name": product.get("name"),
            "result": vars(s),
            "elasticity_used": outcome.elasticity_used,
            "is_elasticity_estimated": outcome.is_elasticity_estimated,
            "confidence": outcome.confidence,
            "narration": narration,
        }

    # kind == "sweep"
    points = [vars(p) for p in outcome.sweep.points]
    optimum = vars(outcome.sweep.optimum)
    summary = {
        "product_name": product.get("name"),
        "lever": outcome.lever,
        "optimum": optimum,
        "elasticity_used": outcome.elasticity_used,
        "is_elasticity_estimated": outcome.is_elasticity_estimated,
        "confidence": outcome.confidence,
    }
    narration = narrate_scenario(summary)
    return {
        "status": "ok",
        "kind": "sweep",
        "lever": outcome.lever,
        "product_name": product.get("name"),
        "points": points,
        "optimum": optimum,
        "elasticity_used": outcome.elasticity_used,
        "is_elasticity_estimated": outcome.is_elasticity_estimated,
        "confidence": outcome.confidence,
        "narration": narration,
    }
