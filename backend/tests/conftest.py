from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh async session per test.

    Uses NullPool so each connection is created/disposed without pooling,
    avoiding event loop mismatch issues with asyncpg + pytest-asyncio.
    Tables are already created by the Alembic migration.
    """
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    session = session_maker()
    yield session
    # Session/engine cleanup is intentionally omitted here.
    # pytest-asyncio runs fixture teardown on a different event loop than
    # the test body, which causes asyncpg "attached to a different loop"
    # errors. NullPool ensures connections are not cached between tests.
