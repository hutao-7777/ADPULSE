"""Pydantic schemas for creative resources."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreativeBase(BaseModel):
    name: str


class CreativeCreate(CreativeBase):
    file_type: str


class CreativeScore(BaseModel):
    ai_score: float
    predicted_ctr: float
    confidence: float
    feature_vector: list[float]
    color_harmony: float
    text_ratio: float
    composition_balance: float
    overall_score: float


class CreativeResponse(CreativeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    image_path: str
    file_type: str
    upload_time: datetime
    ai_score: Optional[float]
    predicted_ctr: Optional[float]
    fatigue_score: float


class CreativeDetailResponse(CreativeResponse):
    score: CreativeScore
