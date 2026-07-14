"""Event Ingestion API - SDK event tracking entrypoint."""

import uuid
from typing import Optional

from fastapi import Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.models import ClickEvent, ConversionEvent, ImpressionEvent

router = APIRouter(prefix="/v1", tags=["events"])


class ImpressionPayload(BaseModel):
    impression_id: str = Field(..., min_length=1)
    ad_unit_id: Optional[str] = None
    device_id: Optional[str] = None
    network_name: Optional[str] = None
    revenue: float = 0.0
    currency: str = "USD"
    viewability_pct: Optional[float] = None
    viewability_ms: Optional[float] = None
    metadata: dict = {}


class ClickPayload(BaseModel):
    click_id: str = Field(..., min_length=1)
    impression_id: Optional[str] = None
    ad_unit_id: Optional[str] = None
    device_id: Optional[str] = None
    network_name: Optional[str] = None
    redirect_url: Optional[str] = None
    metadata: dict = {}


class ConversionPayload(BaseModel):
    event_type: str = Field(..., min_length=1)
    device_id: Optional[str] = None
    click_id: Optional[str] = None
    impression_id: Optional[str] = None
    event_value: float = 0.0
    currency: str = "USD"
    metadata: dict = {}


@router.post("/events/impression", status_code=status.HTTP_204_NO_CONTENT)
async def track_impression(body: ImpressionPayload, request: Request, db: AsyncSession = Depends(get_db)):
    event = ImpressionEvent(
        impression_id=body.impression_id,
        ad_unit_id=uuid.UUID(body.ad_unit_id) if body.ad_unit_id else None,
        device_id=body.device_id,
        network_name=body.network_name,
        revenue=body.revenue,
        currency=body.currency,
        viewability_pct=body.viewability_pct,
        viewability_ms=body.viewability_ms,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
        metadata_=body.metadata,
    )
    db.add(event)
    await db.commit()


@router.post("/events/click", status_code=status.HTTP_204_NO_CONTENT)
async def track_click(body: ClickPayload, db: AsyncSession = Depends(get_db)):
    event = ClickEvent(
        click_id=body.click_id,
        impression_id=body.impression_id,
        ad_unit_id=uuid.UUID(body.ad_unit_id) if body.ad_unit_id else None,
        device_id=body.device_id,
        network_name=body.network_name,
        redirect_url=body.redirect_url,
        metadata_=body.metadata,
    )
    db.add(event)
    await db.commit()


@router.post("/events/conversion", status_code=status.HTTP_204_NO_CONTENT)
async def track_conversion(body: ConversionPayload, db: AsyncSession = Depends(get_db)):
    event = ConversionEvent(
        event_type=body.event_type,
        device_id=body.device_id,
        click_id=body.click_id,
        impression_id=body.impression_id,
        event_value=body.event_value,
        currency=body.currency,
        metadata_=body.metadata,
    )
    db.add(event)
    await db.commit()


@router.post("/events/batch", status_code=status.HTTP_204_NO_CONTENT)
async def track_batch(events: list[dict], db: AsyncSession = Depends(get_db)):
    for ev in events:
        etype = ev.get("event")
        if etype == "impression":
            ie = ImpressionEvent(
                impression_id=ev.get("impression_id", ""),
                ad_unit_id=uuid.UUID(ev["ad_unit_id"]) if ev.get("ad_unit_id") else None,
                device_id=ev.get("device_id"),
                network_name=ev.get("network_name"),
                revenue=ev.get("revenue", 0.0),
                currency=ev.get("currency", "USD"),
            )
            db.add(ie)
        elif etype == "click":
            ce = ClickEvent(
                click_id=ev.get("click_id", ""),
                impression_id=ev.get("impression_id"),
                ad_unit_id=uuid.UUID(ev["ad_unit_id"]) if ev.get("ad_unit_id") else None,
                device_id=ev.get("device_id"),
                network_name=ev.get("network_name"),
                redirect_url=ev.get("redirect_url"),
            )
            db.add(ce)
        elif etype == "conversion":
            cve = ConversionEvent(
                event_type=ev.get("event_type", "unknown"),
                device_id=ev.get("device_id"),
                click_id=ev.get("click_id"),
                event_value=ev.get("value", 0.0),
                currency=ev.get("currency", "USD"),
                metadata_=ev.get("metadata", {}),
            )
            db.add(cve)
    await db.commit()
