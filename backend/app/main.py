"""AdPulse FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from app.core.config import settings
from app.core.database import Base, engine
from app.core.redis import close_redis
from app.core.response import register_exception_handlers
from app.core.seed import seed_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create tables, seed data, cleanup resources."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_data()
    yield
    await engine.dispose()
    await close_redis()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS whitelist - no wildcard in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(attribution.router)
app.include_router(attribution_v2.router)
app.include_router(traffic.router)
app.include_router(rtb.router)
app.include_router(rtb_v2.router)
app.include_router(abtest.router)
app.include_router(abtest_v2.router)
app.include_router(dashboard.router)
app.include_router(agent.router)
app.include_router(agent_v2.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
