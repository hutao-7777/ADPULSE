"""Production A/B testing API endpoints (v2)."""

import uuid
from typing import Any

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import require_permission
from app.models.models import Experiment, User
from app.services.ab_test_v2_engine import ABTestV2Engine

router = APIRouter(prefix="/api/v2/abtests", tags=["abtest-v2"])
engine = ABTestV2Engine()


class AssignmentRequest(BaseModel):
    user_id: str = Field(..., min_length=1)


class AssignmentResponse(BaseModel):
    experiment_id: str
    user_id: str
    variant_name: str
    in_experiment: bool


class MetricRecordRequest(BaseModel):
    user_id: str
    variant_name: str
    metric_name: str
    metric_value: float


@router.post("/{experiment_id}/assign", response_model=AssignmentResponse)
async def assign_user(
    experiment_id: uuid.UUID,
    request: AssignmentRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:read")),
) -> dict:
    """Assign a user to an experiment variant using consistent hashing."""
    result = await engine.assign_user(db, experiment_id, request.user_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found or not running",
        )
    variant, in_experiment = result
    return {
        "experiment_id": str(experiment_id),
        "user_id": request.user_id,
        "variant_name": variant.name,
        "in_experiment": in_experiment,
    }


@router.post("/{experiment_id}/metrics", status_code=status.HTTP_201_CREATED)
async def record_metric(
    experiment_id: uuid.UUID,
    request: MetricRecordRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:write")),
) -> dict:
    """Record a metric event for a variant."""
    await engine.record_metric(
        db,
        experiment_id,
        request.variant_name,
        request.user_id,
        request.metric_name,
        request.metric_value,
    )
    return {"status": "recorded"}


@router.get("/{experiment_id}/analysis")
async def analyze_experiment(
    experiment_id: uuid.UUID,
    metric_name: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:read")),
) -> dict[str, Any]:
    """Return t-test, Mann-Whitney U, power, MDE and confidence intervals."""
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        )
    return await engine.analyze(db, experiment_id, metric_name)
