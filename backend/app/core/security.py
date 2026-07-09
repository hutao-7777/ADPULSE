"""Security helpers: password hashing, JWT tokens, RBAC permission checks."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, cast

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import ApiKey, User
from app.models.base import utc_now

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return cast(bool, pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    """Hash a plain password with bcrypt."""
    return cast(str, pwd_context.hash(password))


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": subject,
        "exp": expire,
        "type": "access",
        "jti": secrets.token_urlsafe(16),
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return cast(
        str, jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    )


def create_refresh_token(
    subject: str,
    token_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, str]:
    """Create a JWT refresh token. Returns (token, token_hash)."""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.now(timezone.utc) + expires_delta
    token_id = token_id or secrets.token_urlsafe(32)
    to_encode = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
        "jti": token_id,
    }
    token = cast(
        str, jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    )
    token_hash = secrets.token_urlsafe(32)  # Store a hash in DB, not the raw token.
    return token, token_hash


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate a JWT token without verifying type."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return cast(dict[str, Any], payload)
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: authenticate via Bearer access token and return the user."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user = await db.get(User, user_uuid)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """Dependency: return user only if active."""
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


async def _check_permission(
    permission_code: str, user: User = Depends(get_current_active_user)
) -> User:
    """Check whether the active user has the required permission."""
    if user.is_superuser:
        return user

    # Direct permissions
    direct_codes = {p.code for p in user.permissions}
    if permission_code in direct_codes:
        return user

    # Role-based permissions
    role_codes: set[str] = set()
    for role in user.roles:
        role_codes.update(p.code for p in role.permissions)
    if permission_code in role_codes:
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Permission denied: {permission_code}",
    )


def require_permission(permission_code: str):
    """Return a dependency callable that checks the given permission code."""

    async def _wrapper(user: User = Depends(get_current_active_user)) -> User:
        return await _check_permission(permission_code, user)

    _wrapper.__name__ = f"require_permission_{permission_code.replace(':', '_')}"
    return _wrapper


async def validate_api_key(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    """Dependency: validate an API key and return the key record."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required",
        )

    prefix = api_key[:8] if len(api_key) >= 8 else api_key
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.key_prefix == prefix)
        .where(ApiKey.is_active == True)  # noqa: E712
    )
    candidates = list(result.scalars().all())
    key_record = next(
        (k for k in candidates if verify_password(api_key, k.key_hash)), None
    )

    if key_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if key_record.expires_at and key_record.expires_at < utc_now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired",
        )

    key_record.last_used_at = utc_now()
    await db.commit()
    return key_record
