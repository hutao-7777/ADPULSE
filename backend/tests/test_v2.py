"""Integration tests for authentication and v2 production services."""

import uuid
from typing import Any, cast

import pytest

pytestmark = pytest.mark.asyncio


def _unwrap(resp) -> dict[str, Any]:
    return cast(dict[str, Any], resp.json()["data"])


async def _login_admin(client) -> dict:
    resp = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert resp.status_code == 200
    return _unwrap(resp)


async def test_auth_login_and_profile(client):
    tokens = await _login_admin(client)
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"

    me = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert _unwrap(me)["email"] == "admin@example.com"


async def test_auth_register_refresh_and_api_keys(client):
    admin = await _login_admin(client)
    admin_token = admin["access_token"]

    register = await client.post(
        "/api/auth/register",
        json={"email": "advertiser@example.com", "password": "secret123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert register.status_code == 201

    user_tokens = await client.post(
        "/api/auth/login",
        json={"email": "advertiser@example.com", "password": "secret123"},
    )
    assert user_tokens.status_code == 200
    refresh_token = _unwrap(user_tokens)["refresh_token"]

    refreshed = await client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refreshed.status_code == 200
    assert "access_token" in _unwrap(refreshed)

    key_resp = await client.post(
        "/api/auth/api-keys",
        json={"name": "dsp-test", "scopes": ["rtb:write"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert key_resp.status_code == 201
    raw_key = _unwrap(key_resp)["key"]

    list_resp = await client.get(
        "/api/auth/api-keys", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert list_resp.status_code == 200
    assert any(k["name"] == "dsp-test" for k in _unwrap(list_resp))

    check = await client.get("/api/auth/api-key-check", headers={"X-API-Key": raw_key})
    assert check.status_code == 200
    assert _unwrap(check)["valid"] is True


async def test_rtb_v2_auction(client):
    admin = await _login_admin(client)
    key_resp = await client.post(
        "/api/auth/api-keys",
        json={"name": "rtb-test", "scopes": ["rtb:write"]},
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )
    raw_key = _unwrap(key_resp)["key"]

    auction = await client.post(
        "/api/v2/rtb/auction",
        json={
            "request_id": "req-1",
            "impression_id": "imp-1",
            "floor_price": 0.5,
            "user_id": "user-1",
            "device_type": "mobile",
            "geo": "tier1",
            "context": {"category": "news"},
        },
        headers={"X-API-Key": raw_key},
    )
    assert auction.status_code == 200
    data = _unwrap(auction)
    assert data["request_id"] == "req-1"
    assert data["currency"] == "USD"
    assert data["latency_ms"] >= 0


async def test_agent_v2_config_and_run(client):
    admin = await _login_admin(client)
    token = admin["access_token"]

    config_resp = await client.post(
        "/api/v2/agent/configs",
        json={
            "name": "test-agent",
            "goal": "maximize roi",
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
            "max_steps": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert config_resp.status_code == 201
    config_id = _unwrap(config_resp)["id"]

    run_resp = await client.post(
        f"/api/v2/agent/{config_id}/run",
        json={"goal": "maximize roi", "max_steps": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert run_resp.status_code == 200
    data = _unwrap(run_resp)
    assert "steps" in data
    assert "final_output" in data


async def test_ab_v2_engine_assign():
    from app.services.ab_test_v2_engine import ABTestV2Engine

    engine = ABTestV2Engine()
    bucket = engine._hash_bucket("user-1", uuid.uuid4())
    assert 0 <= bucket < 100


async def test_attribution_v2_compare_models():
    from datetime import datetime
    from types import SimpleNamespace

    from app.services.attribution_v2_engine import AttributionV2Engine

    engine = AttributionV2Engine()
    now = datetime.utcnow()
    touchpoints = [
        SimpleNamespace(
            id=uuid.uuid4(),
            channel="search",
            event_type="click",
            event_time=now,
            touchpoint_seq=1,
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            channel="social",
            event_type="click",
            event_time=now,
            touchpoint_seq=2,
        ),
    ]
    comparison = engine.compare_models(touchpoints, 1.0, 7, 1)
    assert "first_touch" in comparison
    assert "shapley" in comparison
