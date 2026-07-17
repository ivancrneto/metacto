from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLAlchemy async URL. Host port 5433 maps to the docker-compose Postgres
    # (5432 inside the compose network). Override via DATABASE_URL as needed.
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/metacto"

    # Ranking: higher gravity punishes age more aggressively in "trending".
    trending_gravity: float = 1.5

    app_env: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
