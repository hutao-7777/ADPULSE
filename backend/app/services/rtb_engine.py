"""Real-time bidding simulation engine."""

import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class Impression:
    """A single ad impression opportunity."""

    impression_id: str
    floor_price: float
    user_segments: List[str]
    device_type: str
    geo: str
    ad_format: str
    context_category: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DSPBidder:
    """A demand-side platform bidder."""

    name: str
    budget_remaining: float
    target_segments: List[str]
    max_cpm: float
    pacing_rate: float = 1.0
    bidding_strategy: str = "balanced"

    _initial_budget: float = field(init=False)

    def __post_init__(self) -> None:
        self._initial_budget = self.budget_remaining

    @property
    def spend_ratio(self) -> float:
        if self._initial_budget <= 0:
            return 0.0
        return 1.0 - (self.budget_remaining / self._initial_budget)

    def _relevance_score(self, impression: Impression) -> float:
        if not self.target_segments:
            return 0.5
        matches = [
            seg for seg in impression.user_segments if seg in self.target_segments
        ]
        if not matches:
            return 0.1
        return max(0.1, min(1.0, len(matches) / max(len(self.target_segments), 1)))

    def calculate_bid(self, impression: Impression) -> Optional[float]:
        """Calculate a per-impression bid price.

        The internal math is done in CPM terms, then converted to a single
        impression price (CPM / 1000) for settlement.
        """
        relevance = self._relevance_score(impression)

        # 50% chance to pass when there is no segment match
        if relevance <= 0.1 and random.random() < 0.5:
            return None

        # Strategy modifier
        strategy_modifiers = {
            "aggressive": 1.15,
            "balanced": 1.0,
            "conservative": 0.85,
        }
        strategy_modifier = strategy_modifiers.get(self.bidding_strategy, 1.0)

        # Pacing adjustment
        current_pacing = self.pacing_rate
        if self.spend_ratio > 0.8:
            current_pacing *= 0.5

        # Base CPM bid
        cpm_bid = self.max_cpm * relevance * strategy_modifier * current_pacing

        # Device adjustment
        if impression.device_type == "mobile":
            cpm_bid *= 1.10

        # Geo adjustment
        if impression.geo == "tier1":
            cpm_bid *= 1.15
        elif impression.geo == "tier3":
            cpm_bid *= 0.90

        # Convert to single impression price
        per_impression_bid = cpm_bid / 1000.0

        if self.budget_remaining < per_impression_bid:
            return None

        return max(0.0, per_impression_bid)


class AuctionEngine:
    """Runs first-price or second-price auctions across registered DSPs."""

    def __init__(
        self,
        auction_type: str = "second_price",
        registered_dsps: Optional[List[DSPBidder]] = None,
    ) -> None:
        if auction_type not in {"first_price", "second_price"}:
            raise ValueError("auction_type must be 'first_price' or 'second_price'")
        self.auction_type: str = auction_type
        self.registered_dsps: List[DSPBidder] = registered_dsps or []

    def register_dsp(self, dsp: DSPBidder) -> None:
        self.registered_dsps.append(dsp)

    def get_dsp(self, name: str) -> Optional[DSPBidder]:
        for dsp in self.registered_dsps:
            if dsp.name == name:
                return dsp
        return None

    def run_auction(self, impression: Impression) -> Dict:
        """Run a single auction and return the full result."""
        start_time = time.perf_counter()
        bids: List[Dict] = []

        for dsp in self.registered_dsps:
            response_time = random.randint(5, 50)
            bid_amount = dsp.calculate_bid(impression)
            if bid_amount is not None and bid_amount >= impression.floor_price:
                bids.append(
                    {
                        "dsp": dsp.name,
                        "bid": bid_amount,
                        "response_time_ms": response_time,
                    }
                )

        total_bids = len(bids)
        if total_bids == 0:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "impression_id": impression.impression_id,
                "floor_price": impression.floor_price,
                "auction_type": self.auction_type,
                "total_bids": 0,
                "bids": [],
                "winner": None,
                "reason": "no_bids",
                "latency_ms": latency_ms,
                "timestamp": impression.timestamp.isoformat(),
            }

        sorted_bids = sorted(bids, key=lambda x: x["bid"], reverse=True)
        winner_bid = sorted_bids[0]

        if self.auction_type == "first_price":
            settlement_price = winner_bid["bid"]
        else:  # second_price
            settlement_price = (
                sorted_bids[1]["bid"] if len(sorted_bids) > 1 else winner_bid["bid"]
            )

        settlement_price = max(settlement_price, impression.floor_price)

        winning_dsp = self.get_dsp(winner_bid["dsp"])
        if winning_dsp:
            winning_dsp.budget_remaining -= settlement_price

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        return {
            "impression_id": impression.impression_id,
            "floor_price": impression.floor_price,
            "auction_type": self.auction_type,
            "total_bids": total_bids,
            "bids": sorted_bids,
            "winner": {
                "dsp": winner_bid["dsp"],
                "winning_bid": winner_bid["bid"],
                "settlement_price": settlement_price,
            },
            "reason": None,
            "latency_ms": latency_ms,
            "timestamp": impression.timestamp.isoformat(),
        }

    def _generate_impression(self, campaign_config: Dict) -> Impression:
        """Generate a random impression for batch simulations."""
        categories = {
            "gaming": (2.0, 5.0),
            "ecommerce": (5.0, 15.0),
            "news": (1.0, 3.0),
        }
        category = random.choice(list(categories.keys()))
        floor_cpm_low, floor_cpm_high = categories[category]
        floor_price = round(random.uniform(floor_cpm_low, floor_cpm_high) / 1000.0, 6)

        segments_pool = [
            "female",
            "male",
            "18-24",
            "25-34",
            "35-44",
            "tech_enthusiast",
            "fashion_lover",
            "gamer",
            "parent",
            "business_professional",
        ]
        user_segments = random.sample(segments_pool, k=random.randint(1, 4))

        device_type = random.choice(["mobile", "desktop", "tablet"])
        geo = random.choice(["tier1", "tier2", "tier3"])
        ad_format = random.choice(["banner_300x250", "native", "video_15s"])

        return Impression(
            impression_id=str(uuid.uuid4()),
            floor_price=floor_price,
            user_segments=user_segments,
            device_type=device_type,
            geo=geo,
            ad_format=ad_format,
            context_category=category,
        )

    def run_batch_auctions(self, count: int, campaign_config: Dict) -> List[Dict]:
        """Run many auctions and return all results."""
        results: List[Dict] = []
        for _ in range(count):
            impression = self._generate_impression(campaign_config)
            result = self.run_auction(impression)
            results.append(result)
        return results


def create_default_engine(auction_type: str = "second_price") -> AuctionEngine:
    """Factory for a default RTB engine with sample DSPs."""
    dsps = [
        DSPBidder(
            name="DSP_A",
            budget_remaining=10000.0,
            target_segments=["female", "25-34", "fashion_lover"],
            max_cpm=18.0,
            pacing_rate=1.0,
            bidding_strategy="aggressive",
        ),
        DSPBidder(
            name="DSP_B",
            budget_remaining=8000.0,
            target_segments=["tech_enthusiast", "gamer", "male"],
            max_cpm=15.0,
            pacing_rate=1.0,
            bidding_strategy="balanced",
        ),
        DSPBidder(
            name="DSP_C",
            budget_remaining=6000.0,
            target_segments=["parent", "business_professional", "35-44"],
            max_cpm=12.0,
            pacing_rate=1.0,
            bidding_strategy="conservative",
        ),
    ]
    return AuctionEngine(auction_type=auction_type, registered_dsps=dsps)
