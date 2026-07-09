"""RTB second-price auction engine."""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuctionRequest, AuctionWin, Campaign, Creative


@dataclass
class BidRequest:
    """Incoming bid request from an SSP."""

    request_id: str
    impression_id: str
    floor_price: float
    user_id: Optional[str]
    device_type: Optional[str]
    geo: Optional[str]
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BidResponse:
    """Outgoing bid response to an SSP."""

    request_id: str
    impression_id: str
    bid_amount: Optional[float]
    settlement_price: Optional[float]
    campaign_id: Optional[uuid.UUID]
    creative_id: Optional[uuid.UUID]
    currency: str = "USD"
    latency_ms: float = 0.0
    reason: Optional[str] = None


@dataclass
class BidCandidate:
    """Internal candidate bid from an eligible campaign."""

    campaign_id: uuid.UUID
    creative_id: uuid.UUID
    bid_amount: float


class RTBAuctionEngine:
    """Second-price RTB auction engine."""

    async def _load_active_campaigns(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Fetch active campaigns from the database."""
        result = await db.execute(select(Campaign).where(Campaign.status == "active"))
        campaigns = result.scalars().all()
        return [
            {
                "id": str(c.id),
                "name": c.name,
                "budget": c.budget,
                "daily_budget": c.daily_budget,
                "currency": c.currency,
                "target_cpa": c.target_cpa,
                "target_roas": c.target_roas,
                "frequency_cap": c.frequency_cap,
            }
            for c in campaigns
        ]

    async def _get_campaign_creatives(
        self, db: AsyncSession, campaign_id: uuid.UUID
    ) -> List[Creative]:
        """Return active creatives for a campaign."""
        result = await db.execute(
            select(Creative)
            .where(Creative.campaign_id == campaign_id)
            .where(Creative.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())

    def _score_campaign(
        self, campaign: Dict[str, Any], request: BidRequest
    ) -> Optional[float]:
        """Compute a per-impression bid for a campaign.

        Simplified scoring: target CPA inverse with geo/device modifiers.
        In production this would use ML CTR/CVR predictors.
        """
        target_cpa = campaign.get("target_cpa")
        if target_cpa is None or target_cpa <= 0:
            return None

        base_bid = 1.0 / target_cpa

        # Geo modifier
        geo = (request.geo or "").lower()
        if geo in {"us", "uk", "ca", "de"}:
            base_bid *= 1.2
        elif geo in {"cn", "in", "br"}:
            base_bid *= 0.8

        # Device modifier
        device = (request.device_type or "").lower()
        if device == "mobile":
            base_bid *= 1.1
        elif device == "tablet":
            base_bid *= 0.95

        # Floor price guard
        if base_bid < request.floor_price:
            return None

        return cast(float, round(base_bid, 6))

    async def run_auction(self, db: AsyncSession, request: BidRequest) -> BidResponse:
        """Run a second-price auction and return the winner."""
        start = time.perf_counter()

        campaigns = await self._load_active_campaigns(db)
        candidates: List[BidCandidate] = []

        for campaign in campaigns:
            campaign_id = uuid.UUID(campaign["id"])
            bid_amount = self._score_campaign(campaign, request)
            if bid_amount is None:
                continue

            creatives = await self._get_campaign_creatives(db, campaign_id)
            if not creatives:
                continue

            # Pick the first active creative (simplified; production uses ML scorer).
            creative = creatives[0]
            candidates.append(
                BidCandidate(
                    campaign_id=campaign_id,
                    creative_id=creative.id,
                    bid_amount=bid_amount,
                )
            )

        if not candidates:
            latency_ms = (time.perf_counter() - start) * 1000
            return BidResponse(
                request_id=request.request_id,
                impression_id=request.impression_id,
                bid_amount=None,
                settlement_price=None,
                campaign_id=None,
                creative_id=None,
                latency_ms=latency_ms,
                reason="no_eligible_bids",
            )

        # Sort by bid descending.
        candidates.sort(key=lambda x: x.bid_amount, reverse=True)
        winner = candidates[0]

        # Second-price settlement: max(second_highest_bid, floor_price).
        second_price = (
            candidates[1].bid_amount if len(candidates) > 1 else request.floor_price
        )
        settlement_price = max(second_price, request.floor_price)

        latency_ms = (time.perf_counter() - start) * 1000

        return BidResponse(
            request_id=request.request_id,
            impression_id=request.impression_id,
            bid_amount=winner.bid_amount,
            settlement_price=settlement_price,
            campaign_id=winner.campaign_id,
            creative_id=winner.creative_id,
            latency_ms=latency_ms,
            reason="won",
        )

    async def persist_result(
        self,
        db: AsyncSession,
        request: BidRequest,
        response: BidResponse,
    ) -> None:
        """Persist auction request and win records asynchronously."""
        auction_request = AuctionRequest(
            id=uuid.uuid4(),
            campaign_id=response.campaign_id,
            request_id=request.request_id,
            impression_id=request.impression_id,
            floor_price=request.floor_price,
            user_id=request.user_id,
            device_type=request.device_type,
            geo=request.geo,
            context=request.context,
            latency_ms=response.latency_ms,
        )
        db.add(auction_request)
        await db.flush()

        if response.campaign_id and response.settlement_price is not None:
            win = AuctionWin(
                id=uuid.uuid4(),
                auction_request_id=auction_request.id,
                campaign_id=response.campaign_id,
                creative_id=response.creative_id,
                winning_bid=response.bid_amount or 0.0,
                second_price=response.settlement_price,
                auction_type="second_price",
            )
            db.add(win)

        await db.commit()


# Singleton engine instance.
rtb_auction_engine = RTBAuctionEngine()


def get_rtb_auction_engine() -> RTBAuctionEngine:
    """Return the singleton RTB auction engine."""
    return rtb_auction_engine
