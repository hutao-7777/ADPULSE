"""Traffic quality and fraud alert API."""

import uuid


from fastapi import Depends, Query

from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession


from app.core.database import get_db

from app.core.response import APIRouter

from app.core.security import get_current_active_user

from app.models import User

from app.services.traffic_quality_engine import TrafficQualityEngine

router = APIRouter(prefix="/api/traffic", tags=["traffic"])

engine = TrafficQualityEngine()


class QualityResponse(BaseModel):

    ad_unit_id: str

    date: str

    impressions: int

    clicks: int

    conversions: int

    quality_score: float

    grade: str

    ctr_score: float

    cvr_score: float

    bounce_score: float

    dwell_score: float

    interaction_score: float

    flags: list


class TrendPoint(BaseModel):

    date: str

    quality_score: float

    grade: str

    ctr_score: float


class TrendResponse(BaseModel):

    points: list[TrendPoint]


class AlertResponse(BaseModel):

    id: str

    alert_type: str

    severity: str

    description: str

    detected_at: str

    status: str


@router.post("/assess/{ad_unit_id}", response_model=QualityResponse)
async def assess_traffic(
    ad_unit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Assess traffic quality for an ad unit based on recent event data."""

    result = await engine.assess_from_events(db, ad_unit_id)

    return QualityResponse(**result)


@router.get("/ad-unit/{ad_unit_id}/trend", response_model=TrendResponse)
async def get_quality_trend(
    ad_unit_id: uuid.UUID,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Get quality score trend for an ad unit."""

    points = await engine.get_trend(db, ad_unit_id, days)

    return TrendResponse(points=[TrendPoint(**p) for p in points])


@router.get("/ad-unit/{ad_unit_id}/alerts", response_model=list[AlertResponse])
async def get_alerts(
    ad_unit_id: uuid.UUID,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Get fraud alerts for an ad unit."""

    alerts = await engine.get_alerts(db, ad_unit_id, days)

    return [AlertResponse(**a) for a in alerts]


@router.post("/ad-unit/{ad_unit_id}/check", response_model=QualityResponse)
async def check_and_alert(
    ad_unit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Assess traffic quality and auto-generate fraud alerts."""

    await engine.generate_alerts(db, ad_unit_id)

    return await assess_traffic(ad_unit_id, db, _user)
