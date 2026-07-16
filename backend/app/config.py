"""Application configuration, overridable via APP_-prefixed env vars or a .env file."""

from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET = "dev-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    # SQLite for local dev; set a postgresql+psycopg://... URL in production.
    database_url: str = "sqlite:///./app.db"

    # Signs the anonymous voter-identity cookie. MUST be overridden in production.
    secret_key: str = _DEFAULT_SECRET

    cookie_name: str = "frb_voter"
    cookie_secure: bool = False  # set true when served over HTTPS
    cookie_max_age: int = 60 * 60 * 24 * 365  # one year

    # Where the built React bundle lives; served same-origin in production.
    frontend_dir: str = "frontend/dist"

    @model_validator(mode="after")
    def _require_secret_in_production(self) -> Settings:
        # If we're issuing Secure cookies (i.e. production over HTTPS), refuse to
        # run with the built-in placeholder secret — otherwise identity cookies
        # would be signed with a publicly known key and could be forged.
        if self.cookie_secure and self.secret_key == _DEFAULT_SECRET:
            raise ValueError("APP_SECRET_KEY must be set when APP_COOKIE_SECURE is true")
        return self


settings = Settings()
