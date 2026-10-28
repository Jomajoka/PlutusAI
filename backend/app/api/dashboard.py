from fastapi import APIRouter, Depends, HTTPException
from httpx import HTTPStatusError

from app.api.deps import get_user_token
from app.dashboard.aggregation import build_dashboard_summary
from app.db import supabase_rest

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(business_id: str, token: str = Depends(get_user_token)):
    try:
        products = await supabase_rest.list_rows(
            "products", token, filters={"business_id": f"eq.{business_id}"}
        )
        if not products:
            return build_dashboard_summary([], [])

        product_ids = ",".join(p["id"] for p in products)
        financial_records = await supabase_rest.list_rows(
            "financial_records", token, filters={"product_id": f"in.({product_ids})"}
        )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    return build_dashboard_summary(products, financial_records)
