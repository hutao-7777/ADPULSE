"""Authentication API endpoints."""

import uuid

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import get_current_active_user, validate_api_key
from app.models import ApiKey, User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])
auth_service = AuthService()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str]
    rate_limit_rps: int = 100
    expires_days: int | None = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    key: str | None = None
    scopes: list[str]
    rate_limit_rps: int
    is_active: bool
    expires_at: str | None
    created_at: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Authenticate with email/password and obtain JWT access/refresh tokens."""
    return await auth_service.login(db, request.email, request.password)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    request: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Exchange a valid refresh token for a new access token."""
    return await auth_service.refresh_access_token(db, request.refresh_token)


@router.get("/me", response_model=dict)
async def read_me(current_user: User = Depends(get_current_active_user)) -> dict:
    """Return the currently authenticated user's profile."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
    }


@router.post(
    "/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    request: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Create a new API key for DSP/programmatic access."""
    key_record, raw_key = await auth_service.create_api_key(
        db,
        current_user.id,
        request.name,
        request.scopes,
        request.rate_limit_rps,
        request.expires_days,
    )
    return {
        "id": str(key_record.id),
        "name": key_record.name,
        "key_prefix": key_record.key_prefix,
        "key": raw_key,  # Returned only once.
        "scopes": key_record.scopes,
        "rate_limit_rps": key_record.rate_limit_rps,
        "is_active": key_record.is_active,
        "expires_at": (
            key_record.expires_at.isoformat() if key_record.expires_at else None
        ),
        "created_at": key_record.created_at.isoformat(),
    }


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict]:
    """List API keys owned by the current user."""
    result = await db.execute(select(ApiKey).where(ApiKey.user_id == current_user.id))
    keys = list(result.scalars().all())
    return [
        {
            "id": str(k.id),
            "name": k.name,
            "key_prefix": k.key_prefix,
            "scopes": k.scopes,
            "rate_limit_rps": k.rate_limit_rps,
            "is_active": k.is_active,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "created_at": k.created_at.isoformat(),
        }
        for k in keys
    ]


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register a new user (only when public registration is enabled)."""
    if not settings.ENABLE_PUBLIC_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is disabled",
        )
    user = await auth_service.create_user(
        db,
        email=request.email,
        password=request.password,
    )
    return {"id": str(user.id), "email": user.email}


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Revoke an API key owned by the current user."""
    revoked = await auth_service.revoke_api_key(db, current_user.id, key_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )


@router.get("/api-key-check")
async def api_key_check(key_record: ApiKey = Depends(validate_api_key)) -> dict:
    """Validate an API key (used by DSP integrations)."""
    return {"valid": True, "scopes": key_record.scopes}
