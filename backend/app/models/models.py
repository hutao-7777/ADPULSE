"""SQLAlchemy 2.0 domain models for AdPulse.

All primary keys use UUID. PostgreSQL + pgvector is the target database.
Migrations are managed by Alembic; auto-create-all is forbidden in production.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)

from app.core.config import settings

# pgvector is only used for PostgreSQL deployments. SQLite uses JSON to store
# the embedding vector (vector similarity search is not supported on SQLite).
if settings.is_postgres:
    from pgvector.sqlalchemy import Vector

    _EmbeddingType = Vector(1536)
else:
    _EmbeddingType = JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# ---------------------------------------------------------------------------
# Association tables
# ---------------------------------------------------------------------------

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        Uuid(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        Uuid(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        Uuid(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

campaign_audience_segments = Table(
    "campaign_audience_segments",
    Base.metadata,
    Column(
        "campaign_id",
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "audience_segment_id",
        Uuid(as_uuid=True),
        ForeignKey("audience_segments.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ---------------------------------------------------------------------------
# Auth & RBAC
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    roles: Mapped[List["Role"]] = relationship(
        "Role", secondary=user_roles, back_populates="users", lazy="selectin"
    )
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary="user_permissions",
        back_populates="users",
        lazy="selectin",
    )
    api_keys: Mapped[List["ApiKey"]] = relationship("ApiKey", back_populates="user")
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user"
    )
    advertisers: Mapped[List["Advertiser"]] = relationship(
        "Advertiser", back_populates="owner"
    )
    agent_configs: Mapped[List["AgentConfig"]] = relationship(
        "AgentConfig", back_populates="user"
    )
    agent_runs: Mapped[List["AgentRun"]] = relationship(
        "AgentRun", back_populates="user"
    )

    __table_args__ = (Index("ix_users_email_active", "email", "is_active"),)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    users: Mapped[List["User"]] = relationship(
        "User", secondary=user_roles, back_populates="roles"
    )
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    roles: Mapped[List["Role"]] = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )
    users: Mapped[List["User"]] = relationship(
        "User", secondary="user_permissions", back_populates="permissions"
    )


class UserPermission(Base):
    __tablename__ = "user_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "permission_id", name="uq_user_permission"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (Index("ix_refresh_tokens_user_created", "user_id", "created_at"),)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    rate_limit_rps: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    __table_args__ = (Index("ix_api_keys_prefix_active", "key_prefix", "is_active"),)


# ---------------------------------------------------------------------------
# Advertiser & Campaign domain
# ---------------------------------------------------------------------------


class Advertiser(Base):
    __tablename__ = "advertisers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    billing_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    owner: Mapped["User"] = relationship("User", back_populates="advertisers")
    campaigns: Mapped[List["Campaign"]] = relationship(
        "Campaign", back_populates="advertiser"
    )


class AudienceSegment(Base):
    __tablename__ = "audience_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rules: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    estimated_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    campaigns: Mapped[List["Campaign"]] = relationship(
        "Campaign",
        secondary=campaign_audience_segments,
        back_populates="audience_segments",
    )


class BiddingStrategy(Base):
    __tablename__ = "bidding_strategies"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g. "manual_cpc", "target_cpa", "roi"
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    campaigns: Mapped[List["Campaign"]] = relationship(
        "Campaign", back_populates="bidding_strategy"
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    advertiser_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("advertisers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    bidding_strategy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bidding_strategies.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False, index=True
    )  # draft, active, paused, archived
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    daily_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    target_cpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_roas: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    frequency_cap: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    advertiser: Mapped[Optional["Advertiser"]] = relationship(
        "Advertiser", back_populates="campaigns"
    )
    bidding_strategy: Mapped[Optional["BiddingStrategy"]] = relationship(
        "BiddingStrategy", back_populates="campaigns"
    )
    audience_segments: Mapped[List["AudienceSegment"]] = relationship(
        "AudienceSegment",
        secondary=campaign_audience_segments,
        back_populates="campaigns",
    )
    creatives: Mapped[List["Creative"]] = relationship(
        "Creative", back_populates="campaign"
    )
    experiments: Mapped[List["Experiment"]] = relationship(
        "Experiment", back_populates="campaign"
    )
    daily_metrics: Mapped[List["DailyMetric"]] = relationship(
        "DailyMetric", back_populates="campaign"
    )
    touchpoints: Mapped[List["Touchpoint"]] = relationship(
        "Touchpoint", back_populates="campaign"
    )
    auction_requests: Mapped[List["AuctionRequest"]] = relationship(
        "AuctionRequest", back_populates="campaign"
    )

    __table_args__ = (
        Index("ix_campaigns_status_dates", "status", "start_date", "end_date"),
        Index("ix_campaigns_advertiser_status", "advertiser_id", "status"),
    )


class Creative(Base):
    __tablename__ = "creatives"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    asset_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    call_to_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    predicted_ctr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fatigue_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    campaign: Mapped[Optional["Campaign"]] = relationship(
        "Campaign", back_populates="creatives"
    )
    bids: Mapped[List["AuctionBid"]] = relationship(
        "AuctionBid", back_populates="creative"
    )

    __table_args__ = (
        Index("ix_creatives_campaign_active", "campaign_id", "is_active"),
        Index("ix_creatives_upload_time", "created_at"),
    )


# ---------------------------------------------------------------------------
# RTB auction domain
# ---------------------------------------------------------------------------


class AuctionRequest(Base):
    __tablename__ = "auction_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    impression_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ssp: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    floor_price: Mapped[float] = mapped_column(Float, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    geo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    campaign: Mapped[Optional["Campaign"]] = relationship(
        "Campaign", back_populates="auction_requests"
    )
    bids: Mapped[List["AuctionBid"]] = relationship(
        "AuctionBid", back_populates="auction_request"
    )
    win: Mapped[Optional["AuctionWin"]] = relationship(
        "AuctionWin", back_populates="auction_request"
    )

    __table_args__ = (
        Index("ix_auction_requests_created_at", "created_at"),
        Index("ix_auction_requests_campaign_created", "campaign_id", "created_at"),
    )


class AuctionBid(Base):
    __tablename__ = "auction_bids"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    auction_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("auction_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    creative_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creatives.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dsp_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    bid_amount: Mapped[float] = mapped_column(Float, nullable=False)
    ctr_estimate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    auction_request: Mapped["AuctionRequest"] = relationship(
        "AuctionRequest", back_populates="bids"
    )
    creative: Mapped[Optional["Creative"]] = relationship(
        "Creative", back_populates="bids"
    )

    __table_args__ = (Index("ix_auction_bids_created_at", "created_at"),)


class AuctionWin(Base):
    __tablename__ = "auction_wins"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    auction_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("auction_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creative_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creatives.id", ondelete="SET NULL"),
        nullable=True,
    )
    winning_bid: Mapped[float] = mapped_column(Float, nullable=False)
    second_price: Mapped[float] = mapped_column(Float, nullable=False)
    auction_type: Mapped[str] = mapped_column(
        String(50), default="second_price", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    auction_request: Mapped["AuctionRequest"] = relationship(
        "AuctionRequest", back_populates="win"
    )

    __table_args__ = (
        Index("ix_auction_wins_campaign_created", "campaign_id", "created_at"),
        UniqueConstraint("auction_request_id", name="uq_auction_wins_request"),
    )


# ---------------------------------------------------------------------------
# A/B testing domain
# ---------------------------------------------------------------------------


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
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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
    )
    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment", back_populates="experiment"
    )
    metrics: Mapped[List["ExperimentMetric"]] = relationship(
        "ExperimentMetric", back_populates="experiment"
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
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
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
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
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
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
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


class ConversionEvent(Base):
    __tablename__ = "conversion_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    conversion_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    conversion_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    channel: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    geo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    creative_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creatives.id", ondelete="SET NULL"),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )

    touchpoints: Mapped[List["Touchpoint"]] = relationship(
        "Touchpoint", back_populates="conversion_event"
    )
    attribution_results: Mapped[List["AttributionResult"]] = relationship(
        "AttributionResult", back_populates="conversion_event"
    )

    __table_args__ = (
        Index("ix_conversion_events_user_time", "user_id", "conversion_time"),
        Index("ix_conversion_events_campaign_time", "campaign_id", "conversion_time"),
    )


class Touchpoint(Base):
    __tablename__ = "touchpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creative_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creatives.id", ondelete="SET NULL"),
        nullable=True,
    )
    touchpoint_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # impression, click, view
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    conversion_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversion_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="touchpoints"
    )
    conversion_event: Mapped[Optional["ConversionEvent"]] = relationship(
        "ConversionEvent", back_populates="touchpoints"
    )

    __table_args__ = (
        Index(
            "ix_touchpoints_user_campaign_seq",
            "user_id",
            "campaign_id",
            "touchpoint_seq",
        ),
        Index("ix_touchpoints_event_time", "event_time"),
        Index("ix_touchpoints_conversion", "conversion_event_id"),
    )


class AttributionResult(Base):
    __tablename__ = "attribution_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversion_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversion_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # shapley, linear, last_click, etc.
    click_window_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    view_window_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    channel_credits: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    campaign_credits: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    conversion_event: Mapped["ConversionEvent"] = relationship(
        "ConversionEvent", back_populates="attribution_results"
    )

    __table_args__ = (
        Index(
            "ix_attribution_results_conversion_model",
            "conversion_event_id",
            "model_type",
        ),
        Index("ix_attribution_results_calculated_at", "calculated_at"),
    )


# ---------------------------------------------------------------------------
# Traffic quality domain
# ---------------------------------------------------------------------------


class TrafficQualityScore(Base):
    __tablename__ = "traffic_quality_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    geo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    grade: Mapped[str] = mapped_column(String(20), default="standard", nullable=False)
    ctr_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cvr_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bounce_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dwell_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    interaction_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    flags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    anomaly_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_traffic_quality_scores_campaign_date", "campaign_id", "date"),
        Index("ix_traffic_quality_scores_date", "date"),
    )


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="warning", nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="open", nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_fraud_alerts_campaign_status", "campaign_id", "status"),
        Index("ix_fraud_alerts_detected_at", "detected_at"),
    )


# ---------------------------------------------------------------------------
# Dashboard / reporting
# ---------------------------------------------------------------------------


class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    spend: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ctr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cpm: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cpc: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    roi: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="daily_metrics"
    )

    __table_args__ = (
        Index("ix_daily_metrics_date_campaign", "date", "campaign_id"),
        UniqueConstraint("date", "campaign_id", name="uq_daily_metric_date_campaign"),
    )


# ---------------------------------------------------------------------------
# Agent domain
# ---------------------------------------------------------------------------


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    llm_provider: Mapped[str] = mapped_column(
        String(50), default="openai", nullable=False
    )
    llm_model: Mapped[str] = mapped_column(
        String(100), default="gpt-4o-mini", nullable=False
    )
    tools_enabled: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    max_steps: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="agent_configs")
    runs: Mapped[List["AgentRun"]] = relationship("AgentRun", back_populates="config")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    config_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agent_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), default="running", nullable=False
    )  # running, completed, failed
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    final_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    step_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    config: Mapped["AgentConfig"] = relationship("AgentConfig", back_populates="runs")
    user: Mapped["User"] = relationship("User", back_populates="agent_runs")
    steps: Mapped[List["AgentStep"]] = relationship("AgentStep", back_populates="run")


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # think, act, observe
    thought: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tool_input: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tool_output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="steps")

    __table_args__ = (
        UniqueConstraint("run_id", "step_number", name="uq_agent_step_run_number"),
    )


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[List[float]] = mapped_column(_EmbeddingType, nullable=False)
    memory_type: Mapped[str] = mapped_column(
        String(50), default="observation", nullable=False
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_agent_memories_user_type", "user_id", "memory_type"),
        Index("ix_agent_memories_created_at", "created_at"),
    )


# ---------------------------------------------------------------------------
# Legacy / demo-compatible models
# ---------------------------------------------------------------------------
# The following models preserve the original SQLite-oriented schema used by
# the existing API, services and seed data. They coexist with the new
# PostgreSQL-oriented tables above while the codebase is incrementally
# migrated to the production schema.
# ---------------------------------------------------------------------------


class Auction(Base):
    """Legacy auction result table used by RTB dashboard and seed data."""

    __tablename__ = "auctions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    impression_id: Mapped[str] = mapped_column(String(255), nullable=False)
    floor_price: Mapped[float] = mapped_column(Float, nullable=False)
    winning_bid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    winning_dsp: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    auction_type: Mapped[str] = mapped_column(
        String(50), default="first_price", nullable=False
    )
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    bids: Mapped[List["BidRecord"]] = relationship(
        "BidRecord", back_populates="auction"
    )

    __table_args__ = (
        Index("ix_auction_campaign_id", "campaign_id"),
        Index("ix_auction_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Auction(id={self.id}, campaign_id={self.campaign_id}, "
            f"impression_id={self.impression_id!r})>"
        )


class BidRecord(Base):
    """Legacy bid record table used by RTB API and seed data."""

    __tablename__ = "bid_records"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    auction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("auctions.id", ondelete="CASCADE"),
        nullable=False,
    )
    dsp_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bid_amount: Mapped[float] = mapped_column(Float, nullable=False)
    ctr_estimate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    was_winner: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    auction: Mapped["Auction"] = relationship("Auction", back_populates="bids")

    __table_args__ = (
        Index("ix_bid_record_auction_id", "auction_id"),
        Index("ix_bid_record_dsp_name", "dsp_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<BidRecord(id={self.id}, auction_id={self.auction_id}, "
            f"dsp_name={self.dsp_name!r})>"
        )


class ABTest(Base):
    """Legacy A/B test table used by A/B testing API and seed data."""

    __tablename__ = "ab_tests"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    traffic_split: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    metric_target: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    winner: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    variants: Mapped[List["ABTestVariant"]] = relationship(
        "ABTestVariant", back_populates="ab_test"
    )

    __table_args__ = (
        Index("ix_ab_test_campaign_id", "campaign_id"),
        Index("ix_ab_test_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ABTest(id={self.id}, name={self.name!r}, "
            f"campaign_id={self.campaign_id})>"
        )


class ABTestVariant(Base):
    """Legacy A/B test variant table used by A/B testing API and seed data."""

    __tablename__ = "ab_test_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ab_test_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ab_tests.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    traffic_pct: Mapped[float] = mapped_column(Float, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    ab_test: Mapped["ABTest"] = relationship("ABTest", back_populates="variants")

    __table_args__ = (
        Index("ix_ab_test_variant_ab_test_id", "ab_test_id"),
        Index("ix_ab_test_variant_name", "name"),
    )

    def __repr__(self) -> str:
        return (
            f"<ABTestVariant(id={self.id}, ab_test_id={self.ab_test_id}, "
            f"name={self.name!r})>"
        )
