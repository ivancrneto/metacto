"""Config validation — the production secret guard."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_secure_cookies_require_a_non_default_secret() -> None:
    # Secure cookies (production) + the built-in placeholder secret must not boot.
    with pytest.raises(ValidationError):
        Settings(cookie_secure=True)


def test_secure_cookies_ok_with_an_explicit_secret() -> None:
    settings = Settings(cookie_secure=True, secret_key="a-real-secret")
    assert settings.cookie_secure is True
