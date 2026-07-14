"""AdPulse SDK Platform - FastAPI entrypoint."""

import os
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api import (
    ad_units,
    attribution,
    auth,
    bidding,
    dashboard,
    events,
    publishers,
    report,
    sdk_config,
    traffic,
)
from app.core.config import settings
from app.core.database import Base, engine
from app.core.response import register_exception_handlers
from app.core.seed import seed_data


def _ensure_security_settings():
    if not settings.SECRET_KEY or settings.SECRET_KEY in {
        "change-me-in-production",
        "dev-secret-change-me",
        "",
    }:
        raise RuntimeError("SECRET_KEY is not configured.")


async def _database_is_empty(conn) -> bool:
    def _check(sync_conn) -> bool:
        tables = inspect(sync_conn).get_table_names()
        if not tables:
            return True
        for table in tables:
            row = sync_conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1")).first()
            if row is not None:
                return False
        return True

    return cast(bool, await conn.run_sync(_check))


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_security_settings()
    reset_on_start = os.environ.get("RESET_DB_ON_START", "").lower() in {
        "1",
        "true",
        "yes",
    }
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        if reset_on_start or await _database_is_empty(conn):
            async_session = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            async with async_session() as session:
                await seed_data(session, reset=reset_on_start)
    yield
    await engine.dispose()


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(publishers.router)
app.include_router(ad_units.router)
app.include_router(events.router)
app.include_router(bidding.router)
app.include_router(sdk_config.router)
app.include_router(attribution.router)
app.include_router(traffic.router)
app.include_router(report.router)
app.include_router(dashboard.router)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
