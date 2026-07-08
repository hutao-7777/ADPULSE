"""A/B testing engine with statistical inference."""

import asyncio
import hashlib
import math
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple, cast

import numpy as np
from scipy import stats
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ABTest, ABTestVariant


class ABTestEngine:
    """A/B test lifecycle, assignment, event recording and inference engine."""

    _BUCKET_SIZE = 10_000

    def __init__(self) -> None:
        # Per-test lock to serialize event recording
        self._locks: Dict[uuid.UUID, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._history: Dict[
            uuid.UUID, Dict[str, List[Tuple[datetime, float, float]]]
        ] = defaultdict(lambda: defaultdict(list))

    def _user_bucket(self, test_id: uuid.UUID, user_id: str, salt: str = "") -> int:
        key = f"{str(test_id)}:{user_id}:{salt}".encode("utf-8")
        digest = hashlib.md5(key).hexdigest()
        return int(digest, 16) % self._BUCKET_SIZE

    async def create_test(
        self,
        db: AsyncSession,
        name: str,
        campaign_id: uuid.UUID,
        metric_target: str,
        traffic_split: float,
        variants_config: List[Dict],
    ) -> Dict:
        """Create an A/B test with its variants."""
        total_pct = sum(v["traffic_pct"] for v in variants_config)
        if not (0.99 <= total_pct <= 1.01):
            raise ValueError("Variant traffic percentages must sum to 1.0")

        test = ABTest(
            id=uuid.uuid4(),
            name=name,
            campaign_id=campaign_id,
            status="draft",
            traffic_split=traffic_split,
            metric_target=metric_target,
        )
        db.add(test)
        await db.flush()

        variants = []
        for cfg in variants_config:
            variant = ABTestVariant(
                id=uuid.uuid4(),
                ab_test_id=test.id,
                name=cfg["name"],
                traffic_pct=cfg["traffic_pct"],
            )
            db.add(variant)
            variants.append(variant)

        await db.commit()
        await db.refresh(test)

        return {
            "id": test.id,
            "name": test.name,
            "campaign_id": test.campaign_id,
            "status": test.status,
            "traffic_split": test.traffic_split,
            "metric_target": test.metric_target,
            "variants": [
                {
                    "id": v.id,
                    "name": v.name,
                    "traffic_pct": v.traffic_pct,
                }
                for v in variants
            ],
        }

    async def _get_test_and_variants(
        self, db: AsyncSession, test_id: uuid.UUID
    ) -> Tuple[Optional[ABTest], List[ABTestVariant]]:
        result = await db.execute(select(ABTest).where(ABTest.id == test_id))
        test = result.scalar_one_or_none()
        if test is None:
            return None, []
        variants_result = await db.execute(
            select(ABTestVariant).where(ABTestVariant.ab_test_id == test_id)
        )
        variants = list(variants_result.scalars().all())
        return test, variants

    async def assign_user(
        self, db: AsyncSession, test_id: uuid.UUID, user_id: str
    ) -> Optional[Tuple[str, bool]]:
        """Assign a user to a variant.

        Returns (variant_name, in_experiment). Returns None if the test is not running.
        """
        test, variants = await self._get_test_and_variants(db, test_id)
        if test is None or test.status != "running":
            return None
        if not variants:
            return None

        control_variant = next(
            (v for v in variants if v.name.lower() == "control"), variants[0]
        )

        bucket = self._user_bucket(test_id, user_id)
        experiment_threshold = int(test.traffic_split * self._BUCKET_SIZE)

        if bucket >= experiment_threshold:
            return control_variant.name, False

        # Normalize assignment within experiment traffic
        normalized = bucket / experiment_threshold if experiment_threshold > 0 else 0.0
        cumulative = 0.0
        for variant in variants:
            cumulative += variant.traffic_pct
            if normalized < cumulative:
                return variant.name, True
        return variants[-1].name, True

    async def record_event(
        self,
        db: AsyncSession,
        test_id: uuid.UUID,
        variant_name: str,
        event_type: str,
        revenue: Optional[float] = None,
    ) -> None:
        """Record an event for a variant under a per-test lock."""
        test, variants = await self._get_test_and_variants(db, test_id)
        if test is None:
            raise ValueError("Test not found")
        if test.status != "running":
            raise ValueError("Test is not running")

        variant = next((v for v in variants if v.name == variant_name), None)
        if variant is None:
            raise ValueError(f"Variant {variant_name} not found")

        async with self._locks[test_id]:
            column_map = {
                "impression": ABTestVariant.impressions,
                "click": ABTestVariant.clicks,
                "conversion": ABTestVariant.conversions,
            }

            if event_type in column_map:
                column = column_map[event_type]
                await db.execute(
                    update(ABTestVariant)
                    .where(ABTestVariant.id == variant.id)
                    .values({column: column + 1})
                )
            elif event_type == "revenue":
                if revenue is None:
                    raise ValueError("Revenue value is required for revenue events")
                await db.execute(
                    update(ABTestVariant)
                    .where(ABTestVariant.id == variant.id)
                    .values({ABTestVariant.revenue: ABTestVariant.revenue + revenue})
                )
            else:
                raise ValueError(f"Unsupported event type: {event_type}")

            await db.commit()
            await db.refresh(variant)

            # Refresh anomaly history
            await self._update_history(db, test, variant)

    async def _update_history(
        self, db: AsyncSession, test: ABTest, variant: ABTestVariant
    ) -> None:
        """Append current metric snapshot for anomaly detection."""
        ctr = variant.clicks / variant.impressions if variant.impressions > 0 else 0.0
        cr = variant.conversions / variant.clicks if variant.clicks > 0 else 0.0
        self._history[test.id][variant.name].append((datetime.utcnow(), ctr, cr))

    def _build_samples(self, variant: ABTestVariant, metric: str) -> np.ndarray:
        """Build a single sample array for a variant based on the metric."""
        if metric == "ctr":
            n = variant.impressions
            successes = variant.clicks
        elif metric == "conversion_rate":
            n = variant.clicks
            successes = variant.conversions
        elif metric == "roi":
            n = variant.impressions
            successes = variant.conversions
        else:
            raise ValueError(f"Unsupported metric: {metric}")

        arr = np.zeros(n, dtype=np.float64)
        if successes > 0:
            if metric == "roi" and variant.revenue > 0:
                value = variant.revenue / successes
                arr[:successes] = value
            else:
                arr[:successes] = 1.0
        return arr

    def _proportion_stats(self, n: int, successes: int) -> Tuple[float, float]:
        p = successes / n if n > 0 else 0.0
        var = p * (1 - p) / n if n > 0 else 0.0
        return p, var

    def _power_for_proportions(
        self, n1: int, p1: float, n2: int, p2: float, alpha: float = 0.05
    ) -> float:
        """Approximate power for a two-sided two-proportion z-test."""
        if n1 == 0 or n2 == 0:
            return 0.0
        delta = abs(p1 - p2)
        if delta == 0:
            return 0.0
        se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
        if se == 0:
            return 1.0
        z = delta / se
        z_alpha = stats.norm.ppf(1 - alpha / 2)
        beta = stats.norm.cdf(z_alpha - z)
        return float(1 - beta)

    async def get_results(self, db: AsyncSession, test_id: uuid.UUID) -> Dict:
        """Compute full statistical results for every variant versus control."""
        test, variants = await self._get_test_and_variants(db, test_id)
        if test is None:
            raise ValueError("Test not found")

        control = next((v for v in variants if v.name.lower() == "control"), None)
        if control is None:
            raise ValueError("No control variant found")

        control_samples = self._build_samples(control, test.metric_target)
        control_ctr = (
            control.clicks / control.impressions if control.impressions > 0 else 0.0
        )
        control_cr = control.conversions / control.clicks if control.clicks > 0 else 0.0

        variant_stats = []
        best_variant: Optional[ABTestVariant] = None
        best_p_value = 1.0
        significant_lift = False

        for variant in variants:
            samples = self._build_samples(variant, test.metric_target)
            n = len(samples)

            if test.metric_target == "ctr":
                metric_value = (
                    variant.clicks / variant.impressions
                    if variant.impressions > 0
                    else 0.0
                )
                baseline_value = control_ctr
                n_baseline = control.impressions
            elif test.metric_target == "conversion_rate":
                metric_value = (
                    variant.conversions / variant.clicks if variant.clicks > 0 else 0.0
                )
                baseline_value = control_cr
                n_baseline = control.clicks
            else:  # roi
                metric_value = (
                    variant.revenue / variant.impressions
                    if variant.impressions > 0
                    else 0.0
                )
                baseline_value = (
                    control.revenue / control.impressions
                    if control.impressions > 0
                    else 0.0
                )
                n_baseline = control.impressions

            # t-test on synthetic binary/revenue samples
            if len(control_samples) > 0 and n > 0 and baseline_value != metric_value:
                _, p_value = stats.ttest_ind(control_samples, samples, equal_var=False)
                p_value = float(p_value) if not math.isnan(p_value) else 1.0
            else:
                p_value = 1.0

            # Confidence interval for difference in means/proportions
            diff = metric_value - baseline_value
            if len(control_samples) > 0 and n > 0:
                se = math.sqrt(
                    baseline_value * (1 - baseline_value) / max(len(control_samples), 1)
                    + metric_value * (1 - metric_value) / max(n, 1)
                )
            else:
                se = 0.0
            margin = 1.96 * se
            ci = [diff - margin, diff + margin]

            # Lift vs control
            lift_pct = (
                ((metric_value - baseline_value) / baseline_value * 100.0)
                if baseline_value > 0
                else 0.0
            )

            # Power
            power = self._power_for_proportions(
                n_baseline, baseline_value, n, metric_value
            )

            is_significant = p_value < 0.05
            sample_size_reached = n >= 1000

            if is_significant and p_value < best_p_value:
                best_p_value = p_value
                best_variant = variant
                significant_lift = lift_pct > 0

            variant_stats.append(
                {
                    "name": variant.name,
                    "traffic_pct": variant.traffic_pct,
                    "impressions": variant.impressions,
                    "clicks": variant.clicks,
                    "conversions": variant.conversions,
                    "revenue": variant.revenue,
                    "ctr": (
                        variant.clicks / variant.impressions
                        if variant.impressions > 0
                        else 0.0
                    ),
                    "conversion_rate": (
                        variant.conversions / variant.clicks
                        if variant.clicks > 0
                        else 0.0
                    ),
                    "roi": (
                        variant.revenue / variant.impressions
                        if variant.impressions > 0
                        else 0.0
                    ),
                    "lift_pct": lift_pct,
                    "p_value": p_value,
                    "is_significant": is_significant,
                    "sample_size_reached": sample_size_reached,
                    "confidence_interval": ci,
                    "power": power,
                }
            )

        if best_variant and significant_lift:
            recommendation = (
                f"{best_variant.name} 显著优于 control (p={best_p_value:.4f})"
            )
        elif best_variant and not significant_lift:
            recommendation = "control 更优"
        else:
            recommendation = "继续观察"

        days_running = 0
        if test.start_date:
            days_running = max(0, (datetime.utcnow() - test.start_date).days)

        return {
            "test_info": {
                "name": test.name,
                "status": test.status,
                "metric_target": test.metric_target,
                "start_date": test.start_date.isoformat() if test.start_date else None,
                "days_running": days_running,
            },
            "variants": variant_stats,
            "recommendation": recommendation,
        }

    async def check_anomaly(
        self, db: AsyncSession, test_id: uuid.UUID
    ) -> Optional[Dict]:
        """Detect metric anomalies using a sliding mean ± 3σ window."""
        test, variants = await self._get_test_and_variants(db, test_id)
        if test is None:
            raise ValueError("Test not found")

        alerts = []
        for variant in variants:
            history = self._history.get(test_id, {}).get(variant.name, [])
            if len(history) < 10:
                continue

            for metric_idx, metric_name in enumerate(["ctr", "conversion_rate"]):
                values = cast(List[float], [h[metric_idx + 1] for h in history])
                mean = float(np.mean(values[:-1]))
                std = float(np.std(values[:-1]))
                current = values[-1]
                lower = mean - 3 * std
                upper = mean + 3 * std

                if current < lower or current > upper:
                    severity = (
                        "critical" if abs(current - mean) > 5 * std else "warning"
                    )
                    alerts.append(
                        {
                            "variant": variant.name,
                            "metric": metric_name,
                            "current_value": current,
                            "expected_range": [lower, upper],
                            "severity": severity,
                        }
                    )

        return alerts[0] if alerts else None
