"""Attribution API endpoints."""

import uuid
from datetime import datetime, timezone
from typing import Any, List

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import require_permission
from app.models import ConversionEvent, Touchpoint, User
from app.services.attribution_engine import AttributionEngine

router = APIRouter(prefix="/api/attribution", tags=["attribution"])
engine = AttributionEngine()

_ALLOWED_CHANNELS = {
    "search_ads",
    "social_media",
    "display",
    "email",
    "organic_search",
    "direct",
    "referral",
}
_ALLOWED_MODELS = {
    "first_touch",
    "last_touch",
    "linear",
    "time_decay",
    "shapley",
}


class AttributionRequest(BaseModel):
    conversion_id: uuid.UUID
    click_window_days: int = Field(default=7, ge=0)
    view_window_days: int = Field(default=1, ge=0)
    n_samples: int = Field(default=10_000, ge=100)


class JourneyRequest(BaseModel):
    user_id: str
    campaign_id: uuid.UUID


class TouchpointCreate(BaseModel):
    channel: str = Field(..., min_length=1)
    campaign_id: uuid.UUID
    timestamp: datetime
    cost: float = Field(default=0.0, ge=0)
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_channel(self) -> "TouchpointCreate":
        if self.channel not in _ALLOWED_CHANNELS:
            raise ValueError(f"Invalid channel: {self.channel}")
        return self


class ConversionCreate(BaseModel):
    timestamp: datetime
    value: float = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class JourneyCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    touchpoints: List[TouchpointCreate] = Field(..., min_length=1)
    conversion: ConversionCreate

    @model_validator(mode="after")
    def check_journey(self) -> "JourneyCreateRequest":
        points = sorted(self.touchpoints, key=lambda t: t.timestamp)
        if points[0].timestamp != self.touchpoints[0].timestamp:
            raise ValueError("Touchpoints must be ordered by timestamp ascending")
        if self.conversion.timestamp <= points[-1].timestamp:
            raise ValueError(
                "Conversion timestamp must be later than the last touchpoint"
            )
        return self


class TouchpointResponse(BaseModel):
    id: str
    channel: str
    campaign_id: str
    timestamp: datetime
    cost: float
    metadata: dict
    touchpoint_seq: int


class ConversionResponse(BaseModel):
    timestamp: datetime
    value: float
    currency: str


class JourneyResponse(BaseModel):
    journey_id: str
    user_id: str
    touchpoints: List[TouchpointResponse]
    conversion: ConversionResponse


class AttributionComputeRequest(BaseModel):
    models: List[str] = Field(default_factory=lambda: list(_ALLOWED_MODELS))
    time_decay_halflife_hours: float = Field(default=24.0, gt=0)

    @model_validator(mode="after")
    def check_models(self) -> "AttributionComputeRequest":
        invalid = set(self.models) - _ALLOWED_MODELS
        if invalid:
            raise ValueError(f"Invalid models: {', '.join(sorted(invalid))}")
        if not self.models:
            raise ValueError("At least one model must be requested")
        return self


class AttributionComputeResponse(BaseModel):
    journey_id: str
    models: dict[str, dict[str, float]]


def _to_naive_utc(dt: datetime) -> datetime:
    """Normalize a timezone-aware datetime to UTC and strip tzinfo."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


@router.post(
    "/journeys",
    response_model=JourneyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_journey(
    request: JourneyCreateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:write")),
) -> dict[str, Any]:
    """Create a user conversion journey with touchpoints for attribution."""
    conversion = ConversionEvent(
        id=uuid.uuid4(),
        user_id=request.user_id,
        campaign_id=request.touchpoints[-1].campaign_id,
        conversion_value=request.conversion.value,
        conversion_time=_to_naive_utc(request.conversion.timestamp),
        currency=request.conversion.currency.upper(),
    )
    db.add(conversion)
    await db.flush()

    for idx, tp_in in enumerate(request.touchpoints):
        touchpoint = Touchpoint(
            id=uuid.uuid4(),
            user_id=request.user_id,
            campaign_id=tp_in.campaign_id,
            touchpoint_seq=idx + 1,
            channel=tp_in.channel,
            event_type="click",
            event_time=_to_naive_utc(tp_in.timestamp),
            cost=tp_in.cost,
            metadata_=tp_in.metadata,
            conversion_event_id=conversion.id,
        )
        db.add(touchpoint)

    await db.commit()
    await db.refresh(conversion)

    touchpoints_result = await db.execute(
        select(Touchpoint)
        .where(Touchpoint.conversion_event_id == conversion.id)
        .order_by(Touchpoint.touchpoint_seq)
    )
    touchpoints = list(touchpoints_result.scalars().all())

    return _journey_to_response(conversion, touchpoints)


@router.post(
    "/journeys/{journey_id}/compute",
    response_model=AttributionComputeResponse,
)
async def compute_journey_attribution(
    journey_id: uuid.UUID,
    request: AttributionComputeRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:read")),
) -> dict[str, Any]:
    """Run attribution model comparison for a stored journey."""
    conversion = await db.get(ConversionEvent, journey_id)
    if conversion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found"
        )

    touchpoints_result = await db.execute(
        select(Touchpoint)
        .where(Touchpoint.conversion_event_id == journey_id)
        .order_by(Touchpoint.touchpoint_seq)
    )
    touchpoints = list(touchpoints_result.scalars().all())
    if not touchpoints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No touchpoints found for journey",
        )

    all_models = engine.compare_models(
        touchpoints,
        conversion.conversion_value,
        click_window_days=7,
        view_window_days=1,
        conversion_time=conversion.conversion_time,
        time_decay_halflife_hours=request.time_decay_halflife_hours,
    )
    selected = {m: all_models[m] for m in request.models if m in all_models}

    return {"journey_id": str(journey_id), "models": selected}


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


def _journey_to_response(
    conversion: ConversionEvent, touchpoints: List[Touchpoint]
) -> dict[str, Any]:
    return {
        "journey_id": str(conversion.id),
        "user_id": conversion.user_id,
        "touchpoints": [
            {
                "id": str(tp.id),
                "channel": tp.channel,
                "campaign_id": str(tp.campaign_id),
                "timestamp": tp.event_time,
                "cost": tp.cost,
                "metadata": tp.metadata_,
                "touchpoint_seq": tp.touchpoint_seq,
            }
            for tp in touchpoints
        ],
        "conversion": {
            "timestamp": conversion.conversion_time,
            "value": conversion.conversion_value,
            "currency": conversion.currency,
        },
    }
