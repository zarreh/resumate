import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings
from src.core.database import get_db
from src.main import app

# Test engine with NullPool to avoid event loop issues with asyncpg
_test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_test_session_maker = async_sessionmaker(_test_engine, expire_on_commit=False)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _test_session_maker() as session:
        yield session


# Override get_db globally for all tests
app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh async session per test (for direct DB access in tests).

    Session/engine cleanup is intentionally omitted here.
    pytest-asyncio runs fixture teardown on a different event loop than
    the test body, which causes asyncpg "attached to a different loop"
    errors. NullPool ensures connections are not cached between tests.
    """
    session = _test_session_maker()
    yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client that talks to the app."""
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict:
    """Register a user via the API and return their info + tokens."""
    email = _unique_email()
    password = "testpassword123"
    resp = await client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "email": email, "password": password},
    )
    assert resp.status_code == 201
    data = resp.json()
    return {
        "email": email,
        "password": password,
        "name": "Test User",
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
    }


@pytest_asyncio.fixture
async def auth_headers(registered_user: dict) -> dict[str, str]:
    """Return Authorization headers for the registered user."""
    return {"Authorization": f"Bearer {registered_user['access_token']}"}
