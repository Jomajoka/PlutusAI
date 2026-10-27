from fastapi import APIRouter, Depends, HTTPException
from httpx import HTTPStatusError
from pydantic import BaseModel

from app.api.deps import get_user_token
from app.db import supabase_rest

router = APIRouter(prefix="/businesses", tags=["businesses"])


class CreateBusiness(BaseModel):
    name: str


@router.get("")
async def list_businesses(token: str = Depends(get_user_token)):
    try:
        return await supabase_rest.list_rows("businesses", token)
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


@router.post("")
async def create_business(body: CreateBusiness, token: str = Depends(get_user_token)):
    try:
        return await supabase_rest.insert_row("businesses", token, {"name": body.name})
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
