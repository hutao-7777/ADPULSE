"""SQLAlchemy 2.0 domain models for AdPulse.

All primary keys use UUID. The runtime target is SQLite via aiosqlite.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.campaign import Campaign


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False, index=True
    )  # draft, running, paused, completed
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    traffic_allocation: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False
    )  # percentage of eligible traffic
    min_sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    winner_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("variants.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    campaign: Mapped[Optional["Campaign"]] = relationship(
        "Campaign", back_populates="experiments"
    )
    winner_variant: Mapped[Optional["Variant"]] = relationship(
        "Variant",
        foreign_keys="Experiment.winner_variant_id",
    )
    variants: Mapped[List["Variant"]] = relationship(
        "Variant",
        back_populates="experiment",
        foreign_keys="Variant.experiment_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment",
        back_populates="experiment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    metrics: Mapped[List["ExperimentMetric"]] = relationship(
        "ExperimentMetric",
        back_populates="experiment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_experiments_status_dates", "status", "start_date", "end_date"),
        Index("ix_experiments_campaign_status", "campaign_id", "status"),
    )


class Variant(Base):
    __tablename__ = "variants"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # control, treatment-A, ...
    traffic_pct: Mapped[float] = mapped_column(Float, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    experiment: Mapped["Experiment"] = relationship(
        "Experiment",
        back_populates="variants",
        foreign_keys="Variant.experiment_id",
    )
    metrics: Mapped[List["ExperimentMetric"]] = relationship(
        "ExperimentMetric", back_populates="variant"
    )

    __table_args__ = (
        UniqueConstraint("experiment_id", "name", name="uq_variant_experiment_name"),
    )


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    bucket: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    experiment: Mapped["Experiment"] = relationship(
        "Experiment", back_populates="assignments"
    )
    variant: Mapped["Variant"] = relationship("Variant")

    __table_args__ = (
        UniqueConstraint(
            "experiment_id", "user_id", name="uq_assignment_experiment_user"
        ),
        Index("ix_assignments_user_experiment", "user_id", "experiment_id"),
    )


class ExperimentMetric(Base):
    __tablename__ = "experiment_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    experiment: Mapped["Experiment"] = relationship(
        "Experiment", back_populates="metrics"
    )
    variant: Mapped["Variant"] = relationship("Variant", back_populates="metrics")

    __table_args__ = (
        Index("ix_experiment_metrics_variant_metric", "variant_id", "metric_name"),
        Index("ix_experiment_metrics_event_time", "event_time"),
    )


# ---------------------------------------------------------------------------
# Attribution domain
# ---------------------------------------------------------------------------
