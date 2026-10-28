from app.config import settings
from app.external.fred import fetch_cpi_change_pct


def test_returns_none_without_an_api_key(monkeypatch):
    monkeypatch.setattr(settings, "fred_api_key", "")
    assert fetch_cpi_change_pct("2024-01-01", "2024-03-31") is None
