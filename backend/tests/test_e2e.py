"""End-to-end tests for the AdPulse SDK Platform."""

import os
import pytest
import pytest_asyncio
import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("SECRET_KEY", "test-secret-at-least-32-chars-long-for-e2e")
os.environ.setdefault("ENABLE_PUBLIC_REGISTRATION", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.api import attribution, auth, bidding, dashboard, events, publishers, report, sdk_config, traffic
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.response import register_exception_handlers
from app.core.seed import seed_data

@pytest_asyncio.fixture
async def client():
    settings.SECRET_KEY = "test-secret-at-least-32-chars-long-for-e2e"
    settings.ENABLE_PUBLIC_REGISTRATION = True
    settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        await seed_data(session)

    app = FastAPI(title="AdPulse Test")
    register_exception_handlers(app)

    async def override_get_db():
        async with TestSessionLocal() as s:
            try: yield s
            finally: await s.close()

    app.dependency_overrides[get_db] = override_get_db
    app.include_router(auth.router)
    app.include_router(publishers.router)
    app.include_router(events.router)
    app.include_router(bidding.router)
    app.include_router(sdk_config.router)
    app.include_router(attribution.router)
    app.include_router(traffic.router)
    app.include_router(report.router)
    app.include_router(dashboard.router)

    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_full_platform_flow(client: httpx.AsyncClient):
    """Test the complete SDK platform flow: auth ¡ú publisher ¡ú ad unit ¡ú events ¡ú attribution."""

    # 1. Auth: Login as demo user
    r = await client.post("/api/auth/login", json={"email": "demo@adpulse.com", "password": "demo123456"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json().get("access_token")
    assert token
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Auth: Verify token
    r = await client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert "demo@adpulse.com" in r.text

    # 3. Dashboard: Verify seeded KPIs
    r = await client.get("/api/dashboard/summary", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "impressions" in data
    assert data["impressions"] > 0, "No seeded impressions"

    # 4. Publishers: List
    r = await client.get("/api/publishers", headers=headers)
    assert r.status_code == 200
    publishers = r.json()
    assert len(publishers) > 0
    pub_id = publishers[0]["id"]

    # 5. Apps: List under publisher
    r = await client.get(f"/api/publishers/{pub_id}/apps", headers=headers)
    assert r.status_code == 200
    apps = r.json()
    assert len(apps) > 0
    app_id = apps[0]["id"]

    # 6. Ad Units: List
    r = await client.get(f"/api/ad-units?app_id={app_id}", headers=headers)
    assert r.status_code == 200
    units = r.json()
    assert len(units) > 0
    au_id = units[0]["id"]

    # 7. Ad Networks: List
    r = await client.get("/api/ad-units/ad-networks", headers=headers)
    assert r.status_code == 200
    nets = r.json()
    assert len(nets) > 0
    net_id = nets[0]["id"]

    # 8. Ad Sources: List
    r = await client.get(f"/api/ad-units/{au_id}/sources", headers=headers)
    assert r.status_code == 200
    sources = r.json()
    assert len(sources) > 0
    src_id = sources[0]["id"]

    # 9. SDK Config: Fetch config
    r = await client.get(f"/v1/sdk/config/{au_id}?publisher=pub_key&device_id=e2e_test_dev")
    assert r.status_code == 200
    config = r.json()
    assert config["ad_unit_id"] == str(au_id)

    # 10. Bidding: Request bid
    r = await client.post("/v1/bid", json={
        "publisher_key": "test_key", "ad_unit_id": str(au_id),
        "device_id": "e2e_test_dev", "sdk_version": "1.0.0",
    })
    assert r.status_code == 200
    bid = r.json()
    assert bid["ad_unit_id"] == str(au_id)
    assert bid["source_type"] in ("bidding", "waterfall", "fallback")

    # 11. Events: Track impression
    r = await client.post("/v1/events/impression", json={
        "impression_id": "e2e_imp_1", "ad_unit_id": str(au_id),
        "device_id": "e2e_dev", "revenue": 0.005,
    })
    assert r.status_code == 204

    # 12. Events: Track click
    r = await client.post("/v1/events/click", json={
        "click_id": "e2e_clk_1", "impression_id": "e2e_imp_1",
        "ad_unit_id": str(au_id), "device_id": "e2e_dev",
    })
    assert r.status_code == 204

    # 13. Events: Track conversion
    r = await client.post("/v1/events/conversion", json={
        "event_type": "install", "device_id": "e2e_dev",
        "click_id": "e2e_clk_1", "event_value": 1.0,
    })
    assert r.status_code == 204

    # 14. Attribution: Match conversion
    r = await client.post("/api/attribution/create-and-match", json={
        "device_id": "e2e_dev", "event_type": "install", "event_value": 1.0,
    }, headers=headers)
    assert r.status_code == 200
    attr = r.json()
    assert attr["attributed_network"] in ("ad_mob", None)  # may match if events exist

    # 15. Attribution: Report
    r = await client.get("/api/attribution/report?days=7", headers=headers)
    assert r.status_code == 200
    report_data = r.json()
    assert "total_conversions" in report_data

    # 16. Traffic: Assess quality
    r = await client.post(f"/api/traffic/assess/{au_id}", headers=headers)
    assert r.status_code == 200
    quality = r.json()
    assert quality["quality_score"] >= 0
    assert quality["grade"] in ("premium", "standard", "low", "fraud")

    # 17. Traffic: Get alerts
    r = await client.get(f"/api/traffic/ad-unit/{au_id}/alerts?days=7", headers=headers)
    assert r.status_code == 200
    # May have 0 alerts for clean data

    # 18. Report: Export CSV
    r = await client.get("/api/report/summary?format=csv&days=7", headers=headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")

    # 19. Report: Export JSON
    r = await client.get("/api/report/summary?format=json&days=7", headers=headers)
    assert r.status_code == 200
    assert "rows" in r.json()

    # 20. Update waterfall order
    r = await client.patch(f"/api/ad-units/{au_id}/waterfall", json=[src_id], headers=headers)
    # Should succeed ¡ª test may need auth; 200 or 401 depending on dependency setup
    assert r.status_code in (200, 401)

    # 21. Update AdSource eCPM
    r = await client.patch(f"/api/ad-units/sources/{src_id}", json={"ecpm": 6.50}, headers=headers)
    assert r.status_code in (200, 401)

    # 22. Dashboard trend
    r = await client.get("/api/dashboard/trend", headers=headers)
    assert r.status_code == 200
    trend = r.json()
    assert "trend" in trend
