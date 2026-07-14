"""AdUnit & Mediation 配置 API。"""

import uuid
from typing import List, Optional

from fastapi import Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import get_current_active_user
from app.models import AdNetwork, AdSource, AdUnit, User

router = APIRouter(prefix="/api/ad-units", tags=["ad_units"])


class AdUnitCreate(BaseModel):
    app_id: str
    name: str = Field(..., min_length=1, max_length=255)
    ad_format: str = Field(..., pattern="^(banner|interstitial|rewarded|native)$")
    width: Optional[int] = None
    height: Optional[int] = None


class AdUnitResponse(BaseModel):
    id: str
    app_id: str
    name: str
    ad_format: str
    width: Optional[int]
    height: Optional[int]
    status: str
    waterfall_config: dict
    bidding_config: dict
    created_at: str


class AdNetworkResponse(BaseModel):
    id: str
    name: str
    display_name: Optional[str]
    supports_bidding: bool
    status: str


class AdSourceCreate(BaseModel):
    ad_network_id: str
    instance_name: str = Field(..., min_length=1)
    ecpm: float = 0.0
    floor_price: float = 0.0
    priority: int = 0
    bidding_endpoint: Optional[str] = None
    credentials: dict = {}


class AdSourceResponse(BaseModel):
    id: str
    ad_unit_id: str
    ad_network_id: str
    instance_name: str
    ecpm: float
    floor_price: float
    priority: int
    bidding_endpoint: Optional[str]
    status: str


@router.get("", response_model=list[AdUnitResponse])
async def list_ad_units(
    app_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    stmt = select(AdUnit).order_by(AdUnit.created_at.desc())
    if app_id:
        stmt = stmt.where(AdUnit.app_id == uuid.UUID(app_id))
    result = await db.execute(stmt)
    return [
        AdUnitResponse(
            id=str(u.id), app_id=str(u.app_id), name=u.name,
            ad_format=u.ad_format, width=u.width, height=u.height,
            status=u.status, waterfall_config=u.waterfall_config,
            bidding_config=u.bidding_config, created_at=u.created_at.isoformat(),
        )
        for u in result.scalars().all()
    ]


@router.post("", response_model=AdUnitResponse, status_code=status.HTTP_201_CREATED)
async def create_ad_unit(
    body: AdUnitCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    au = AdUnit(
        app_id=uuid.UUID(body.app_id), name=body.name, ad_format=body.ad_format,
        width=body.width, height=body.height,
    )
    db.add(au)
    await db.commit()
    await db.refresh(au)
    return AdUnitResponse(
        id=str(au.id), app_id=str(au.app_id), name=au.name,
        ad_format=au.ad_format, width=au.width, height=au.height,
        status=au.status, waterfall_config=au.waterfall_config,
        bidding_config=au.bidding_config, created_at=au.created_at.isoformat(),
    )


@router.get("/ad-networks", response_model=list[AdNetworkResponse])
async def list_ad_networks(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(AdNetwork).where(AdNetwork.status == "active"))
    return [
        AdNetworkResponse(
            id=str(n.id), name=n.name, display_name=n.display_name,
            supports_bidding=n.supports_bidding, status=n.status,
        )
        for n in result.scalars().all()
    ]


@router.get("/{ad_unit_id}/sources", response_model=list[AdSourceResponse])
async def list_ad_sources(
    ad_unit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(AdSource).where(AdSource.ad_unit_id == ad_unit_id).order_by(AdSource.priority.asc())
    )
    return [
        AdSourceResponse(
            id=str(s.id), ad_unit_id=str(s.ad_unit_id), ad_network_id=str(s.ad_network_id),
            instance_name=s.instance_name, ecpm=s.ecpm, floor_price=s.floor_price,
            priority=s.priority, bidding_endpoint=s.bidding_endpoint, status=s.status,
        )
        for s in result.scalars().all()
    ]


@router.post("/{ad_unit_id}/sources", response_model=AdSourceResponse, status_code=status.HTTP_201_CREATED)
async def add_ad_source(
    ad_unit_id: uuid.UUID,
    body: AdSourceCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    src = AdSource(
        ad_unit_id=ad_unit_id, ad_network_id=uuid.UUID(body.ad_network_id),
        instance_name=body.instance_name, ecpm=body.ecpm, floor_price=body.floor_price,
        priority=body.priority, bidding_endpoint=body.bidding_endpoint,
        credentials=body.credentials,
    )
    db.add(src)
    await db.commit()
    await db.refresh(src)
    return AdSourceResponse(
        id=str(src.id), ad_unit_id=str(src.ad_unit_id),
        ad_network_id=str(src.ad_network_id), instance_name=src.instance_name,
        ecpm=src.ecpm, floor_price=src.floor_price, priority=src.priority,
        bidding_endpoint=src.bidding_endpoint, status=src.status,
    )


@router.patch("/{ad_unit_id}/waterfall")
async def update_waterfall(
    ad_unit_id: uuid.UUID,
    waterfall: List[str],
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    au = await db.get(AdUnit, ad_unit_id)
    if not au:
        from fastapi import HTTPException
        raise HTTPException(404, "AdUnit not found")
    au.waterfall_config["order"] = waterfall
    await db.commit()
    return {"status": "ok"}


@router.patch("/{ad_unit_id}/bidding-config")
async def update_bidding_config(
    ad_unit_id: uuid.UUID,
    config: dict,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    au = await db.get(AdUnit, ad_unit_id)
    if not au:
        from fastapi import HTTPException
        raise HTTPException(404, "AdUnit not found")
    au.bidding_config = config
    await db.commit()
    return {"status": "ok"}

@router.patch("/sources/{source_id}")
async def update_ad_source(
    source_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Update AdSource fields (ecpm, status, priority, etc.)."""
    src = await db.get(AdSource, source_id)
    if not src:
        from fastapi import HTTPException
        raise HTTPException(404, "AdSource not found")
    allowed = {"ecpm", "status", "priority", "instance_name", "floor_price"}
    for key, val in body.items():
        if key in allowed:
            setattr(src, key, val)
    await db.commit()
    return {"status": "ok", "id": str(source_id)}


@router.delete("/sources/{source_id}", status_code=204)
async def delete_ad_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    src = await db.get(AdSource, source_id)
    if src:
        await db.delete(src)
        await db.commit()
