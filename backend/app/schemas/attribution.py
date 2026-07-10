"""Pydantic schemas for multi-touch attribution APIs."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TouchpointCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    campaign_id: str = Field(..., min_length=1)
    channel: str = Field(..., min_length=1)
    event_type: str = Field(..., pattern="^(impression|click|conversion)$")
    event_time: Optional[datetime] = Field(default=None)
    conversion_value: Optional[float] = Field(default=None, ge=0)


class ConversionCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    campaign_id: str = Field(..., min_length=1)
    conversion_value: float = Field(..., ge=0)
    channel: str = Field(..., min_length=1)
    device_type: Optional[str] = Field(default=None)
    geo: Optional[str] = Field(default=None)
    creative_id: Optional[str] = Field(default=None)
    conversion_time: Optional[datetime] = Field(default=None)


class AttributionCalculateRequest(BaseModel):
    conversion_value: float = Field(..., ge=0)
    models: Optional[List[str]] = Field(default=None)


class TouchpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    touchpoint_seq: int = Field(..., alias="seq")
    channel: str
    event_type: str
    event_time: Optional[datetime]
    conversion_event_id: Optional[UUID]


class AttributionCompareResponse(BaseModel):
    journey: List[Dict]
    conversion_value: float
    models: Dict[str, Dict[str, float]]
    model_credits: Dict[str, Dict[str, float]]
    summary: str
    data_source: Optional[str] = None


class ChannelAverageCredit(BaseModel):
    channel: str
    avg_credit: float


class ModelComparisonItem(BaseModel):
    model_type: str
    channel_credits: List[ChannelAverageCredit]


class ModelComparisonResponse(BaseModel):
    comparisons: List[ModelComparisonItem]
    data_source: Optional[str] = None
