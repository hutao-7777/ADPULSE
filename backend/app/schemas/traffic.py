"""Pydantic schemas for traffic quality APIs."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrafficAssessRequest(BaseModel):
    campaign_id: str = Field(..., min_length=1)
    date: Optional[datetime] = Field(default=None)
    geo: Optional[str] = Field(default=None)
    device_type: Optional[str] = Field(default=None)
    raw_metrics: Dict = Field(..., description="Raw traffic metrics dictionary")


class TrafficQualityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    date: datetime
    geo: Optional[str]
    device_type: Optional[str]
    quality_score: float
    grade: str
    ctr_score: float
    cvr_score: float
    bounce_score: float
    dwell_score: float
    interaction_score: float
    flags: List[str]
    anomaly_count: int


class FraudAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    alert_type: str
    severity: str
    description: str
    detected_at: datetime
    status: str


class QualityTrendPoint(BaseModel):
    date: str
    quality_score: float
    grade: str
    ctr_score: float
    cvr_score: float
    bounce_score: float
    dwell_score: float
    interaction_score: float
    anomaly_count: int
    flags: List[str]


class QualityTrendResponse(BaseModel):
    trend: List[QualityTrendPoint]
