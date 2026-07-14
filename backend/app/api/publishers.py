"""Publisher & App 管理 API。"""

import uuid
from typing import Optional

from fastapi import Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import get_current_active_user
from app.models import App, Publisher, User

router = APIRouter(prefix="/api/publishers", tags=["publishers"])


class PublisherCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    company: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class PublisherResponse(BaseModel):
    id: str
    name: str
    company: Optional[str]
    email: Optional[str]
    website: Optional[str]
    status: str
    created_at: str


class AppCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    platform: str = Field(..., pattern="^(web|android|ios)$")
    domain: Optional[str] = None
    package_name: Optional[str] = None
    app_store_id: Optional[str] = None


class AppResponse(BaseModel):
    id: str
    publisher_id: str
    name: str
    platform: str
    domain: Optional[str]
    package_name: Optional[str]
    app_store_id: Optional[str]
    status: str
    created_at: str


@router.get("", response_model=list[PublisherResponse])
async def list_publishers(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """List all publishers."""
    result = await db.execute(
        select(Publisher)
        .where(Publisher.status == "active")
        .order_by(Publisher.created_at.desc())
    )
    return [
        PublisherResponse(
            id=str(p.id),
            name=p.name,
            company=p.company,
            email=p.email,
            website=p.website,
            status=p.status,
            created_at=p.created_at.isoformat(),
        )
        for p in result.scalars().all()
    ]


@router.post("", response_model=PublisherResponse, status_code=status.HTTP_201_CREATED)
async def create_publisher(
    body: PublisherCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new publisher owned by the current user."""
    pub = Publisher(
        owner_id=current_user.id,
        name=body.name,
        company=body.company,
        email=body.email,
        website=body.website,
    )
    db.add(pub)
    await db.commit()
    await db.refresh(pub)
    return PublisherResponse(
        id=str(pub.id),
        name=pub.name,
        company=pub.company,
        email=pub.email,
        website=pub.website,
        status=pub.status,
        created_at=pub.created_at.isoformat(),
    )


@router.get("/{publisher_id}/apps", response_model=list[AppResponse])
async def list_apps(
    publisher_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """List apps under a publisher."""
    result = await db.execute(
        select(App)
        .where(App.publisher_id == publisher_id, App.status == "active")
        .order_by(App.created_at.desc())
    )
    return [
        AppResponse(
            id=str(a.id),
            publisher_id=str(a.publisher_id),
            name=a.name,
            platform=a.platform,
            domain=a.domain,
            package_name=a.package_name,
            app_store_id=a.app_store_id,
            status=a.status,
            created_at=a.created_at.isoformat(),
        )
        for a in result.scalars().all()
    ]


@router.post(
    "/{publisher_id}/apps",
    response_model=AppResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_app(
    publisher_id: uuid.UUID,
    body: AppCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Create a new app under a publisher."""
    app = App(
        publisher_id=publisher_id,
        name=body.name,
        platform=body.platform,
        domain=body.domain,
        package_name=body.package_name,
        app_store_id=body.app_store_id,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return AppResponse(
        id=str(app.id),
        publisher_id=str(app.publisher_id),
        name=app.name,
        platform=app.platform,
        domain=app.domain,
        package_name=app.package_name,
        app_store_id=app.app_store_id,
        status=app.status,
        created_at=app.created_at.isoformat(),
    )
