"""Shared pytest fixtures for AdPulse API tests."""

import os
from contextlib import asynccontextmanager

import httpx  # noqa: E402
import pytest_asyncio  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Ensure required settings are present before the app configuration is imported.
os.environ.setdefault(
    "SECRET_KEY", "test-secret-key-must-be-at-least-32-characters-long"
)
os.environ.setdefault("ENABLE_PUBLIC_REGISTRATION", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.api import (  # noqa: E402
    abtest,
    agent,
    attribution,
    auth,
    dashboard,
    rtb,
    traffic,
)
from app.core.config import settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.response import register_exception_handlers  # noqa: E402
from app.core.seed import seed_data  # noqa: E402


@pytest_asyncio.fixture
async def client():
    """Create a test client backed by an in-memory SQLite database."""
    settings.SECRET_KEY = "test-secret-key-must-be-at-least-32-characters-long"
    settings.ENABLE_PUBLIC_REGISTRATION = True
    settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"

    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        echo=False,
    )
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    async with TestSessionLocal() as seed_session:
        await seed_data(seed_session)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
        await test_engine.dispose()

    test_app = FastAPI(lifespan=lifespan)
    register_exception_handlers(test_app)
    test_app.include_router(auth.router)
    test_app.include_router(attribution.router)
    test_app.include_router(traffic.router)
    test_app.include_router(rtb.router)
    test_app.include_router(abtest.router)
    test_app.include_router(dashboard.router)
    test_app.include_router(agent.router)
    test_app.dependency_overrides[get_db] = override_get_db

    # Agent tools open their own sessions via AsyncSessionLocal; redirect them
    # to the in-memory test database so tests do not depend on adpulse.db.
    import app.agent.tools as tools_module

    tools_module.AsyncSessionLocal = TestSessionLocal

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
        timeout=httpx.Timeout(60.0),
    ) as ac:
        yield ac

    await test_engine.dispose()
    test_app.dependency_overrides.clear()
