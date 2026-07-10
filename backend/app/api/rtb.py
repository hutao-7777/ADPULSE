"""RTB API endpoints."""

import uuid
from typing import Dict, List, Optional

from fastapi import Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import get_current_active_user, validate_api_key
from app.models import ApiKey, User
from app.schemas.rtb import (
    AuctionResult,
    BatchAuctionRequest,
    BatchAuctionResponse,
    DSPStatus,
    SingleAuctionRequest,
)
from app.services.rtb_engine import BidRequest, RTBAuctionEngine, get_rtb_auction_engine
from app.services.rtb_simulation_engine import (
    AuctionEngine,
    Impression,
    create_default_engine,
)

router = APIRouter(prefix="/api/rtb", tags=["rtb"])


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
    data_source: Optional[str] = None


@router.post(
    "/auction", response_model=BidResponseSchema, status_code=status.HTTP_200_OK
)
async def run_auction(
    request: BidRequestSchema,
    data_source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    engine: RTBAuctionEngine = Depends(get_rtb_auction_engine),
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
        "data_source": data_source,
    }


_simulation_engine: AuctionEngine = create_default_engine("second_price")


def _get_simulation_engine() -> AuctionEngine:
    return _simulation_engine


def _result_to_schema(result: Dict, data_source: Optional[str] = None) -> AuctionResult:
    winner = result.get("winner")
    return AuctionResult(
        impression_id=result["impression_id"],
        floor_price=result["floor_price"],
        auction_type=result["auction_type"],
        total_bids=result["total_bids"],
        bids=result["bids"],
        winner=winner,
        reason=result.get("reason"),
        latency_ms=result["latency_ms"],
        timestamp=result["timestamp"],
        data_source=data_source,
    )


@router.post("/simulate", response_model=AuctionResult)
async def run_simulation_auction(
    request: SingleAuctionRequest,
    data_source: Optional[str] = Query(None),
    engine: AuctionEngine = Depends(_get_simulation_engine),
    _user: User = Depends(get_current_active_user),
) -> AuctionResult:
    """Run a visual RTB auction simulation (JWT authenticated)."""
    engine.auction_type = request.auction_type
    impression = Impression(
        impression_id=str(uuid.uuid4()),
        floor_price=request.floor_price,
        user_segments=request.user_segments,
        device_type=request.device_type,
        geo=request.geo,
        ad_format=request.ad_format,
        context_category=request.context_category,
    )
    result = engine.run_auction(impression)
    return _result_to_schema(result, data_source)


@router.post("/simulate/batch", response_model=BatchAuctionResponse)
async def run_simulation_batch(
    request: BatchAuctionRequest,
    data_source: Optional[str] = Query(None),
    engine: AuctionEngine = Depends(_get_simulation_engine),
    _user: User = Depends(get_current_active_user),
) -> BatchAuctionResponse:
    """Run a batch RTB auction simulation (JWT authenticated)."""
    engine.auction_type = request.auction_type
    results = engine.run_batch_auctions(request.count, request.campaign_config)

    wins = [r for r in results if r["winner"]]
    win_rate_by_dsp: Dict[str, Dict] = {}
    total_bids_by_dsp: Dict[str, int] = {}

    for result in results:
        for bid in result["bids"]:
            dsp = bid["dsp"]
            total_bids_by_dsp[dsp] = total_bids_by_dsp.get(dsp, 0) + 1
            if result["winner"] and result["winner"]["dsp"] == dsp:
                win_rate_by_dsp.setdefault(dsp, {"wins": 0, "bids": 0})
                win_rate_by_dsp[dsp]["wins"] += 1
            win_rate_by_dsp.setdefault(dsp, {"wins": 0, "bids": 0})
            win_rate_by_dsp[dsp]["bids"] += 1

    for dsp, stats in win_rate_by_dsp.items():
        stats["win_rate"] = stats["wins"] / stats["bids"] if stats["bids"] > 0 else 0.0

    avg_winning_bid = (
        sum(r["winner"]["settlement_price"] for r in wins) / len(wins) if wins else 0.0
    )
    total_latency = sum(r["latency_ms"] for r in results)

    stats = {
        "total_auctions": len(results),
        "filled_auctions": len(wins),
        "fill_rate": len(wins) / len(results) if results else 0.0,
        "avg_winning_bid": avg_winning_bid,
        "avg_winning_cpm": avg_winning_bid * 1000.0,
        "win_rate_by_dsp": win_rate_by_dsp,
        "total_latency_ms": total_latency,
        "avg_latency_ms": total_latency / len(results) if results else 0.0,
    }

    return BatchAuctionResponse(
        count=len(results),
        results=[_result_to_schema(r, data_source) for r in results],
        stats=stats,
        data_source=data_source,
    )


@router.get("/dsps", response_model=List[DSPStatus])
async def list_simulation_dsps(
    data_source: Optional[str] = Query(None),
    engine: AuctionEngine = Depends(_get_simulation_engine),
    _user: User = Depends(get_current_active_user),
) -> List[DSPStatus]:
    """List DSPs participating in the simulation."""
    return [
        DSPStatus(
            name=dsp.name,
            budget_remaining=dsp.budget_remaining,
            target_segments=dsp.target_segments,
            max_cpm=dsp.max_cpm,
            pacing_rate=dsp.pacing_rate,
            bidding_strategy=dsp.bidding_strategy,
            data_source=data_source,
        )
        for dsp in engine.registered_dsps
    ]
