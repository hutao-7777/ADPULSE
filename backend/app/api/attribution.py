"""Attribution API endpoints for multi-touch user journey analysis."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, status
from app.core.response import APIRouter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import AttributionResult, ConversionEvent, Touchpoint
from app.schemas.attribution import (
    AttributionCalculateRequest,
    AttributionCompareResponse,
    ConversionCreate,
    ModelComparisonResponse,
    TouchpointCreate,
    TouchpointResponse,
)
from app.services.attribution_engine import AttributionEngine

router = APIRouter(prefix="/api/attribution", tags=["attribution"])

_engine = AttributionEngine()


def _as_uuid(value: str) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _get_engine() -> AttributionEngine:
    return _engine


@router.post("/journey", response_model=TouchpointResponse, status_code=status.HTTP_201_CREATED)
async def create_touchpoint(
    request: TouchpointCreate,
    db: AsyncSession = Depends(get_db),
) -> Touchpoint:
    """Create a new touchpoint in a user's journey."""
    campaign_uuid = _as_uuid(request.campaign_id)
    if campaign_uuid is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid campaign_id")

    # Compute next sequence number
    count_result = await db.execute(
        select(func.count(Touchpoint.id))
        .where(Touchpoint.user_id == request.user_id)
        .where(Touchpoint.campaign_id == campaign_uuid)
    )
    next_seq = (count_result.scalar() or 0) + 1

    conversion_event_id: Optional[uuid.UUID] = None
    event_time = request.event_time or datetime.utcnow()

    # If this touchpoint represents a conversion, also record a conversion event
    if request.event_type == "conversion":
        conversion = ConversionEvent(
            user_id=request.user_id,
            campaign_id=campaign_uuid,
            conversion_value=request.conversion_value or 1.0,
            conversion_time=event_time,
            channel=request.channel,
        )
        db.add(conversion)
        await db.flush()
        conversion_event_id = conversion.id

    touchpoint = Touchpoint(
        user_id=request.user_id,
        campaign_id=campaign_uuid,
        touchpoint_seq=next_seq,
        channel=request.channel,
        event_type=request.event_type,
        event_time=event_time,
        conversion_event_id=conversion_event_id,
    )
    db.add(touchpoint)
    await db.commit()
    await db.refresh(touchpoint)
    return touchpoint


@router.get("/journey/{user_id}/{campaign_id}", response_model=List[TouchpointResponse])
async def get_user_journey(
    user_id: str,
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[Touchpoint]:
    """Return the full touchpoint journey for a user in a campaign."""
    campaign_uuid = _as_uuid(campaign_id)
    if campaign_uuid is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid campaign_id")

    result = await db.execute(
        select(Touchpoint)
        .where(Touchpoint.user_id == user_id)
        .where(Touchpoint.campaign_id == campaign_uuid)
        .order_by(Touchpoint.touchpoint_seq.asc(), Touchpoint.event_time.asc())
    )
    return list(result.scalars().all())


@router.post("/conversion", status_code=status.HTTP_201_CREATED)
async def record_conversion(
    request: ConversionCreate,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Record a conversion event and link recent unassigned touchpoints."""
    campaign_uuid = _as_uuid(request.campaign_id)
    if campaign_uuid is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid campaign_id")

    creative_uuid = _as_uuid(request.creative_id) if request.creative_id else None

    conversion = ConversionEvent(
        user_id=request.user_id,
        campaign_id=campaign_uuid,
        conversion_value=request.conversion_value,
        conversion_time=request.conversion_time or datetime.utcnow(),
        channel=request.channel,
        device_type=request.device_type,
        geo=request.geo,
        creative_id=creative_uuid,
    )
    db.add(conversion)
    await db.flush()

    # Link recent unassigned touchpoints to this conversion
    await db.execute(
        Touchpoint.__table__.update()
        .where(Touchpoint.user_id == request.user_id)
        .where(Touchpoint.campaign_id == campaign_uuid)
        .where(Touchpoint.conversion_event_id.is_(None))
        .where(Touchpoint.event_time <= conversion.conversion_time)
        .values({Touchpoint.conversion_event_id: conversion.id})
    )
    await db.commit()
    await db.refresh(conversion)

    return {"id": str(conversion.id), "status": "recorded"}


@router.post("/calculate/{user_id}/{campaign_id}", response_model=AttributionCompareResponse)
async def calculate_attribution(
    user_id: str,
    campaign_id: str,
    request: AttributionCalculateRequest,
    db: AsyncSession = Depends(get_db),
    engine: AttributionEngine = Depends(_get_engine),
) -> Dict[str, Any]:
    """Calculate attribution models for the latest conversion of a user/campaign."""
    campaign_uuid = _as_uuid(campaign_id)
    if campaign_uuid is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid campaign_id")

    # Use the most recent conversion event for this user/campaign
    conversion_result = await db.execute(
        select(ConversionEvent)
        .where(ConversionEvent.user_id == user_id)
        .where(ConversionEvent.campaign_id == campaign_uuid)
        .order_by(ConversionEvent.conversion_time.desc())
    )
    conversion = conversion_result.scalar_one_or_none()

    if conversion is None:
        # Create a synthetic conversion if none exists so the API remains usable
        conversion = ConversionEvent(
            user_id=user_id,
            campaign_id=campaign_uuid,
            conversion_value=request.conversion_value,
            conversion_time=datetime.utcnow(),
            channel="direct",
        )
        db.add(conversion)
        await db.flush()

    journey = await engine.build_user_journey(db, user_id, campaign_uuid)
    if not journey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No touchpoint journey found for this user and campaign",
        )

    comparison = engine.compare_models(
        journey,
        request.conversion_value,
        conversion_time=conversion.conversion_time,
        models=request.models,
    )

    await engine.persist_results(db, conversion.id, comparison["model_credits"])
    return comparison


@router.get("/model-comparison", response_model=ModelComparisonResponse)
async def get_model_comparison(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, List[Dict[str, Any]]]:
    """Aggregate attribution credits across all recorded conversion events."""
    result = await db.execute(select(AttributionResult))
    records = result.scalars().all()

    if not records:
        return {"comparisons": []}

    totals: Dict[str, Dict[str, List[float]]] = {}
    for record in records:
        model_totals = totals.setdefault(record.model_type, {})
        for channel, credit in record.channel_credits.items():
            model_totals.setdefault(channel, []).append(float(credit))

    comparisons = []
    for model_type, channel_values in totals.items():
        channel_credits = [
            {"channel": ch, "avg_credit": round(sum(values) / len(values), 4)}
            for ch, values in channel_values.items()
        ]
        comparisons.append({"model_type": model_type, "channel_credits": channel_credits})

    return {"comparisons": comparisons}
