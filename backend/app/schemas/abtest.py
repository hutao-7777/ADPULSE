"""Pydantic schemas for A/B testing."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VariantConfig(BaseModel):
    name: str
    traffic_pct: float = Field(..., ge=0.0, le=1.0)


class ABTestCreate(BaseModel):
    name: str
    campaign_id: UUID
    metric_target: str = Field(..., pattern="^(ctr|conversion_rate|roi)$")
    traffic_split: float = Field(..., ge=0.0, le=1.0)
    variants_config: List[VariantConfig]

    @model_validator(mode="after")
    def check_traffic_distribution(self):
        total = sum(v.traffic_pct for v in self.variants_config)
        if not (0.99 <= total <= 1.01):
            raise ValueError("Variant traffic percentages must sum to 1.0")
        return self


class ABTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    campaign_id: UUID
    status: str
    traffic_split: float
    metric_target: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    winner: Optional[str]
    created_at: datetime
    data_source: Optional[str] = None


class ABTestDetailResponse(ABTestResponse):
    variants: List["ABTestVariantResponse"]


class ABTestVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    traffic_pct: float
    conversions: int
    impressions: int
    clicks: int
    revenue: float
    data_source: Optional[str] = None


class UserAssignRequest(BaseModel):
    user_id: str


class UserAssignResponse(BaseModel):
    variant: Optional[str]
    in_experiment: bool


class EventRecordRequest(BaseModel):
    variant: str
    event_type: str = Field(..., pattern="^(impression|click|conversion|revenue)$")
    revenue: Optional[float] = Field(None, ge=0)


class VariantStats(BaseModel):
    name: str
    traffic_pct: float
    impressions: int
    clicks: int
    conversions: int
    revenue: float
    ctr: float
    conversion_rate: float
    roi: float
    lift_pct: float
    p_value: float
    is_significant: bool
    sample_size_reached: bool
    confidence_interval: List[float]
    power: float
    data_source: Optional[str] = None


class ABTestResults(BaseModel):
    test_info: dict
    variants: List[VariantStats]
    recommendation: str
    data_source: Optional[str] = None


class AnomalyAlert(BaseModel):
    variant: str
    metric: str
    current_value: float
    expected_range: List[float]
    severity: str


ABTestDetailResponse.model_rebuild()
