"""Agent API endpoints for the ReAct bidding agent."""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status

from app.agent.bidding_agent import BiddingAgent
from app.schemas.agent import (
    AgentMemoryResponse,
    AgentRunRequest,
    AgentRunResponse,
    AgentStatus,
    AgentStrategy,
)

router = APIRouter(prefix="/api/agent", tags=["agent"])

# In-memory agent registry (per campaign)
_agents: Dict[str, BiddingAgent] = {}


def _get_or_create_agent(campaign_id: str) -> BiddingAgent:
    if campaign_id not in _agents:
        _agents[campaign_id] = BiddingAgent(campaign_id=campaign_id)
    return _agents[campaign_id]


@router.post("/{campaign_id}/run", response_model=AgentRunResponse)
async def run_agent(
    campaign_id: str,
    request: AgentRunRequest = AgentRunRequest(),
) -> AgentRunResponse:
    """Run the bidding agent ReAct loop for a campaign."""
    agent = _get_or_create_agent(campaign_id)

    performance_before = await _get_campaign_metrics(campaign_id)
    iterations = await agent.run_loop(max_iterations=request.max_iterations)
    performance_after = await _get_campaign_metrics(campaign_id)

    final_recommendation = "保持当前策略"
    if iterations:
        last_action = iterations[-1]["action"]
        final_recommendation = last_action["reasoning"]

    return AgentRunResponse(
        campaign_id=campaign_id,
        iterations=iterations,  # type: ignore[arg-type]
        final_recommendation=final_recommendation,
        metrics_before=performance_before,
        metrics_after=performance_after,
    )


@router.get("/{campaign_id}/memory", response_model=AgentMemoryResponse)
async def get_agent_memory(campaign_id: str) -> AgentMemoryResponse:
    """Get the recent decision memory of the agent."""
    agent = _get_or_create_agent(campaign_id)
    memory = agent.get_memory()
    return AgentMemoryResponse(
        campaign_id=campaign_id,
        memory=[
            {
                "timestamp": m["timestamp"],
                "action": m["action"],
                "parameters": m["parameters"],
                "result": m["result"],
                "expected_vs_actual": m.get("expected_vs_actual", {}),
                "learned": m["learned"],
            }
            for m in memory
        ],
    )


@router.get("/{campaign_id}/status", response_model=AgentStatus)
async def get_agent_status(campaign_id: str) -> AgentStatus:
    """Get the current status and strategy of the agent."""
    agent = _get_or_create_agent(campaign_id)
    status_data = agent.get_status()
    return AgentStatus(
        campaign_id=status_data["campaign_id"],
        strategy=AgentStrategy(**status_data["strategy"]),
        memory_size=status_data["memory_size"],
        current_state=status_data["current_state"],
        last_action=status_data["last_action"],
    )


@router.post("/{campaign_id}/strategy", response_model=AgentStatus)
async def update_agent_strategy(
    campaign_id: str,
    strategy: AgentStrategy,
) -> AgentStatus:
    """Update the agent's strategy targets."""
    agent = _get_or_create_agent(campaign_id)
    agent.update_strategy(strategy.model_dump())
    status_data = agent.get_status()
    return AgentStatus(
        campaign_id=status_data["campaign_id"],
        strategy=AgentStrategy(**status_data["strategy"]),
        memory_size=status_data["memory_size"],
        current_state=status_data["current_state"],
        last_action=status_data["last_action"],
    )


async def _get_campaign_metrics(campaign_id: str) -> Dict[str, Any]:
    """Lightweight helper to snapshot campaign metrics before/after a run."""
    from app.agent.tools import get_campaign_performance

    perf = await get_campaign_performance(campaign_id)
    return {
        "impressions": perf["impressions"],
        "clicks": perf["clicks"],
        "ctr": perf["ctr"],
        "spend": perf["spend"],
        "revenue": perf["revenue"],
        "roi": perf["roi"],
        "spend_ratio": perf["spend_ratio"],
    }
