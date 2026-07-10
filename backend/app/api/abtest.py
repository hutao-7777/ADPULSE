"""A/B testing API endpoints."""

import uuid
from datetime import datetime
from typing import Any, List, Optional

from fastapi import Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import require_permission
from app.models import Experiment, ExperimentDailyStat, ExperimentMetric, User, Variant
from app.models.base import utc_now
from app.services.ab_test_engine import ABTestEngine
from app.services.experiment_simulator import experiment_simulator

router = APIRouter(prefix="/api/abtests", tags=["abtest"])
engine = ABTestEngine()


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


class ExperimentVariantCreate(BaseModel):
    name: str = Field(..., min_length=1)
    config: dict = Field(default_factory=dict)
    traffic_allocation: int = Field(..., ge=0, le=100)


class ExperimentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None
    campaign_id: uuid.UUID | None = None
    traffic_split: int = Field(..., ge=1, le=99)
    variants: List[ExperimentVariantCreate] = Field(..., min_length=2)
    success_metric: str = Field(..., pattern="^(conversion_rate|ctr|revenue|roi)$")
    min_sample_size: int | None = Field(None, ge=1)
    max_duration_days: int | None = Field(None, ge=1)

    @model_validator(mode="after")
    def check_variants(self) -> "ExperimentCreateRequest":
        names = [v.name for v in self.variants]
        if len(names) != len(set(names)):
            raise ValueError("Variant names must be unique")
        total = sum(v.traffic_allocation for v in self.variants)
        if total != 100:
            raise ValueError("Variant traffic allocations must sum to 100")
        return self


class ExperimentVariantResponse(BaseModel):
    id: str
    name: str
    config: dict
    traffic_allocation: int
    created_at: datetime
    data_source: Optional[str] = None


class ExperimentResponse(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    traffic_split: int
    success_metric: str
    min_sample_size: int | None
    max_duration_days: int | None
    start_date: datetime | None
    end_date: datetime | None
    created_at: datetime
    updated_at: datetime
    variants: List[ExperimentVariantResponse]
    data_source: Optional[str] = None


class ExperimentStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(draft|running|paused|stopped)$")


class ExperimentEventRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    event_type: str = Field(..., pattern="^(exposure|conversion)$")
    variant_name: str = Field(..., min_length=1)
    metadata: dict = Field(default_factory=dict)


class ExperimentEventResponse(BaseModel):
    status: str


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    request: ExperimentCreateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:write")),
) -> dict[str, Any]:
    """Create a new A/B experiment with variants and simulated historical data."""
    experiment = Experiment(
        id=uuid.uuid4(),
        campaign_id=request.campaign_id,
        name=request.name,
        description=request.description,
        status="draft",
        metric_name=request.success_metric,
        traffic_allocation=request.traffic_split,
        min_sample_size=request.min_sample_size,
        max_duration_days=request.max_duration_days,
    )
    db.add(experiment)
    await db.flush()

    for variant_in in request.variants:
        variant = Variant(
            id=uuid.uuid4(),
            experiment_id=experiment.id,
            name=variant_in.name,
            traffic_pct=variant_in.traffic_allocation / 100.0,
            config=variant_in.config,
        )
        db.add(variant)

    await db.commit()

    # Generate historical mock data from start_date up to today.
    stmt = select(Variant).where(Variant.experiment_id == experiment.id)
    result = await db.execute(stmt)
    variants_list = list(result.scalars().all())

    start = experiment.start_date or utc_now()
    if isinstance(start, datetime):
        start = start.date()
    await experiment_simulator.generate_history(experiment.id, variants_list, start, db)

    result = await db.execute(
        select(Experiment)
        .where(Experiment.id == experiment.id)
        .options(selectinload(Experiment.variants))
    )
    experiment = result.scalar_one()
    return _experiment_to_response(experiment)


@router.patch(
    "/{experiment_id}/status",
    response_model=ExperimentResponse,
    status_code=status.HTTP_200_OK,
)
async def update_experiment_status(
    experiment_id: uuid.UUID,
    request: ExperimentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:write")),
) -> dict[str, Any]:
    """Transition an experiment between draft/running/paused/stopped."""
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        )

    current = experiment.status
    new = request.status

    allowed_transitions = {
        "draft": {"running", "stopped"},
        "running": {"paused", "stopped"},
        "paused": {"running", "stopped"},
        "stopped": set(),
    }

    if new not in allowed_transitions.get(current, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {current} to {new}",
        )

    if new == "running" and current == "draft":
        if experiment.min_sample_size is None or experiment.max_duration_days is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "min_sample_size and max_duration_days must be set before running"
                ),
            )
        experiment.start_date = utc_now()

    if new == "stopped":
        experiment.end_date = utc_now()

    experiment.status = new
    await db.commit()

    result = await db.execute(
        select(Experiment)
        .where(Experiment.id == experiment.id)
        .options(selectinload(Experiment.variants))
    )
    experiment = result.scalar_one()
    return _experiment_to_response(experiment)


