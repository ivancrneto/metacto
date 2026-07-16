"""Application configuration, overridable via APP_-prefixed env vars or a .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    # SQLite for local dev; set a postgresql+psycopg://... URL in production.
    database_url: str = "sqlite:///./app.db"

    # Signs the anonymous voter-identity cookie. MUST be overridden in production.
    secret_key: str = "dev-insecure-secret-change-me"

    cookie_name: str = "frb_voter"
    cookie_secure: bool = False  # set true when served over HTTPS
    cookie_max_age: int = 60 * 60 * 24 * 365  # one year

    # Where the built React bundle lives; served same-origin in production.
    frontend_dir: str = "frontend/dist"


settings = Settings()
