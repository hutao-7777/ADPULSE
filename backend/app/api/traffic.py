"""Traffic quality and fraud alert API endpoints."""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import FraudAlert, TrafficQualityScore
from app.schemas.traffic import (
    FraudAlertResponse,
    QualityTrendResponse,
    TrafficAssessRequest,
    TrafficQualityResponse,
)
from app.services.traffic_quality_engine import TrafficQualityEngine

router = APIRouter(prefix="/api/traffic", tags=["traffic"])

_engine = TrafficQualityEngine()


def _as_uuid(value: str) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _get_engine() -> TrafficQualityEngine:
    return _engine


@router.post("/assess", response_model=TrafficQualityResponse, status_code=status.HTTP_201_CREATED)
async def assess_traffic(
    request: TrafficAssessRequest,
    db: AsyncSession = Depends(get_db),
) -> TrafficQualityScore:
    """Submit raw traffic metrics and receive a quality assessment."""
    campaign_uuid = _as_uuid(request.campaign_id)
    if campaign_uuid is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid campaign_id")

    date = request.date or datetime.utcnow()
    date = date.replace(hour=0, minute=0, second=0, microsecond=0)

    raw_metrics = request.raw_metrics or {}
    if request.geo:
        raw_metrics["geo"] = request.geo
    if request.device_type:
        raw_metrics["device_type"] = request.device_type

    score = await _engine.save_assessment(db, campaign_uuid, date, raw_metrics)
    return score


@router.get("/quality/{campaign_id}", response_model=TrafficQualityResponse)
async def get_latest_quality(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
) -> TrafficQualityScore:
    """Return the most recent quality score for a campaign."""
    campaign_uuid = _as_uuid(campaign_id)
    if campaign_uuid is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid campaign_id")

    result = await db.execute(
        select(TrafficQualityScore)
        .where(TrafficQualityScore.campaign_id == campaign_uuid)
        .order_by(TrafficQualityScore.date.desc())
    )
    score = result.scalar_one_or_none()
    if score is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No quality score found")
    return score


@router.get("/trend/{campaign_id}", response_model=QualityTrendResponse)
async def get_quality_trend(
    campaign_id: str,
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    engine: TrafficQualityEngine = Depends(_get_engine),
) -> Dict[str, List[dict]]:
    """Return daily traffic quality trend for a campaign."""
    campaign_uuid = _as_uuid(campaign_id)
    if campaign_uuid is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid campaign_id")

    trend = await engine.get_campaign_quality_trend(db, campaign_uuid, days)
    return {"trend": trend}


@router.get("/alerts/{campaign_id}", response_model=List[FraudAlertResponse])
async def get_fraud_alerts(
    campaign_id: str,
    status_filter: Optional[str] = "open",
    db: AsyncSession = Depends(get_db),
) -> List[FraudAlert]:
    """List fraud alerts for a campaign, optionally filtered by status."""
    campaign_uuid = _as_uuid(campaign_id)
    if campaign_uuid is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid campaign_id")

    query = (
        select(FraudAlert)
        .where(FraudAlert.campaign_id == campaign_uuid)
        .order_by(FraudAlert.detected_at.desc())
    )
    if status_filter:
        query = query.where(FraudAlert.status == status_filter)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/alerts/{alert_id}/resolve", response_model=FraudAlertResponse)
async def resolve_fraud_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
) -> FraudAlert:
    """Mark a fraud alert as resolved."""
    alert_uuid = _as_uuid(alert_id)
    if alert_uuid is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid alert_id")

    alert = await db.get(FraudAlert, alert_uuid)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.status = "resolved"
    await db.commit()
    await db.refresh(alert)
    return alert
