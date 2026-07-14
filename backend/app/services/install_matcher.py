"""Install attribution matching engine - click-to-install matching + multi-touch."""

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ClickEvent, ConversionEvent, Touchpoint


class InstallMatcher:
    """Match conversion/install events to click/impression events for attribution."""

    DEFAULT_CLICK_WINDOW_HOURS = 168  # 7 days
    DEFAULT_VIEW_WINDOW_HOURS = 24  # 1 day

    async def match_conversion(
        self,
        db: AsyncSession,
        conversion: ConversionEvent,
        click_window_hours: int = DEFAULT_CLICK_WINDOW_HOURS,
        view_window_hours: int = DEFAULT_VIEW_WINDOW_HOURS,
        model: str = "last_click",
    ) -> Optional[str]:
        """Match a conversion to clicks/impressions and return the attributed
        network name.
        """
        device_id = conversion.device_id
        if not device_id:
            return None

        conversion_time = conversion.created_at
        click_start = conversion_time - timedelta(hours=click_window_hours)

        # Find matching clicks
        result = await db.execute(
            select(ClickEvent)
            .where(ClickEvent.device_id == device_id)
            .where(ClickEvent.created_at.between(click_start, conversion_time))
            .order_by(ClickEvent.created_at.desc())
        )
        clicks: List[ClickEvent] = list(result.scalars().all())

        if not clicks:
            return None

        # Apply attribution model
        if model == "last_click":
            winner = clicks[0]
        elif model == "first_click":
            winner = clicks[-1]
        else:
            winner = clicks[0]  # default to last-click

        attributed_network = winner.network_name

        # Create touchpoints for multi-touch
        for i, click in enumerate(clicks):
            tp = Touchpoint(
                user_id=device_id,
                ad_unit_id=click.ad_unit_id,
                touchpoint_seq=i + 1,
                channel=click.network_name or "unknown",
                event_type="click",
                event_time=click.created_at,
                conversion_event_id=conversion.id,
                cost=0.0,
            )
            db.add(tp)

        return attributed_network

    async def match_all_pending(
        self,
        db: AsyncSession,
        click_window_hours: int = DEFAULT_CLICK_WINDOW_HOURS,
        view_window_hours: int = DEFAULT_VIEW_WINDOW_HOURS,
    ) -> int:
        """Match all unattributed conversions."""
        result = await db.execute(
            select(ConversionEvent).where(ConversionEvent.attributed_network.is_(None))
        )
        conversions: List[ConversionEvent] = list(result.scalars().all())
        matched = 0

        for cv in conversions:
            network = await self.match_conversion(
                db, cv, click_window_hours, view_window_hours
            )
            if network:
                cv.attributed_network = network
                cv.attribution_model = "last_click"
                matched += 1

        if matched > 0:
            await db.commit()

        return matched

    async def get_report(
        self,
        db: AsyncSession,
        publisher_id: Optional[uuid.UUID] = None,
        days: int = 7,
    ) -> Dict:
        """Aggregate attribution report by network."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await db.execute(
            select(ConversionEvent)
            .where(ConversionEvent.created_at >= since)
            .where(ConversionEvent.attributed_network.isnot(None))
        )
        conversions: List[ConversionEvent] = list(result.scalars().all())

        by_network: Dict[str, Dict] = {}
        for cv in conversions:
            net = cv.attributed_network or "unknown"
            if net not in by_network:
                by_network[net] = {"conversions": 0, "revenue": 0.0}
            by_network[net]["conversions"] += 1
            by_network[net]["revenue"] += cv.event_value

        return {
            "total_conversions": len(conversions),
            "total_revenue": sum(cv.event_value for cv in conversions),
            "by_network": by_network,
        }

    async def compare_models(
        self,
        db: AsyncSession,
        conversion: ConversionEvent,
        click_window_hours: int = DEFAULT_CLICK_WINDOW_HOURS,
    ) -> Dict[str, Dict[str, float]]:
        """Run multi-touch attribution comparison on a single conversion."""
        device_id = conversion.device_id
        if not device_id:
            return {}

        conversion_time = conversion.created_at
        click_start = conversion_time - timedelta(hours=click_window_hours)

        result = await db.execute(
            select(ClickEvent)
            .where(ClickEvent.device_id == device_id)
            .where(ClickEvent.created_at.between(click_start, conversion_time))
            .order_by(ClickEvent.created_at.asc())
        )
        clicks: List[ClickEvent] = list(result.scalars().all())
        if not clicks:
            return {}

        n = len(clicks)
        channels = [c.network_name or "unknown" for c in clicks]
        results: Dict[str, Dict[str, float]] = {}

        # Last Click
        results["last_click"] = defaultdict(float)
        results["last_click"][channels[-1]] = 1.0

        # First Click
        results["first_click"] = defaultdict(float)
        results["first_click"][channels[0]] = 1.0

        # Linear
        results["linear"] = defaultdict(float)
        share = 1.0 / n
        for ch in channels:
            results["linear"][ch] += share

        # Time Decay
        results["time_decay"] = defaultdict(float)
        max_time = clicks[-1].created_at
        total_weight = 0.0
        weights = []
        for click in clicks:
            hours_ago = (max_time - click.created_at).total_seconds() / 3600.0
            w = 2 ** (-hours_ago / 168.0)  # 7-day half-life
            weights.append(w)
            total_weight += w
        for ch, w in zip(channels, weights):
            results["time_decay"][ch] += w / total_weight if total_weight > 0 else 0

        return {model: dict(ch) for model, ch in results.items()}
