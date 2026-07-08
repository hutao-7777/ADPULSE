"""Production RTB API endpoints (v2) requiring API key authentication."""

from fastapi import Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import validate_api_key
from app.models.models import ApiKey
from app.services.rtb_v2_engine import BidRequest, RTBV2Engine, get_rtb_v2_engine

router = APIRouter(prefix="/api/v2/rtb", tags=["rtb-v2"])


class BidRequestSchema(BaseModel):
    """Incoming bid request payload."""

    request_id: str = Field(..., min_length=1)
    impression_id: str = Field(..., min_length=1)
    floor_price: float = Field(..., gt=0)
    user_id: str | None = None
    device_type: str | None = None
    geo: str | None = None
    context: dict = Field(default_factory=dict)


class BidResponseSchema(BaseModel):
    """Outgoing bid response payload."""

    request_id: str
    impression_id: str
    bid_amount: float | None
    settlement_price: float | None
    campaign_id: str | None
    creative_id: str | None
    currency: str
    latency_ms: float
    reason: str | None


@router.post(
    "/auction", response_model=BidResponseSchema, status_code=status.HTTP_200_OK
)
async def run_auction_v2(
    request: BidRequestSchema,
    db: AsyncSession = Depends(get_db),
    engine: RTBV2Engine = Depends(get_rtb_v2_engine),
    api_key: ApiKey = Depends(validate_api_key),
) -> dict:
    """Run a production second-price auction for an SSP/DSP.

    Requires a valid API key with appropriate scopes.
    """
    bid_request = BidRequest(
        request_id=request.request_id,
        impression_id=request.impression_id,
        floor_price=request.floor_price,
        user_id=request.user_id,
        device_type=request.device_type,
        geo=request.geo,
        context=request.context,
    )

    response = await engine.run_auction(db, bid_request)

    # Persist asynchronously in the background to keep latency low.
    # In production this should be a background task/queue.
    await engine.persist_result(db, bid_request, response)

    return {
        "request_id": response.request_id,
        "impression_id": response.impression_id,
        "bid_amount": response.bid_amount,
        "settlement_price": response.settlement_price,
        "campaign_id": str(response.campaign_id) if response.campaign_id else None,
        "creative_id": str(response.creative_id) if response.creative_id else None,
        "currency": response.currency,
        "latency_ms": response.latency_ms,
        "reason": response.reason,
    }
