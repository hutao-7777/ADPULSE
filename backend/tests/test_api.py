"""Integration tests for AdPulse APIs."""

import uuid
from datetime import datetime, timedelta

import pytest

from app.core.seed import SEED_CAMPAIGNS


def _campaign_id(name: str) -> str:
    return str(SEED_CAMPAIGNS[name])


@pytest.mark.asyncio
async def test_single_auction(client):
    """Run a single RTB auction and verify the result shape."""
    payload = {
        "floor_price": 1.5,
        "user_segments": ["tech", "news"],
        "device_type": "mobile",
        "geo": "tier1",
        "ad_format": "banner_300x250",
        "context_category": "news",
        "auction_type": "second_price",
    }
    response = await client.post("/api/rtb/auction/single", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert "impression_id" in data
    assert "bids" in data
    assert "winner" in data
    assert "latency_ms" in data


@pytest.mark.asyncio
async def test_batch_auction(client):
    """Run a batch auction and verify aggregate stats."""
    payload = {
        "count": 100,
        "auction_type": "second_price",
        "campaign_config": {},
    }
    response = await client.post("/api/rtb/auction/batch", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["count"] == 100
    assert len(data["results"]) == 100
    stats = data["stats"]
    assert 0 <= stats["fill_rate"] <= 1
    assert stats["total_auctions"] == 100
    assert stats["filled_auctions"] <= stats["total_auctions"]


@pytest.mark.asyncio
async def test_abtest_flow(client):
    """Create, start, assign users, record events and fetch A/B test results."""
    campaign_id = _campaign_id("Summer Sale 2026")
    create_payload = {
        "name": "Integration Banner Test",
        "campaign_id": campaign_id,
        "metric_target": "ctr",
        "traffic_split": 1.0,
        "variants_config": [
            {"name": "control", "traffic_pct": 0.5},
            {"name": "red_cta", "traffic_pct": 0.5},
        ],
    }
    create_res = await client.post("/api/abtests", json=create_payload)
    assert create_res.status_code == 201
    test_data = create_res.json()["data"]
    test_id = test_data["id"]
    assert test_data["status"] == "draft"

    start_res = await client.post(f"/api/abtests/{test_id}/start")
    assert start_res.status_code == 200
    assert start_res.json()["data"]["status"] == "running"

    assign_res = await client.post(
        f"/api/abtests/{test_id}/assign", json={"user_id": "user-integration-001"}
    )
    assert assign_res.status_code == 200
    assignment = assign_res.json()["data"]
    assert assignment["in_experiment"] is True
    variant = assignment["variant"]
    assert variant in {"control", "red_cta"}

    event_base = {"variant": variant}
    for _ in range(100):
        impression_res = await client.post(
            f"/api/abtests/{test_id}/event",
            json={**event_base, "event_type": "impression"},
        )
        assert impression_res.status_code == 200
    for _ in range(10):
        click_res = await client.post(
            f"/api/abtests/{test_id}/event",
            json={**event_base, "event_type": "click"},
        )
        assert click_res.status_code == 200

    results_res = await client.get(f"/api/abtests/{test_id}/results")
    assert results_res.status_code == 200
    results_data = results_res.json()["data"]
    assert "test_info" in results_data
    assert "variants" in results_data
    assert "recommendation" in results_data
    assert any(v["name"] == variant for v in results_data["variants"])


@pytest.mark.asyncio
async def test_agent_loop(client):
    """Trigger the bidding agent and verify the ReAct decision chain."""
    campaign_id = _campaign_id("App Install Q3")
    response = await client.post(
        f"/api/agent/{campaign_id}/run",
        json={"max_iterations": 3},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["campaign_id"] == campaign_id
    assert "iterations" in data
    assert len(data["iterations"]) > 0
    assert "final_recommendation" in data
    assert "metrics_before" in data
    assert "metrics_after" in data

    first = data["iterations"][0]
    assert "thought" in first
    assert "action" in first
    assert "observation" in first
    assert "analysis" in first["thought"]
    assert "action" in first["action"]
    assert "reasoning" in first["action"]
    assert "learned" in first["observation"]


@pytest.mark.asyncio
async def test_attribution_flow(client):
    """Create journey touchpoints, record a conversion and calculate attribution."""
    campaign_id = _campaign_id("Summer Sale 2026")
    user_id = f"user-{uuid.uuid4().hex[:8]}"

    # Create touchpoints
    for idx, (channel, event_type) in enumerate(
        [
            ("display_view", "impression"),
            ("search", "impression"),
            ("display_click", "click"),
            ("social", "click"),
        ],
        start=1,
    ):
        payload = {
            "user_id": user_id,
            "campaign_id": campaign_id,
            "channel": channel,
            "event_type": event_type,
            "event_time": (datetime.utcnow() - timedelta(hours=5 - idx)).isoformat(),
        }
        res = await client.post("/api/attribution/journey", json=payload)
        assert res.status_code == 201, res.text

    # Record conversion
    conv_res = await client.post(
        "/api/attribution/conversion",
        json={
            "user_id": user_id,
            "campaign_id": campaign_id,
            "conversion_value": 100.0,
            "channel": "direct",
        },
    )
    assert conv_res.status_code == 201

    # Calculate attribution
    calc_res = await client.post(
        f"/api/attribution/calculate/{user_id}/{campaign_id}",
        json={"conversion_value": 100.0},
    )
    assert calc_res.status_code == 200
    calc_data = calc_res.json()["data"]
    assert "journey" in calc_data
    assert "models" in calc_data
    assert "model_credits" in calc_data
    assert "summary" in calc_data
    assert len(calc_data["journey"]) == 4

    # Model comparison aggregation
    comparison_res = await client.get("/api/attribution/model-comparison")
    assert comparison_res.status_code == 200
    comparison_data = comparison_res.json()["data"]
    assert "comparisons" in comparison_data
    assert len(comparison_data["comparisons"]) > 0


@pytest.mark.asyncio
async def test_traffic_assess(client):
    """Submit traffic metrics and retrieve quality score + alerts."""
    campaign_id = _campaign_id("App Install Q3")
    raw_metrics = {
        "impressions": 10000,
        "clicks": 250,
        "conversions": 20,
        "bounce_count": 80,
        "total_dwell_sec": 4200,
        "interaction_events": 1800,
        "unique_users": 240,
        "click_timestamps": [1, 2, 3, 4, 5],
        "ip_distribution": {"192.168.1.1": 120},
    }
    assess_res = await client.post(
        "/api/traffic/assess",
        json={"campaign_id": campaign_id, "raw_metrics": raw_metrics},
    )
    assert assess_res.status_code == 201
    score = assess_res.json()["data"]
    assert "quality_score" in score
    assert "grade" in score
    assert 0 <= score["quality_score"] <= 100
    assert score["grade"] in {"premium", "standard", "low", "fraud"}

    quality_res = await client.get(f"/api/traffic/quality/{campaign_id}")
    assert quality_res.status_code == 200
    assert quality_res.json()["data"]["campaign_id"] == campaign_id

    trend_res = await client.get(f"/api/traffic/trend/{campaign_id}")
    assert trend_res.status_code == 200
    assert "trend" in trend_res.json()["data"]

    alerts_res = await client.get(f"/api/traffic/alerts/{campaign_id}")
    assert alerts_res.status_code == 200
