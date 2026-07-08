"""Shared pytest fixtures for AdPulse API tests."""

from contextlib import asynccontextmanager

import httpx
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import (
    abtest,
    abtest_v2,
    agent,
    agent_v2,
    attribution,
    attribution_v2,
    auth,
    dashboard,
    rtb,
    rtb_v2,
    traffic,
)
from app.core.database import Base, get_db
from app.core.response import register_exception_handlers
from app.core.seed import seed_data


@pytest_asyncio.fixture
async def client():
    """Create a test client backed by an in-memory SQLite database."""
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
    test_app.include_router(attribution_v2.router)
    test_app.include_router(traffic.router)
    test_app.include_router(rtb.router)
    test_app.include_router(rtb_v2.router)
    test_app.include_router(abtest.router)
    test_app.include_router(abtest_v2.router)
    test_app.include_router(dashboard.router)
    test_app.include_router(agent.router)
    test_app.include_router(agent_v2.router)
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
