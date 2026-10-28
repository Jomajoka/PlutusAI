from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from httpx import HTTPStatusError
from pydantic import BaseModel

from app.api.deps import get_user_token
from app.db import supabase_rest
from app.extraction.candidates import extract_candidates
from app.extraction.grouping import group_records
from app.extraction.pdf import extract_pages_text, select_relevant_pages
from app.llm.client import LLMUnavailableError
from app.llm.structuring import StructuredRecord, structure_candidates

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# How many pages (out of a long report) get sent on to extraction/LLM
# structuring. Keeps free-tier LLM calls bounded on large PDFs.
_MAX_RELEVANT_PAGES = 15


class PreviewRequest(BaseModel):
    business_id: str
    text: str


class PreviewRecord(BaseModel):
    field: str
    value: float
    product_name: str
    period: str | None
    source_line: str
    verified: bool


class PreviewResponse(BaseModel):
    records: list[PreviewRecord]
    unverified_records: list[PreviewRecord]
    notes: list[dict]


class ConfirmRecord(BaseModel):
    field: str
    value: float
    product_name: str
    period: str | None


class ConfirmNote(BaseModel):
    category: str | None
    text: str


class ConfirmRequest(BaseModel):
    business_id: str
    records: list[ConfirmRecord]
    notes: list[ConfirmNote] = []


async def _preview_from_text(text: str, business_id: str, token: str) -> PreviewResponse:
    candidates = extract_candidates(text)
    if not candidates:
        return PreviewResponse(records=[], unverified_records=[], notes=[])

    try:
        existing_products = await supabase_rest.list_rows(
            "products", token, filters={"business_id": f"eq.{business_id}"}
        )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
    known_product_names = [p["name"] for p in existing_products]

    try:
        result = structure_candidates(candidates, known_product_names)
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return PreviewResponse(
        records=[PreviewRecord(**_record_dict(r)) for r in result.records],
        unverified_records=[PreviewRecord(**_record_dict(r)) for r in result.unverified_records],
        notes=result.notes,
    )


@router.post("/text/preview", response_model=PreviewResponse)
async def preview_text(body: PreviewRequest, token: str = Depends(get_user_token)):
    return await _preview_from_text(body.text, body.business_id, token)


@router.post("/pdf/preview", response_model=PreviewResponse)
async def preview_pdf(
    business_id: str = Form(...),
    file: UploadFile = File(...),
    token: str = Depends(get_user_token),
):
    pdf_bytes = await file.read()
    try:
        pages = extract_pages_text(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {exc}")

    relevant_pages = select_relevant_pages(pages, max_pages=_MAX_RELEVANT_PAGES)
    combined_text = "\n".join(relevant_pages)

    return await _preview_from_text(combined_text, business_id, token)


@router.post("/text/confirm")
async def confirm_text(body: ConfirmRequest, token: str = Depends(get_user_token)):
    structured = [
        StructuredRecord(
            field=r.field,
            value=r.value,
            product_name=r.product_name,
            period=r.period,
            source_line="",
            verified=True,
        )
        for r in body.records
    ]
    financial_rows, unit_prices = group_records(structured)

    try:
        existing_products = await supabase_rest.list_rows(
            "products", token, filters={"business_id": f"eq.{body.business_id}"}
        )
        product_ids = {p["name"]: p["id"] for p in existing_products}

        for name in {row.product_name for row in financial_rows} | set(unit_prices):
            if name in product_ids:
                continue
            created = await supabase_rest.insert_row(
                "products",
                token,
                {
                    "business_id": body.business_id,
                    "name": name,
                    "unit_price": unit_prices.get(name),
                },
            )
            product_ids[name] = created["id"]

        for row in financial_rows:
            await supabase_rest.insert_row(
                "financial_records",
                token,
                {
                    "product_id": product_ids[row.product_name],
                    "period": row.period,
                    "revenue": row.revenue,
                    "units_sold": row.units_sold,
                    "cost_breakdown": row.cost_breakdown,
                },
            )

        for note in body.notes:
            await supabase_rest.insert_row(
                "business_notes",
                token,
                {
                    "business_id": body.business_id,
                    "category": note.category,
                    "content": {"text": note.text},
                },
            )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    return {"saved_financial_rows": len(financial_rows), "saved_notes": len(body.notes)}


def _record_dict(record: StructuredRecord) -> dict:
    return {
        "field": record.field,
        "value": record.value,
        "product_name": record.product_name,
        "period": record.period,
        "source_line": record.source_line,
        "verified": record.verified,
    }
