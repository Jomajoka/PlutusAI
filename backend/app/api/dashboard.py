from fastapi import APIRouter, Depends, HTTPException
from httpx import HTTPStatusError

from app.api.deps import get_user_token
from app.classification.industry import classify_industry
from app.dashboard.aggregation import build_dashboard_summary
from app.dashboard.benchmarks import compare_to_benchmark
from app.dashboard.seasonality import build_seasonality_summary
from app.dashboard.validation import build_backtest_summary
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


@router.get("/backtest")
async def dashboard_backtest(business_id: str, token: str = Depends(get_user_token)):
    try:
        products = await supabase_rest.list_rows(
            "products", token, filters={"business_id": f"eq.{business_id}"}
        )
        if not products:
            return []

        product_ids = ",".join(p["id"] for p in products)
        financial_records = await supabase_rest.list_rows(
            "financial_records", token, filters={"product_id": f"in.({product_ids})"}
        )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    return build_backtest_summary(products, financial_records)


@router.get("/seasonality")
async def dashboard_seasonality(business_id: str, token: str = Depends(get_user_token)):
    try:
        products = await supabase_rest.list_rows(
            "products", token, filters={"business_id": f"eq.{business_id}"}
        )
        if not products:
            return []

        product_ids = ",".join(p["id"] for p in products)
        financial_records = await supabase_rest.list_rows(
            "financial_records", token, filters={"product_id": f"in.({product_ids})"}
        )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    return build_seasonality_summary(products, financial_records)


@router.get("/benchmark")
async def dashboard_benchmark(business_id: str, token: str = Depends(get_user_token)):
    try:
        businesses = await supabase_rest.list_rows(
            "businesses", token, filters={"id": f"eq.{business_id}"}
        )
        if not businesses:
            raise HTTPException(status_code=404, detail="Business not found")

        products = await supabase_rest.list_rows(
            "products", token, filters={"business_id": f"eq.{business_id}"}
        )
        if not products:
            return {"status": "unavailable"}

        product_ids = ",".join(p["id"] for p in products)
        financial_records = await supabase_rest.list_rows(
            "financial_records", token, filters={"product_id": f"in.({product_ids})"}
        )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    summary = build_dashboard_summary(products, financial_records)
    total_revenue = summary["kpis"]["total_revenue"]
    total_margin = summary["kpis"]["total_margin"]
    if not total_revenue:
        return {"status": "unavailable"}

    industry = businesses[0].get("industry")
    if not industry:
        business_name = businesses[0].get("name") or ""
        product_names = [p.get("name") for p in products if p.get("name")]
        industry = classify_industry(business_name, product_names)
        if industry:
            try:
                await supabase_rest.update_row(
                    "businesses", token, {"id": f"eq.{business_id}"}, {"industry": industry}
                )
            except HTTPStatusError:
                pass  # caching failed -- still fine to answer this request, just re-classify next time

    comparison = compare_to_benchmark(industry, (total_margin / total_revenue) * 100)
    if comparison is None:
        return {"status": "unavailable"}

    return {
        "status": "ok",
        "industry": comparison.industry,
        "business_margin_pct": comparison.business_margin_pct,
        "benchmark_low_pct": comparison.benchmark_low_pct,
        "benchmark_high_pct": comparison.benchmark_high_pct,
        "position": comparison.position,
    }
