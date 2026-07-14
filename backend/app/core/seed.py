"""Seed data for AdPulse SDK Platform demo."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models import (
    AdNetwork, AdSource, AdUnit, App,
    ClickEvent, ConversionEvent, ImpressionEvent,
    Permission, Publisher, Role, User,
    role_permissions, user_roles,
)

NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

def _uuid(name): return uuid.uuid5(NAMESPACE, name)

async def seed_data(session, reset=False):
    if reset:
        for t in ["click_events","impression_events","conversion_events",
                  "ad_sources","ad_networks","ad_units","apps","publishers"]:
            await session.execute(text(f"DELETE FROM {t}"))
        await session.commit()
    await _seed_auth(session)
    await _seed_publisher_data(session)
    await _seed_events(session)

async def _seed_auth(session):
    admin_role = Role(id=_uuid("role_admin"), name="admin")
    pub_role = Role(id=_uuid("role_publisher"), name="publisher")
    session.add_all([admin_role, pub_role])
    perm1 = Permission(id=_uuid("perm_dash"), code="dashboard:read")
    session.add(perm1)
    user = User(
        id=_uuid("user_demo"), email="demo@adpulse.com",
        hashed_password=get_password_hash("demo123456"),
        full_name="Demo Publisher", is_active=True, is_superuser=True,
    )
    session.add(user)
    await session.flush()
    await session.execute(user_roles.insert().values(user_id=user.id, role_id=admin_role.id))
    await session.execute(role_permissions.insert().values(role_id=admin_role.id, permission_id=perm1.id))
    await session.commit()

async def _seed_publisher_data(session):
    pub = Publisher(
        id=_uuid("pub_demo"), owner_id=_uuid("user_demo"),
        name="Demo Media", status="active",
    )
    session.add(pub)
    await session.flush()

    web_app = App(
        id=_uuid("app_web"), publisher_id=pub.id,
        name="Demo Website", platform="web", domain="demo.com",
    )
    session.add(web_app)
    await session.flush()

    banner = AdUnit(
        id=_uuid("au_banner"), app_id=web_app.id,
        name="Header Banner", ad_format="banner", width=728, height=90,
    )
    interstitial = AdUnit(
        id=_uuid("au_interstitial"), app_id=web_app.id,
        name="Interstitial", ad_format="interstitial", width=320, height=480,
    )
    session.add_all([banner, interstitial])
    await session.flush()

    networks = [
        AdNetwork(id=_uuid("net_admob"), name="ad_mob", display_name="AdMob", supports_bidding=False),
        AdNetwork(id=_uuid("net_meta"), name="meta", display_name="Meta", supports_bidding=True),
        AdNetwork(id=_uuid("net_unity"), name="unity", display_name="Unity Ads", supports_bidding=False),
    ]
    session.add_all(networks)
    await session.flush()

    sources = [
        AdSource(ad_unit_id=banner.id, ad_network_id=_uuid("net_admob"), instance_name="AdMob Main", ecpm=4.50, priority=1),
        AdSource(ad_unit_id=banner.id, ad_network_id=_uuid("net_meta"), instance_name="Meta Bid", ecpm=5.20, priority=1, bidding_endpoint="https://meta.com/bid"),
        AdSource(ad_unit_id=banner.id, ad_network_id=_uuid("net_unity"), instance_name="Unity Backup", ecpm=3.20, priority=2),
    ]
    session.add_all(sources)
    banner.waterfall_config["order"] = ["net_admob", "net_unity"]
    banner.bidding_config = {"enabled": True, "timeout_ms": 500, "networks": ["net_meta"]}
    await session.commit()

async def _seed_events(session):
    now = datetime.now(timezone.utc)
    au_banner = _uuid("au_banner")
    pub_id = _uuid("pub_demo")
    app_id = _uuid("app_web")

    for day_offset in range(3):
        day = now - timedelta(days=2 - day_offset)
        for i in range(200):
            imp = ImpressionEvent(
                impression_id=f"imp_{day_offset}_{i}",
                ad_unit_id=au_banner, app_id=app_id, publisher_id=pub_id,
                network_name="ad_mob", revenue=0.005, currency="USD",
                created_at=day + timedelta(seconds=i * 30),
            )
            session.add(imp)

    for ci in range(20):
        ce = ClickEvent(
            click_id=f"clk_{ci}",
            impression_id=f"imp_{ci % 3}_{ci}",
            ad_unit_id=au_banner, network_name="ad_mob",
            created_at=now - timedelta(minutes=ci * 10),
        )
        session.add(ce)

    for vi in range(5):
        cv = ConversionEvent(
            event_type="install", device_id=f"dev_{vi}",
            click_id=f"clk_{vi * 4}",
            event_value=1.00, attributed_network="ad_mob",
            created_at=now - timedelta(minutes=vi * 30),
        )
        session.add(cv)

    await session.commit()
