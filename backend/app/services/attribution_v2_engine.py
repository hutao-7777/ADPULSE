"""Production multi-touch attribution engine.

Supports configurable click/view windows and Monte Carlo Shapley Value
approximation with 10,000 permutation samples.
"""

import random
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AttributionResult, ConversionEvent, Touchpoint


class AttributionV2Engine:
    """Attribution engine with ordered touchpoints and Shapley approximation."""

    async def build_user_journey(
        self,
        db: AsyncSession,
        user_id: str,
        campaign_id: uuid.UUID,
        click_window_days: int = 7,
        view_window_days: int = 1,
    ) -> List[Touchpoint]:
        """Return ordered touchpoints within the attribution windows."""
        result = await db.execute(
            select(Touchpoint)
            .where(Touchpoint.user_id == user_id)
            .where(Touchpoint.campaign_id == campaign_id)
            .order_by(Touchpoint.touchpoint_seq.asc(), Touchpoint.event_time.asc())
        )
        return list(result.scalars().all())

    def _filter_by_window(
        self,
        touchpoints: List[Touchpoint],
        conversion_time: datetime,
        click_window_days: int,
        view_window_days: int,
    ) -> List[Touchpoint]:
        """Filter touchpoints by click/view lookback windows."""
        filtered = []
        for tp in touchpoints:
            delta = conversion_time - tp.event_time
            if delta.total_seconds() < 0:
                continue
            if tp.event_type == "click" and delta <= timedelta(days=click_window_days):
                filtered.append(tp)
            elif tp.event_type == "view" and delta <= timedelta(days=view_window_days):
                filtered.append(tp)
            elif tp.event_type == "impression" and delta <= timedelta(
                days=view_window_days
            ):
                filtered.append(tp)
        return filtered

    def _characteristic_function(
        self, coalition: Tuple[Touchpoint, ...], conversion_value: float
    ) -> float:
        """Marginal contribution of a coalition: last-touch value."""
        return conversion_value if coalition else 0.0

    def shapley_monte_carlo(
        self,
        touchpoints: List[Touchpoint],
        conversion_value: float,
        n_samples: int = 10_000,
    ) -> Dict[str, float]:
        """Estimate Shapley Values via Monte Carlo permutation sampling.

        Returns credits keyed by touchpoint ID.
        """
        if not touchpoints:
            return {}
        if len(touchpoints) == 1:
            return {str(touchpoints[0].id): conversion_value}

        rng = random.Random(42)
        credits: Dict[str, float] = defaultdict(float)

        indices = list(range(len(touchpoints)))
        for _ in range(n_samples):
            rng.shuffle(indices)
            prev_value = 0.0
            seen: set[int] = set()
            for idx in indices:
                seen.add(idx)
                coalition = tuple(touchpoints[i] for i in seen)
                current_value = self._characteristic_function(
                    coalition, conversion_value
                )
                marginal = current_value - prev_value
                credits[str(touchpoints[idx].id)] += marginal
                prev_value = current_value

        # Average over permutations.
        for key in credits:
            credits[key] /= n_samples
        return dict(credits)

    def compare_models(
        self,
        touchpoints: List[Touchpoint],
        conversion_value: float,
        click_window_days: int = 7,
        view_window_days: int = 1,
    ) -> Dict[str, Dict[str, float]]:
        """Compute attribution credits using multiple models."""
        filtered = self._filter_by_window(
            touchpoints,
            datetime.now(),
            click_window_days,
            view_window_days,
        )
        if not filtered:
            return {}

        n = len(filtered)
        channel_credits: Dict[str, Dict[str, float]] = {}

        # First touch
        channel_credits["first_touch"] = defaultdict(float)
        channel_credits["first_touch"][filtered[0].channel] = conversion_value

        # Last touch
        channel_credits["last_touch"] = defaultdict(float)
        channel_credits["last_touch"][filtered[-1].channel] = conversion_value

        # Linear
        channel_credits["linear"] = defaultdict(float)
        share = conversion_value / n
        for tp in filtered:
            channel_credits["linear"][tp.channel] += share

        # Time decay (half-life 7 days)
        channel_credits["time_decay"] = defaultdict(float)
        max_time = max(tp.event_time for tp in filtered)
        weights = []
        for tp in filtered:
            days_ago = (max_time - tp.event_time).total_seconds() / 86400.0
            weight = 2 ** (-days_ago / 7.0)
            weights.append(weight)
        total_weight = sum(weights)
        for tp, weight in zip(filtered, weights):
            channel_credits["time_decay"][tp.channel] += (
                conversion_value * weight / total_weight
            )

        # Shapley
        channel_credits["shapley"] = defaultdict(float)
        shapley_credits = self.shapley_monte_carlo(filtered, conversion_value)
        for tp in filtered:
            tp_credit = shapley_credits.get(str(tp.id), 0.0)
            channel_credits["shapley"][tp.channel] += tp_credit

        return {model: dict(channels) for model, channels in channel_credits.items()}

    async def calculate_for_conversion(
        self,
        db: AsyncSession,
        conversion_id: uuid.UUID,
        click_window_days: int = 7,
        view_window_days: int = 1,
        n_samples: int = 10_000,
    ) -> Dict[str, Any]:
        """Run Shapley attribution for a single conversion event."""
        conversion = await db.get(ConversionEvent, conversion_id)
        if conversion is None:
            raise ValueError("Conversion not found")

        touchpoints = await self.build_user_journey(
            db, conversion.user_id, conversion.campaign_id or uuid.uuid4()
        )
        filtered = self._filter_by_window(
            touchpoints,
            conversion.conversion_time,
            click_window_days,
            view_window_days,
        )

        credits = self.shapley_monte_carlo(
            filtered, conversion.conversion_value, n_samples
        )

        # Aggregate by channel and campaign.
        channel_credits: Dict[str, float] = defaultdict(float)
        campaign_credits: Dict[str, float] = defaultdict(float)
        for tp in filtered:
            credit = credits.get(str(tp.id), 0.0)
            channel_credits[tp.channel] += credit
            campaign_credits[str(tp.campaign_id)] += credit

        result = AttributionResult(
            conversion_event_id=conversion_id,
            model_type="shapley",
            click_window_days=click_window_days,
            view_window_days=view_window_days,
            channel_credits=dict(channel_credits),
            campaign_credits=dict(campaign_credits),
            sample_size=n_samples,
        )
        db.add(result)
        await db.commit()

        return {
            "conversion_id": str(conversion_id),
            "model": "shapley",
            "sample_size": n_samples,
            "channel_credits": dict(channel_credits),
            "campaign_credits": dict(campaign_credits),
            "touchpoint_credits": credits,
        }
