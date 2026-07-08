"""RTB auction simulation API."""

import uuid
from datetime import datetime
from typing import Dict, List

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.models.models import Auction, BidRecord
from app.schemas.rtb import (
    AuctionResult,
    BatchAuctionRequest,
    BatchAuctionResponse,
    DSPConfigUpdate,
    DSPStatus,
    SingleAuctionRequest,
)
from app.services.rtb_engine import AuctionEngine, Impression, create_default_engine

router = APIRouter(prefix="/api/rtb", tags=["rtb"])

_engine: AuctionEngine = create_default_engine("second_price")


def get_engine() -> AuctionEngine:
    return _engine


def _result_to_schema(result: Dict) -> AuctionResult:
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
    )


async def _persist_auction(
    db: AsyncSession, result: Dict, campaign_id: uuid.UUID | None = None
) -> None:
    """Persist an auction result and its bids to the database."""
    winner = result.get("winner")
    auction = Auction(
        id=uuid.uuid4(),
        campaign_id=campaign_id,
        impression_id=result["impression_id"],
        floor_price=result["floor_price"],
        winning_bid=winner["winning_bid"] if winner else None,
        winning_dsp=winner["dsp"] if winner else None,
        auction_type=result["auction_type"],
        latency_ms=float(result["latency_ms"]),
        created_at=datetime.fromisoformat(result["timestamp"]),
    )
    db.add(auction)
    await db.flush()

    for bid in result["bids"]:
        record = BidRecord(
            id=uuid.uuid4(),
            auction_id=auction.id,
            dsp_name=bid["dsp"],
            bid_amount=bid["bid"],
            ctr_estimate=0.0,
            was_winner=(winner is not None and winner["dsp"] == bid["dsp"]),
            created_at=auction.created_at,
        )
        db.add(record)


@router.post("/auction/single", response_model=AuctionResult)
async def run_single_auction(
    request: SingleAuctionRequest,
    db: AsyncSession = Depends(get_db),
    engine: AuctionEngine = Depends(get_engine),
) -> AuctionResult:
    """Run a single RTB auction simulation."""
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
    await _persist_auction(db, result)
    await db.commit()

    return _result_to_schema(result)


@router.post("/auction/batch", response_model=BatchAuctionResponse)
async def run_batch_auction(
    request: BatchAuctionRequest,
    db: AsyncSession = Depends(get_db),
    engine: AuctionEngine = Depends(get_engine),
) -> BatchAuctionResponse:
    """Run a batch of RTB auction simulations."""
    engine.auction_type = request.auction_type
    results = engine.run_batch_auctions(request.count, request.campaign_config)

    for result in results:
        await _persist_auction(db, result)
    await db.commit()

    # Aggregate stats
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
        results=[_result_to_schema(r) for r in results],
        stats=stats,
    )


@router.get("/dsps", response_model=List[DSPStatus])
async def list_dsps(engine: AuctionEngine = Depends(get_engine)) -> List[DSPStatus]:
    """List registered DSPs with their current status."""
    return [
        DSPStatus(
            name=dsp.name,
            budget_remaining=dsp.budget_remaining,
            target_segments=dsp.target_segments,
            max_cpm=dsp.max_cpm,
            pacing_rate=dsp.pacing_rate,
            bidding_strategy=dsp.bidding_strategy,
        )
        for dsp in engine.registered_dsps
    ]


@router.post("/dsps/{dsp_name}/config", response_model=DSPStatus)
async def update_dsp_config(
    dsp_name: str,
    update: DSPConfigUpdate,
    engine: AuctionEngine = Depends(get_engine),
) -> DSPStatus:
    """Update configuration for a specific DSP."""
    dsp = engine.get_dsp(dsp_name)
    if dsp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="DSP not found"
        )

    if update.bidding_strategy is not None:
        dsp.bidding_strategy = update.bidding_strategy
    if update.budget_remaining is not None:
        dsp.budget_remaining = update.budget_remaining
        dsp._initial_budget = update.budget_remaining
    if update.target_segments is not None:
        dsp.target_segments = update.target_segments
    if update.max_cpm is not None:
        dsp.max_cpm = update.max_cpm
    if update.pacing_rate is not None:
        dsp.pacing_rate = update.pacing_rate

    return DSPStatus(
        name=dsp.name,
        budget_remaining=dsp.budget_remaining,
        target_segments=dsp.target_segments,
        max_cpm=dsp.max_cpm,
        pacing_rate=dsp.pacing_rate,
        bidding_strategy=dsp.bidding_strategy,
    )
