"""Agent API endpoints using real LLM function calling."""

import uuid
from typing import Any

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.bidding_agent import BiddingAgent
from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import get_current_active_user
from app.models import AgentConfig, User

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    goal: str
    max_steps: int = 10


class AgentConfigCreate(BaseModel):
    name: str
    goal: str
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    tools_enabled: list[str] | None = None
    max_steps: int = 10


@router.post("/configs", status_code=status.HTTP_201_CREATED)
async def create_config(
    request: AgentConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Create an agent configuration."""
    config = AgentConfig(
        user_id=current_user.id,
        name=request.name,
        goal=request.goal,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        tools_enabled=request.tools_enabled or [],
        max_steps=request.max_steps,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return {
        "id": str(config.id),
        "name": config.name,
        "goal": config.goal,
        "llm_provider": config.llm_provider,
        "llm_model": config.llm_model,
    }


@router.post("/{config_id}/run")
async def run_agent(
    config_id: uuid.UUID,
    request: AgentRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Run the agent with real LLM function calling and vector memory."""
    config = await db.get(AgentConfig, config_id)
    if config is None or config.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Config not found"
        )

    agent = BiddingAgent(db, current_user, config)
    return await agent.run(request.goal, max_steps=request.max_steps)
