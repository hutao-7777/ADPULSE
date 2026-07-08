"""Seed mock data for local development and integration tests."""

import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.models import (
    ABTest,
    ABTestVariant,
    ApiKey,
    Auction,
    Campaign,
    Creative,
    DailyMetric,
    Permission,
    Role,
    User,
    role_permissions,
    user_roles,
)

NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _uuid(name: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, name)


def _now() -> datetime:
    return datetime.utcnow()


async def seed_data(session: AsyncSession | None = None) -> None:
    """Seed deterministic mock data using INSERT OR IGNORE semantics."""
    if session is None:
        async with AsyncSessionLocal() as session:
            await _seed_all(session)
    else:
        await _seed_all(session)


async def _seed_all(session: AsyncSession) -> None:
    await _seed_auth(session)
    await _seed_campaigns(session)
    await _seed_daily_metrics(session)
    await _seed_creatives(session)
    await _seed_ab_tests(session)
    await _seed_auctions(session)


async def _seed_auth(session: AsyncSession) -> None:
    """Seed default roles, permissions and a demo admin user."""
    # Permissions
    permission_codes = [
        "user:write",
        "campaign:read",
        "campaign:write",
        "apikey:write",
        "rtb:write",
    ]
    permissions = [
        {"id": _uuid(f"permission-{code}"), "code": code} for code in permission_codes
    ]
    await session.execute(
        sqlite_insert(Permission)
        .values(permissions)
        .on_conflict_do_nothing(index_elements=["id"])
    )

    # Roles
    role_defs = {
        "admin": permission_codes,
        "advertiser": ["campaign:read", "campaign:write", "apikey:write"],
        "viewer": ["campaign:read"],
    }
    role_records = {}
    for role_name, perms in role_defs.items():
        role_id = _uuid(f"role-{role_name}")
        role_records[role_name] = role_id
        await session.execute(
            sqlite_insert(Role)
            .values({"id": role_id, "name": role_name})
            .on_conflict_do_nothing(index_elements=["id"])
        )
        # Link permissions
        role_perms = []
        for code in perms:
            perm_id = _uuid(f"permission-{code}")
            role_perms.append({"role_id": role_id, "permission_id": perm_id})
        if role_perms:
            await session.execute(
                sqlite_insert(role_permissions)
                .values(role_perms)
                .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
            )

    # Demo admin user
    admin_id = _uuid("user-admin")
    await session.execute(
        sqlite_insert(User)
        .values(
            {
                "id": admin_id,
                "email": "admin@example.com",
                "hashed_password": get_password_hash("admin123"),
                "full_name": "Demo Admin",
                "is_active": True,
                "is_superuser": True,
            }
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.execute(
        sqlite_insert(user_roles)
        .values({"user_id": admin_id, "role_id": role_records["admin"]})
        .on_conflict_do_nothing(index_elements=["user_id", "role_id"])
    )

    # Demo DSP API key (raw key: adpulse_demo_dsp_key)
    api_key_id = _uuid("apikey-demo-dsp")
    await session.execute(
        sqlite_insert(ApiKey)
        .values(
            {
                "id": api_key_id,
                "user_id": admin_id,
                "name": "Demo DSP Key",
                "key_prefix": "adpulse_",
                "key_hash": get_password_hash("adpulse_demo_dsp_key"),
                "scopes": ["rtb:write"],
                "rate_limit_rps": 1000,
                "is_active": True,
            }
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )

    await session.commit()


SEED_CAMPAIGNS = {
    "Summer Sale 2026": _uuid("campaign-summer-sale-2026"),
    "App Install Q3": _uuid("campaign-app-install-q3"),
    "Brand Awareness": _uuid("campaign-brand-awareness"),
}


async def _seed_campaigns(session: AsyncSession) -> None:
    campaigns = [
        {
            "id": _uuid("campaign-summer-sale-2026"),
            "name": "Summer Sale 2026",
            "status": "running",
            "budget": 10000.0,
            "spent": 3450.0,
            "start_date": _now() - timedelta(days=7),
            "target_cpa": 45.0,
            "created_at": _now() - timedelta(days=7),
        },
        {
            "id": _uuid("campaign-app-install-q3"),
            "name": "App Install Q3",
            "status": "running",
            "budget": 5000.0,
            "spent": 1200.0,
            "start_date": _now() - timedelta(days=5),
            "target_cpa": 30.0,
            "created_at": _now() - timedelta(days=5),
        },
        {
            "id": _uuid("campaign-brand-awareness"),
            "name": "Brand Awareness",
            "status": "paused",
            "budget": 20000.0,
            "spent": 8900.0,
            "start_date": _now() - timedelta(days=14),
            "target_cpa": 60.0,
            "created_at": _now() - timedelta(days=14),
        },
    ]
    await session.execute(
        sqlite_insert(Campaign)
        .values(campaigns)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.commit()


async def _seed_daily_metrics(session: AsyncSession) -> None:
    campaign_ids = [
        _uuid("campaign-summer-sale-2026"),
        _uuid("campaign-app-install-q3"),
        _uuid("campaign-brand-awareness"),
    ]

    rng = random.Random(42)
    metrics = []
    for campaign_id in campaign_ids:
        for day_offset in range(7):
            date = (_now() - timedelta(days=6 - day_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            impressions = rng.randint(1000, 5000)
            ctr = rng.uniform(0.01, 0.05)
            clicks = int(impressions * ctr)
            clicks = max(1, clicks)
            conversion_rate = rng.uniform(0.05, 0.15)
            conversions = int(clicks * conversion_rate)
            cpm = rng.uniform(2.0, 10.0)
            spend = impressions * cpm / 1000.0
            revenue_per_conversion = rng.uniform(20.0, 100.0)
            revenue = conversions * revenue_per_conversion

            metrics.append(
                {
                    "id": _uuid(f"daily-metric-{campaign_id}-{date.isoformat()}"),
                    "date": date,
                    "campaign_id": campaign_id,
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "spend": round(spend, 4),
                    "revenue": round(revenue, 4),
                    "ctr": round(clicks / impressions, 6),
                    "cpm": round(spend / impressions * 1000, 4),
                    "cpc": round(spend / clicks, 4),
                    "roi": round(revenue / spend, 4) if spend > 0 else 0.0,
                }
            )

    await session.execute(
        sqlite_insert(DailyMetric)
        .values(metrics)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.commit()


async def _seed_creatives(session: AsyncSession) -> None:
    creatives = [
        {
            "id": _uuid("creative-summer-banner-v1"),
            "name": "summer_banner_v1",
            "image_path": "uploads/seed_summer_banner_v1.png",
            "file_type": "image/png",
            "ai_score": 87.0,
            "predicted_ctr": 0.032,
            "fatigue_score": 0.25,
        },
        {
            "id": _uuid("creative-summer-banner-v2"),
            "name": "summer_banner_v2",
            "image_path": "uploads/seed_summer_banner_v2.png",
            "file_type": "image/png",
            "ai_score": 72.0,
            "predicted_ctr": 0.025,
            "fatigue_score": 0.45,
        },
        {
            "id": _uuid("creative-app-install-native"),
            "name": "app_install_native",
            "image_path": "uploads/seed_app_install_native.png",
            "file_type": "image/png",
            "ai_score": 91.0,
            "predicted_ctr": 0.041,
            "fatigue_score": 0.15,
        },
    ]
    await session.execute(
        sqlite_insert(Creative)
        .values(creatives)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.commit()


async def _seed_ab_tests(session: AsyncSession) -> None:
    campaign_summer = _uuid("campaign-summer-sale-2026")
    campaign_app = _uuid("campaign-app-install-q3")

    ab_tests = [
        {
            "id": _uuid("abtest-summer-banner"),
            "name": "Summer Banner Test",
            "campaign_id": campaign_summer,
            "status": "running",
            "traffic_split": 0.5,
            "metric_target": "ctr",
            "start_date": _now() - timedelta(days=3),
            "created_at": _now() - timedelta(days=3),
        },
        {
            "id": _uuid("abtest-landing-page"),
            "name": "Landing Page Test",
            "campaign_id": campaign_app,
            "status": "stopped",
            "traffic_split": 0.5,
            "metric_target": "conversion_rate",
            "start_date": _now() - timedelta(days=5),
            "end_date": _now() - timedelta(days=1),
            "created_at": _now() - timedelta(days=5),
        },
    ]
    await session.execute(
        sqlite_insert(ABTest)
        .values(ab_tests)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.commit()

    variants = [
        # Summer Banner Test
        {
            "id": _uuid("variant-summer-control"),
            "ab_test_id": _uuid("abtest-summer-banner"),
            "name": "control",
            "traffic_pct": 0.5,
            "impressions": 2500,
            "clicks": 75,
            "conversions": 5,
            "revenue": 250.0,
        },
        {
            "id": _uuid("variant-summer-blue-cta"),
            "ab_test_id": _uuid("abtest-summer-banner"),
            "name": "blue_cta",
            "traffic_pct": 0.5,
            "impressions": 2480,
            "clicks": 92,
            "conversions": 7,
            "revenue": 420.0,
        },
        # Landing Page Test
        {
            "id": _uuid("variant-landing-original"),
            "ab_test_id": _uuid("abtest-landing-page"),
            "name": "original",
            "traffic_pct": 0.5,
            "impressions": 1200,
            "clicks": 48,
            "conversions": 5,
            "revenue": 180.0,
        },
        {
            "id": _uuid("variant-landing-simplified"),
            "ab_test_id": _uuid("abtest-landing-page"),
            "name": "simplified",
            "traffic_pct": 0.5,
            "impressions": 1180,
            "clicks": 52,
            "conversions": 8,
            "revenue": 320.0,
        },
    ]
    await session.execute(
        sqlite_insert(ABTestVariant)
        .values(variants)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.commit()


async def _seed_auctions(session: AsyncSession) -> None:
    campaign_ids = [
        _uuid("campaign-summer-sale-2026"),
        _uuid("campaign-app-install-q3"),
        _uuid("campaign-brand-awareness"),
    ]
    dsps = ["DSP_A", "DSP_B", "DSP_C"]
    rng = random.Random(2026)

    auctions = []
    for i in range(50):
        campaign_id = campaign_ids[i % len(campaign_ids)]
        created_at = _now() - timedelta(minutes=rng.randint(0, 1440))
        floor_price = round(rng.uniform(1.0, 10.0), 4)
        winning_bid = round(rng.uniform(2.0, 15.0), 4)
        auctions.append(
            {
                "id": _uuid(f"auction-seed-{i}"),
                "campaign_id": campaign_id,
                "impression_id": f"imp-seed-{i:03d}",
                "floor_price": floor_price,
                "winning_bid": winning_bid,
                "winning_dsp": rng.choice(dsps),
                "auction_type": rng.choice(["first_price", "second_price"]),
                "latency_ms": float(rng.randint(10, 80)),
                "created_at": created_at,
            }
        )

    await session.execute(
        sqlite_insert(Auction)
        .values(auctions)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.commit()
