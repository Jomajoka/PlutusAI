import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    cors_allowed_origins: list[str] = os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
    ).split(",")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    # Config-driven, not hardcoded -- free-tier model lineups rotate over time.
    # Comma-separated, tried in order (fallback chain).
    openrouter_structuring_models: list[str] = [
        m for m in os.getenv("OPENROUTER_STRUCTURING_MODELS", "").split(",") if m
    ]


settings = Settings()
