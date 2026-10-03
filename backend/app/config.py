import os


class Settings:
    cors_allowed_origins: list[str] = os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
    ).split(",")


settings = Settings()
