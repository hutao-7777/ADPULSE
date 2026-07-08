from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.core.seed import seed_data
from app.api import attribution, rtb, dashboard, abtest, agent, traffic


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_data()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(attribution.router)
app.include_router(traffic.router)
app.include_router(rtb.router)
app.include_router(abtest.router)
app.include_router(dashboard.router)
app.include_router(agent.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
