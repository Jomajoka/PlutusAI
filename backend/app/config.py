import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    cors_allowed_origins: list[str] = os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
    ).split(",")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")


settings = Settings()
