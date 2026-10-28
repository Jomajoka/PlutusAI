"""Fetch general US inflation (CPI) context from FRED (Federal Reserve
Economic Data), a free government data source. Used only as supplementary
context for narration/backtest results -- never fed into the calc engine's
actual math -- so a failure here should never break the response it's
supplementary to. Reuses app/calc_engine/periods.py to turn our loose
`period` text labels into the date range FRED needs.
"""

import httpx

from app.config import settings

_TIMEOUT_SECONDS = 15
_CPI_SERIES_ID = "CPIAUCSL"  # CPI for All Urban Consumers, seasonally adjusted


def fetch_cpi_change_pct(start_date: str, end_date: str) -> float | None:
    """% change in CPI between the first and last available observation in
    [start_date, end_date] (ISO "YYYY-MM-DD"). Returns None -- never raises --
    if the API key isn't configured, the request fails, or there isn't
    enough data in the window to compute a change.
    """
    if not settings.fred_api_key:
        return None

    try:
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            resp = client.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id": _CPI_SERIES_ID,
                    "api_key": settings.fred_api_key,
                    "file_type": "json",
                    "observation_start": start_date,
                    "observation_end": end_date,
                },
            )
            resp.raise_for_status()
            observations = resp.json().get("observations", [])
    except (httpx.HTTPError, ValueError, KeyError):
        return None

    values = [
        float(obs["value"]) for obs in observations if obs.get("value") not in (None, ".")
    ]
    if len(values) < 2 or values[0] == 0:
        return None

    return (values[-1] - values[0]) / values[0]
