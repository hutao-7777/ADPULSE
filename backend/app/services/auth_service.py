"""Authentication and authorization business logic."""

import secrets
import uuid
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    _hash_refresh_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models import ApiKey, RefreshToken, Role, User
from app.models.base import utc_now


class AuthService:
    """Service for login, token refresh, and API key management."""

    async def authenticate_user(
        self, db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """Verify email/password and return the user if valid."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def login(self, db: AsyncSession, email: str, password: str) -> dict:
        """Authenticate and issue access/refresh token pair."""
        user = await self.authenticate_user(db, email, password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        access_token = create_access_token(str(user.id))
        refresh_token, token_hash = create_refresh_token(str(user.id))

        refresh = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(refresh)
        await db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def refresh_access_token(self, db: AsyncSession, refresh_token: str) -> dict:
        """Validate a refresh token and issue a new access token."""
        payload = decode_token(refresh_token)
        if payload is None or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user = await db.get(User, user_uuid)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Look up the exact DB record bound to this refresh token hash.
        token_hash = _hash_refresh_token(refresh_token)
        result = await db.execute(
            select(RefreshToken)
            .where(RefreshToken.user_id == user.id)
            .where(RefreshToken.token_hash == token_hash)
            .where(RefreshToken.revoked_at.is_(None))
            .where(RefreshToken.expires_at > utc_now())
        )
        active_token = result.scalar_one_or_none()
        if active_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or expired",
            )

        new_access_token = create_access_token(str(user.id))
        return {"access_token": new_access_token, "token_type": "bearer"}

    async def revoke_refresh_token(
        self, db: AsyncSession, user_id: uuid.UUID, token_hash: str
    ) -> None:
        """Revoke a refresh token by hash."""
        result = await db.execute(
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.token_hash == token_hash)
        )
        token = result.scalar_one_or_none()
        if token:
            token.revoked_at = utc_now()
            await db.commit()

    async def create_api_key(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        name: str,
        scopes: list[str],
        rate_limit_rps: int = 100,
        expires_days: Optional[int] = None,
    ) -> tuple[ApiKey, str]:
        """Create a new API key. Returns the key record and the raw key (shown once)."""
        raw_key = f"adpulse_{secrets.token_urlsafe(32)}"
        prefix = raw_key[:8]
        key_hash = get_password_hash(raw_key)

        expires_at = None
        if expires_days:
            expires_at = utc_now() + timedelta(days=expires_days)

        api_key = ApiKey(
            user_id=user_id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
            rate_limit_rps=rate_limit_rps,
            expires_at=expires_at,
        )
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
        return api_key, raw_key

    async def revoke_api_key(
        self, db: AsyncSession, user_id: uuid.UUID, key_id: uuid.UUID
    ) -> bool:
        """Revoke an API key by id. Returns True if the key existed and was revoked."""
        key = await db.get(ApiKey, key_id)
        if key is None or key.user_id != user_id:
            return False
        key.is_active = False
        await db.commit()
        return True

    async def create_user(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role_names: Optional[list[str]] = None,
        is_superuser: bool = False,
    ) -> User:
        """Create a new user with optional roles."""
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            is_superuser=is_superuser,
        )
        db.add(user)
        await db.flush()

        if role_names:
            roles_result = await db.execute(
                select(Role).where(Role.name.in_(role_names))
            )
            roles = list(roles_result.scalars().all())
            user.roles.extend(roles)

        await db.commit()
        await db.refresh(user)
        return user
