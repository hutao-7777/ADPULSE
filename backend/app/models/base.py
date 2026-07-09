"""SQLAlchemy declarative base and timestamp defaults for AdPulse."""

from datetime import datetime, timezone

from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
