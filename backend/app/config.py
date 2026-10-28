import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    cors_allowed_origins: list[str] = os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
    ).split(",")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    # Provider-agnostic: any OpenAI-compatible chat completions endpoint
    # (OpenRouter, Groq, etc). We've already had to switch providers once
    # due to free-tier rate limits, so this is config, not hardcoded.
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv(
        "LLM_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"
    )
    # Comma-separated, tried in order (fallback chain).
    llm_structuring_models: list[str] = [
        m for m in os.getenv("LLM_STRUCTURING_MODELS", "").split(",") if m
    ]


settings = Settings()
