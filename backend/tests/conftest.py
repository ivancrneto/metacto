"""Test harness.

Tests run against a real Postgres (matching production) in a dedicated
``metacto_test`` database, created once and truncated between tests. Each test
gets its own AsyncEngine created inside its own event loop, which sidesteps
pytest-asyncio's cross-loop pitfalls without any global loop juggling.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.models  # noqa: F401 — register tables on Base.metadata
from app.config import settings
from app.db import Base, get_session
from app.main import app

TEST_DB = "metacto_test"

_server = settings.database_url.rsplit("/", 1)[0]
TEST_DATABASE_URL = f"{_server}/{TEST_DB}"
ADMIN_DATABASE_URL = f"{_server}/postgres"

_schema_ready = False


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    global _schema_ready

    admin = create_async_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        if not _schema_ready:
            await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
            await conn.execute(text(f"CREATE DATABASE {TEST_DB}"))
    await admin.dispose()

    eng = create_async_engine(TEST_DATABASE_URL)
    if not _schema_ready:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _schema_ready = True

    # Clean slate for every test.
    async with eng.begin() as conn:
        await conn.execute(text("TRUNCATE users, feature_requests, votes RESTART IDENTITY CASCADE"))

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Direct DB access for tests that need to plant rows (e.g. custom ages)."""
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    async def _override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def create_request(
    client: AsyncClient,
) -> Callable[..., Awaitable[dict[str, Any]]]:
    """Helper: create a feature request as ``author`` and return the JSON body."""

    async def _create(
        author: str,
        title: str = "A perfectly reasonable feature",
        description: str = "Some useful description.",
    ) -> dict[str, Any]:
        resp = await client.post(
            "/feature-requests",
            headers={"X-User": author},
            json={"title": title, "description": description},
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _create