@router.post(
    "/{experiment_id}/record",
    response_model=ExperimentEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_experiment_event(
    experiment_id: uuid.UUID,
    request: ExperimentEventRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:write")),
) -> dict[str, str]:
    """Record an exposure or conversion event for a user/variant."""
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        )

    variant_result = await db.execute(
        select(Variant)
        .where(Variant.experiment_id == experiment_id)
        .where(Variant.name == request.variant_name)
    )
    variant = variant_result.scalar_one_or_none()
    if variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variant {request.variant_name} not found",
        )

    metric_name = request.event_type

    if request.event_type == "exposure":
        existing = await db.execute(
            select(ExperimentMetric)
            .where(ExperimentMetric.experiment_id == experiment_id)
            .where(ExperimentMetric.user_id == request.user_id)
            .where(ExperimentMetric.metric_name == metric_name)
        )
        if existing.scalar_one_or_none() is not None:
            return {"status": "recorded"}

    metric = ExperimentMetric(
        id=uuid.uuid4(),
        experiment_id=experiment_id,
        variant_id=variant.id,
        user_id=request.user_id,
        metric_name=metric_name,
        metric_value=1.0,
        event_time=utc_now(),
    )
    db.add(metric)
    await db.commit()
    return {"status": "recorded"}


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
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:read")),
) -> dict[str, Any]:
    """Aggregate experiment stats from ExperimentDailyStat and return comparisons."""
    exp_result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    exp = exp_result.scalar_one_or_none()
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        )

    v_result = await db.execute(
        select(Variant).where(Variant.experiment_id == experiment_id)
    )
    variants = list(v_result.scalars().all())

    d_result = await db.execute(
        select(ExperimentDailyStat).where(
            ExperimentDailyStat.experiment_id == experiment_id
        )
    )
    rows = list(d_result.scalars().all())

    variant_summaries = []
    control_summary = None
    for v in variants:
        v_rows = [r for r in rows if r.variant_id == v.id]
        total_users = sum(r.users for r in v_rows)
        total_impressions = sum(r.impressions for r in v_rows)
        total_clicks = sum(r.clicks for r in v_rows)
        total_conversions = sum(r.conversions for r in v_rows)
        total_revenue = sum(r.revenue for r in v_rows)

        ctr = total_clicks / total_impressions if total_impressions > 0 else 0.0
        cvr = total_conversions / total_users if total_users > 0 else 0.0
        avg_revenue = total_revenue / total_users if total_users > 0 else 0.0

        summary = {
            "variant_id": str(v.id),
            "name": v.name,
            "traffic_pct": v.traffic_pct,
            "users": total_users,
            "impressions": total_impressions,
            "clicks": total_clicks,
            "conversions": total_conversions,
            "revenue": round(total_revenue, 2),
            "ctr": round(ctr, 4),
            "conversion_rate": round(cvr, 4),
            "avg_revenue_per_user": round(avg_revenue, 2),
        }
        variant_summaries.append(summary)
        if v.name.lower() == "control":
            control_summary = summary

    if control_summary is None and variant_summaries:
        control_summary = variant_summaries[0]

    comparisons = []
    metric_key = {
        "ctr": "ctr",
        "conversion_rate": "conversion_rate",
        "revenue": "avg_revenue_per_user",
    }.get(exp.metric_name, "ctr")

    for vs in variant_summaries:
        if control_summary and vs["name"].lower() == control_summary["name"].lower():
            continue
        ctrl_val = control_summary.get(metric_key, 0) if control_summary else 0
        treat_val = vs.get(metric_key, 0)
        lift = ((treat_val - ctrl_val) / ctrl_val * 100) if ctrl_val > 0 else 0.0
        comparisons.append(
            {
                "variant_name": vs["name"],
                "control_name": (
                    control_summary["name"] if control_summary else "baseline"
                ),
                "metric": exp.metric_name,
                "control_value": round(ctrl_val, 4),
                "treatment_value": round(treat_val, 4),
                "relative_lift_pct": round(lift, 2),
                "is_significant": abs(lift) > 5.0,
            }
        )

    return {
        "experiment_id": str(exp.id),
        "status": exp.status,
        "metric": exp.metric_name,
        "control": control_summary,
        "variants": variant_summaries,
        "comparisons": comparisons,
    }


