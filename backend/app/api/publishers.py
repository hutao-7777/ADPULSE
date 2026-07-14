"""Publisher & App 管理 API。"""

import uuid
from typing import Optional

from fastapi import Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import get_current_active_user, require_permission
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
