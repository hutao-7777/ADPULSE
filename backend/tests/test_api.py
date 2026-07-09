"""Integration tests for AdPulse production services."""

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


async def test_rtb_auction(client):
    admin = await _login_admin(client)
    key_resp = await client.post(
        "/api/auth/api-keys",
        json={"name": "rtb-test", "scopes": ["rtb:write"]},
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )
    raw_key = _unwrap(key_resp)["key"]

    auction = await client.post(
        "/api/rtb/auction",
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


async def test_agent_config_and_run(client):
    admin = await _login_admin(client)
    token = admin["access_token"]

    config_resp = await client.post(
        "/api/agent/configs",
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
        f"/api/agent/{config_id}/run",
        json={"goal": "maximize roi", "max_steps": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert run_resp.status_code == 200
    data = _unwrap(run_resp)
    assert "steps" in data
    assert "final_output" in data


async def test_ab_engine_assign():
    from app.services.ab_test_engine import ABTestEngine

    engine = ABTestEngine()
    bucket = engine._hash_bucket("user-1", uuid.uuid4())
    assert 0 <= bucket < 100


async def test_attribution_compare_models():
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from app.services.attribution_engine import AttributionEngine

    engine = AttributionEngine()
    now = datetime.now(timezone.utc)
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


async def test_ab_experiment_lifecycle(client):
    admin = await _login_admin(client)
    token = admin["access_token"]

    create_resp = await client.post(
        "/api/abtests",
        json={
            "name": "cta_button_color_2024",
            "description": "测试CTA按钮颜色对转化率的影响",
            "traffic_split": 50,
            "variants": [
                {
                    "name": "control",
                    "config": {"button_color": "blue"},
                    "traffic_allocation": 50,
                },
                {
                    "name": "treatment",
                    "config": {"button_color": "red"},
                    "traffic_allocation": 50,
                },
            ],
            "success_metric": "conversion_rate",
            "min_sample_size": 100,
            "max_duration_days": 14,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    experiment = _unwrap(create_resp)
    assert experiment["status"] == "draft"
    assert len(experiment["variants"]) == 2
    exp_id = experiment["id"]

    # Invalid: allocations do not sum to 100
    invalid = await client.post(
        "/api/abtests",
        json={
            "name": "bad",
            "traffic_split": 50,
            "variants": [
                {"name": "a", "traffic_allocation": 30},
                {"name": "b", "traffic_allocation": 60},
            ],
            "success_metric": "conversion_rate",
            "min_sample_size": 100,
            "max_duration_days": 14,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert invalid.status_code == 422

    # Start experiment
    start = await client.patch(
        f"/api/abtests/{exp_id}/status",
        json={"status": "running"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert start.status_code == 200
    assert _unwrap(start)["status"] == "running"

    # Record exposure and conversion
    record = await client.post(
        f"/api/abtests/{exp_id}/record",
        json={
            "user_id": "user-1",
            "event_type": "exposure",
            "variant_name": "control",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert record.status_code == 201

    # Duplicate exposure should be silently accepted
    dup = await client.post(
        f"/api/abtests/{exp_id}/record",
        json={
            "user_id": "user-1",
            "event_type": "exposure",
            "variant_name": "control",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dup.status_code == 201

    conversion = await client.post(
        f"/api/abtests/{exp_id}/record",
        json={
            "user_id": "user-1",
            "event_type": "conversion",
            "variant_name": "control",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert conversion.status_code == 201

    # Pause / resume / stop
    paused = await client.patch(
        f"/api/abtests/{exp_id}/status",
        json={"status": "paused"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert paused.status_code == 200

    resumed = await client.patch(
        f"/api/abtests/{exp_id}/status",
        json={"status": "running"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resumed.status_code == 200

    stopped = await client.patch(
        f"/api/abtests/{exp_id}/status",
        json={"status": "stopped"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert stopped.status_code == 200

    # Cannot restart a stopped experiment
    restart = await client.patch(
        f"/api/abtests/{exp_id}/status",
        json={"status": "running"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert restart.status_code == 400


async def test_ab_status_transition_validation(client):
    admin = await _login_admin(client)
    token = admin["access_token"]

    create_resp = await client.post(
        "/api/abtests",
        json={
            "name": "incomplete",
            "traffic_split": 50,
            "variants": [
                {"name": "a", "traffic_allocation": 50},
                {"name": "b", "traffic_allocation": 50},
            ],
            "success_metric": "ctr",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    exp_id = _unwrap(create_resp)["id"]

    # Missing min_sample_size / max_duration_days
    bad = await client.patch(
        f"/api/abtests/{exp_id}/status",
        json={"status": "running"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad.status_code == 400


async def test_attribution_journey_lifecycle(client):
    admin = await _login_admin(client)
    token = admin["access_token"]
    campaign_id = str(uuid.uuid4())

    create_resp = await client.post(
        "/api/attribution/journeys",
        json={
            "user_id": "user-journey-1",
            "touchpoints": [
                {
                    "channel": "search_ads",
                    "campaign_id": campaign_id,
                    "timestamp": "2024-01-15T10:00:00Z",
                    "cost": 2.50,
                    "metadata": {"keyword": "buy shoes"},
                },
                {
                    "channel": "social_media",
                    "campaign_id": campaign_id,
                    "timestamp": "2024-01-16T14:30:00Z",
                    "cost": 1.20,
                    "metadata": {"platform": "instagram"},
                },
                {
                    "channel": "email",
                    "campaign_id": campaign_id,
                    "timestamp": "2024-01-18T09:00:00Z",
                    "cost": 0.30,
                    "metadata": {"campaign_name": "flash_sale"},
                },
            ],
            "conversion": {
                "timestamp": "2024-01-18T15:00:00Z",
                "value": 150.00,
                "currency": "USD",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    journey = _unwrap(create_resp)
    assert journey["user_id"] == "user-journey-1"
    assert len(journey["touchpoints"]) == 3
    journey_id = journey["journey_id"]

    # Invalid channel
    invalid_channel = await client.post(
        "/api/attribution/journeys",
        json={
            "user_id": "u1",
            "touchpoints": [
                {
                    "channel": "invalid_channel",
                    "campaign_id": campaign_id,
                    "timestamp": "2024-01-15T10:00:00Z",
                }
            ],
            "conversion": {
                "timestamp": "2024-01-16T10:00:00Z",
                "value": 10.0,
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert invalid_channel.status_code == 422

    # Conversion before last touchpoint
    invalid_time = await client.post(
        "/api/attribution/journeys",
        json={
            "user_id": "u1",
            "touchpoints": [
                {
                    "channel": "search_ads",
                    "campaign_id": campaign_id,
                    "timestamp": "2024-01-15T10:00:00Z",
                }
            ],
            "conversion": {
                "timestamp": "2024-01-14T10:00:00Z",
                "value": 10.0,
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert invalid_time.status_code == 422

    # Compute attribution
    compute = await client.post(
        f"/api/attribution/journeys/{journey_id}/compute",
        json={"models": ["first_touch", "last_touch", "linear", "shapley"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert compute.status_code == 200
    data = _unwrap(compute)
    assert data["journey_id"] == journey_id
    assert set(data["models"].keys()) == {
        "first_touch",
        "last_touch",
        "linear",
        "shapley",
    }

    # Missing journey
    missing = await client.post(
        f"/api/attribution/journeys/{uuid.uuid4()}/compute",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert missing.status_code == 404