@router.get("/{experiment_id}/trend")
async def get_experiment_trend(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:read")),
) -> dict[str, Any]:
    """Return daily stats for each variant, for the trend chart."""
    v_stmt = select(Variant).where(Variant.experiment_id == experiment_id)
    v_result = await db.execute(v_stmt)
    variants = {v.id: v.name for v in v_result.scalars().all()}
    if not variants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found or has no variants",
        )

    d_stmt = (
        select(ExperimentDailyStat)
        .where(ExperimentDailyStat.experiment_id == experiment_id)
        .order_by(ExperimentDailyStat.date.asc())
    )
    d_result = await db.execute(d_stmt)
    rows = d_result.scalars().all()

    dates = sorted({r.date.isoformat() for r in rows})
    date_labels = [d[5:].replace("-", "/") for d in dates]

    variant_data: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        vname = variants.get(r.variant_id, "unknown")
        if vname not in variant_data:
            variant_data[vname] = []
        ctr = r.clicks / r.impressions if r.impressions > 0 else 0.0
        cvr = r.conversions / r.users if r.users > 0 else 0.0
        variant_data[vname].append(
            {
                "date": r.date.isoformat(),
                "date_label": r.date.strftime("%m/%d").lstrip("0").replace("/0", "/"),
                "impressions": r.impressions,
                "clicks": r.clicks,
                "conversions": r.conversions,
                "revenue": r.revenue,
                "users": r.users,
                "ctr": round(ctr, 4),
                "conversion_rate": round(cvr, 4),
            }
        )

    return {
        "dates": date_labels,
        "variants": [
            {"name": name, "daily": variant_data[name]}
            for name in sorted(
                variant_data.keys(), key=lambda n: (n.lower() != "control", n)
            )
        ],
    }


def _experiment_to_response(experiment: Experiment) -> dict[str, Any]:
    return {
        "id": str(experiment.id),
        "name": experiment.name,
        "campaign_id": str(experiment.campaign_id) if experiment.campaign_id else None,
        "description": experiment.description,
        "status": experiment.status,
        "traffic_split": experiment.traffic_allocation,
        "success_metric": experiment.metric_name,
        "min_sample_size": experiment.min_sample_size,
        "max_duration_days": experiment.max_duration_days,
        "start_date": experiment.start_date,
        "end_date": experiment.end_date,
        "created_at": experiment.created_at,
        "updated_at": experiment.updated_at,
        "variants": [
            {
                "id": str(v.id),
                "name": v.name,
                "config": v.config,
                "traffic_allocation": int(round(v.traffic_pct * 100)),
                "created_at": v.created_at,
            }
            for v in experiment.variants
        ],
    }


@router.get("", response_model=List[ExperimentResponse])
async def list_experiments(
    status_filter: str | None = None,
    data_source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:read")),
) -> List[dict[str, Any]]:
    """List A/B experiments."""
    query = select(Experiment).order_by(Experiment.created_at.desc())
    if status_filter:
        query = query.where(Experiment.status == status_filter)
    result = await db.execute(query.options(selectinload(Experiment.variants)))
    return [
        {**_experiment_to_response(e), "data_source": data_source}
        for e in result.scalars().all()
    ]


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: uuid.UUID,
    data_source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:read")),
) -> dict[str, Any]:
    """Get a single A/B experiment."""
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        )
    await db.refresh(experiment, attribute_names=["variants"])
    return {**_experiment_to_response(experiment), "data_source": data_source}


@router.post("/{experiment_id}/start", response_model=ExperimentResponse)
async def start_experiment(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:write")),
) -> dict[str, Any]:
    """Start an experiment (convenience shortcut)."""
    return await update_experiment_status(
        experiment_id,
        ExperimentStatusUpdate(status="running"),
        db,
        _user,
    )


@router.post("/{experiment_id}/stop", response_model=ExperimentResponse)
async def stop_experiment(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:write")),
) -> dict[str, Any]:
    """Stop an experiment (convenience shortcut)."""
    return await update_experiment_status(
        experiment_id,
        ExperimentStatusUpdate(status="stopped"),
        db,
        _user,
    )


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("campaign:write")),
) -> None:
    """Delete an experiment and its variants/metrics."""
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        )
    await db.delete(experiment)
    await db.commit()
