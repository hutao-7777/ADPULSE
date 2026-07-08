"""Pydantic schemas for the bidding agent."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentStrategy(BaseModel):
    target_cpa: float = Field(..., gt=0)
    max_cpm: float = Field(..., gt=0)
    daily_budget: float = Field(..., gt=0)


class AgentStatus(BaseModel):
    campaign_id: str
    strategy: AgentStrategy
    memory_size: int
    current_state: str
    last_action: Optional[str] = None


class ThoughtStep(BaseModel):
    analysis: str
    data: Dict[str, Any]


class ActionStep(BaseModel):
    action: str
    parameters: Dict[str, Any]
    reasoning: str


class ObservationStep(BaseModel):
    observation: str
    expected_vs_actual: Dict[str, Any]
    learned: str


class AgentIteration(BaseModel):
    iteration: int
    thought: ThoughtStep
    action: ActionStep
    observation: ObservationStep


class AgentRunRequest(BaseModel):
    max_iterations: int = Field(default=3, ge=1, le=10)


class AgentRunResponse(BaseModel):
    campaign_id: str
    iterations: List[AgentIteration]
    final_recommendation: str
    metrics_before: Dict[str, Any]
    metrics_after: Dict[str, Any]


class AgentMemoryEntry(BaseModel):
    timestamp: str
    action: str
    parameters: Dict[str, Any]
    result: Dict[str, Any]
    expected_vs_actual: Dict[str, Any] = Field(default_factory=dict)
    learned: str


class AgentMemoryResponse(BaseModel):
    campaign_id: str
    memory: List[AgentMemoryEntry]
