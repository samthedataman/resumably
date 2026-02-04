"""
Application configuration using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Resumably"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql://localhost/resumably"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # 2FA
    totp_issuer: str = "Resumably"

    # Google/Gmail OAuth
    google_credentials: str = ""
    google_client_id: str = ""  # For Google Sign-In

    # Anthropic
    anthropic_api_key: str = ""

    # Frontend URL (for CORS)
    frontend_url: str = "http://localhost:3000"

    # Email Settings (for password reset)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@resumably.com"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
