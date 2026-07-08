"""A/B test API endpoints."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import ABTest, ABTestVariant
from app.schemas.abtest import (
    ABTestCreate,
    ABTestDetailResponse,
    ABTestResponse,
    ABTestResults,
    ABTestVariantResponse,
    AnomalyAlert,
    EventRecordRequest,
    UserAssignRequest,
    UserAssignResponse,
)
from app.services.ab_test_engine import ABTestEngine

router = APIRouter(prefix="/api/abtests", tags=["abtest"])

_engine = ABTestEngine()


def get_engine() -> ABTestEngine:
    return _engine


@router.post("", response_model=ABTestDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_ab_test(
    request: ABTestCreate,
    db: AsyncSession = Depends(get_db),
    engine: ABTestEngine = Depends(get_engine),
) -> ABTestDetailResponse:
    """Create a new A/B test with variants."""
    result = await engine.create_test(
        db=db,
        name=request.name,
        campaign_id=request.campaign_id,
        metric_target=request.metric_target,
        traffic_split=request.traffic_split,
        variants_config=[v.model_dump() for v in request.variants_config],
    )

    test = await db.get(ABTest, result["id"])
    variants_result = await db.execute(
        select(ABTestVariant).where(ABTestVariant.ab_test_id == test.id)
    )
    variants = variants_result.scalars().all()

    return ABTestDetailResponse(
        id=test.id,
        name=test.name,
        campaign_id=test.campaign_id,
        status=test.status,
        traffic_split=test.traffic_split,
        metric_target=test.metric_target,
        start_date=test.start_date,
        end_date=test.end_date,
        winner=test.winner,
        created_at=test.created_at,
        variants=[ABTestVariantResponse.model_validate(v) for v in variants],
    )


@router.get("", response_model=List[ABTestResponse])
async def list_ab_tests(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> List[ABTestResponse]:
    """List A/B tests, optionally filtered by status."""
    query = select(ABTest).order_by(ABTest.created_at.desc())
    if status_filter:
        query = query.where(ABTest.status == status_filter)
    result = await db.execute(query)
    tests = result.scalars().all()
    return [ABTestResponse.model_validate(t) for t in tests]


@router.get("/{test_id}", response_model=ABTestDetailResponse)
async def get_ab_test(
    test_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ABTestDetailResponse:
    """Get A/B test details including variants."""
    test = await db.get(ABTest, test_id)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")

    variants_result = await db.execute(
        select(ABTestVariant).where(ABTestVariant.ab_test_id == test.id)
    )
    variants = variants_result.scalars().all()

    return ABTestDetailResponse(
        id=test.id,
        name=test.name,
        campaign_id=test.campaign_id,
        status=test.status,
        traffic_split=test.traffic_split,
        metric_target=test.metric_target,
        start_date=test.start_date,
        end_date=test.end_date,
        winner=test.winner,
        created_at=test.created_at,
        variants=[ABTestVariantResponse.model_validate(v) for v in variants],
    )


@router.post("/{test_id}/start", response_model=ABTestResponse)
async def start_ab_test(
    test_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ABTestResponse:
    """Start an A/B test."""
    test = await db.get(ABTest, test_id)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    if test.status == "running":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test already running")

    from datetime import datetime

    test.status = "running"
    test.start_date = datetime.utcnow()
    await db.commit()
    await db.refresh(test)
    return ABTestResponse.model_validate(test)


@router.post("/{test_id}/stop", response_model=ABTestResponse)
async def stop_ab_test(
    test_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ABTestResponse:
    """Stop an A/B test."""
    test = await db.get(ABTest, test_id)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    if test.status != "running":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test is not running")

    from datetime import datetime

    test.status = "stopped"
    test.end_date = datetime.utcnow()
    await db.commit()
    await db.refresh(test)
    return ABTestResponse.model_validate(test)


@router.get("/{test_id}/results", response_model=ABTestResults)
async def get_ab_test_results(
    test_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    engine: ABTestEngine = Depends(get_engine),
) -> ABTestResults:
    """Get statistical results for an A/B test."""
    try:
        results = await engine.get_results(db, test_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ABTestResults(**results)


@router.post("/{test_id}/assign", response_model=UserAssignResponse)
async def assign_user_to_variant(
    test_id: uuid.UUID,
    request: UserAssignRequest,
    db: AsyncSession = Depends(get_db),
    engine: ABTestEngine = Depends(get_engine),
) -> UserAssignResponse:
    """Assign a user to a variant."""
    assignment = await engine.assign_user(db, test_id, request.user_id)
    if assignment is None:
        return UserAssignResponse(variant=None, in_experiment=False)
    variant_name, in_experiment = assignment
    return UserAssignResponse(variant=variant_name, in_experiment=in_experiment)


@router.post("/{test_id}/event")
async def record_ab_test_event(
    test_id: uuid.UUID,
    request: EventRecordRequest,
    db: AsyncSession = Depends(get_db),
    engine: ABTestEngine = Depends(get_engine),
) -> dict:
    """Record an event for a variant."""
    try:
        await engine.record_event(
            db, test_id, request.variant, request.event_type, request.revenue
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return {"status": "recorded"}


@router.get("/{test_id}/anomaly", response_model=Optional[AnomalyAlert])
async def check_ab_test_anomaly(
    test_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    engine: ABTestEngine = Depends(get_engine),
) -> Optional[AnomalyAlert]:
    """Check for metric anomalies in an A/B test."""
    try:
        alert = await engine.check_anomaly(db, test_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if alert is None:
        return None
    return AnomalyAlert(**alert)
