"""Production attribution API endpoints (v2)."""

import uuid
from typing import Any

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import require_permission
from app.models.models import ConversionEvent, User
from app.services.attribution_v2_engine import AttributionV2Engine

router = APIRouter(prefix="/api/v2/attribution", tags=["attribution-v2"])
engine = AttributionV2Engine()


class AttributionRequest(BaseModel):
    conversion_id: uuid.UUID
    click_window_days: int = Field(default=7, ge=0)
    view_window_days: int = Field(default=1, ge=0)
    n_samples: int = Field(default=10_000, ge=100)


class JourneyRequest(BaseModel):
    user_id: str
    campaign_id: uuid.UUID


@router.post("/calculate")
async def calculate_attribution(
    request: AttributionRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:read")),
) -> dict[str, Any]:
    """Calculate Shapley attribution for a conversion event."""
    conversion = await db.get(ConversionEvent, request.conversion_id)
    if conversion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversion not found"
        )
    return await engine.calculate_for_conversion(
        db,
        request.conversion_id,
        request.click_window_days,
        request.view_window_days,
        request.n_samples,
    )


@router.post("/compare-models")
async def compare_attribution_models(
    request: JourneyRequest,
    click_window_days: int = 7,
    view_window_days: int = 1,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:read")),
) -> dict[str, Any]:
    """Compare first-touch, last-touch, linear, time-decay and Shapley models."""
    touchpoints = await engine.build_user_journey(
        db, request.user_id, request.campaign_id
    )
    if not touchpoints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No touchpoint journey found",
        )
    comparison = engine.compare_models(
        touchpoints, 1.0, click_window_days, view_window_days
    )
    return {
        "user_id": request.user_id,
        "campaign_id": str(request.campaign_id),
        "models": comparison,
    }
