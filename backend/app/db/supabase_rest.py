import httpx

from app.config import settings


def _headers(user_token: str) -> dict[str, str]:
    return {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
    }


async def list_rows(
    table: str, user_token: str, filters: dict[str, str] | None = None
) -> list[dict]:
    url = f"{settings.supabase_url}/rest/v1/{table}"
    params = {"select": "*", **(filters or {})}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers(user_token), params=params)
        resp.raise_for_status()
        return resp.json()


async def insert_row(table: str, user_token: str, payload: dict) -> dict:
    url = f"{settings.supabase_url}/rest/v1/{table}"
    headers = _headers(user_token)
    headers["Prefer"] = "return=representation"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()[0]
