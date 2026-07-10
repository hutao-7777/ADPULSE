"""Experiment simulator: generates realistic mock daily data for A/B tests."""

import random
import uuid
from datetime import date, timedelta
from typing import List

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExperimentDailyStat, Variant

# ── Simulation parameters ──────────────────────────────────────────
_DAILY_USERS_MIN = 800
_DAILY_USERS_MAX = 1500
_IMP_PER_USER_MIN = 2.5
_IMP_PER_USER_MAX = 4.0

_CONTROL_CTR_BASE = 0.025
_CONTROL_CTR_NOISE = 0.003
_CONTROL_CONV_BASE = 0.032
_CONTROL_CONV_NOISE = 0.004
_REVENUE_PER_CONV_MIN = 80.0
_REVENUE_PER_CONV_MAX = 200.0

_TREATMENT_LIFT_MIN = 1.05
_TREATMENT_LIFT_MAX = 1.25

_WEEKEND_DIP_MIN = 0.70
_WEEKEND_DIP_MAX = 0.85


class ExperimentSimulator:
    """Generates realistic daily experiment data."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    async def generate_history(
        self,
        experiment_id: uuid.UUID,
        variants: List[Variant],
        start_date: date,
        db: AsyncSession,
    ) -> None:
        """Generate daily stats from start_date up to today (inclusive)."""
        await db.execute(
            delete(ExperimentDailyStat).where(
                ExperimentDailyStat.experiment_id == experiment_id
            )
        )
        today = date.today()
        current = start_date
        while current <= today:
            await self._generate_one_day(experiment_id, variants, current, db)
            current += timedelta(days=1)
        await db.commit()

    async def generate_one_day(
        self,
        experiment_id: uuid.UUID,
        variants: List[Variant],
        target_date: date,
        db: AsyncSession,
    ) -> None:
        """Generate (or overwrite) stats for a single day."""
        await db.execute(
            delete(ExperimentDailyStat).where(
                ExperimentDailyStat.experiment_id == experiment_id,
                ExperimentDailyStat.date == target_date,
            )
        )
        await self._generate_one_day(experiment_id, variants, target_date, db)
        await db.commit()

    async def _generate_one_day(
        self,
        experiment_id: uuid.UUID,
        variants: List[Variant],
        target_date: date,
        db: AsyncSession,
    ) -> None:
        total_users = self._rng.randint(_DAILY_USERS_MIN, _DAILY_USERS_MAX)

        if target_date.weekday() >= 5:
            total_users = int(
                total_users * self._rng.uniform(_WEEKEND_DIP_MIN, _WEEKEND_DIP_MAX)
            )

        control_idx = next(
            (i for i, v in enumerate(variants) if v.name.lower() == "control"), 0
        )
        control = variants[control_idx]

        traffic_pcts = [v.traffic_pct for v in variants]
        total_pct = sum(traffic_pcts) or 100
        variant_users = [
            max(10, int(total_users * pct / total_pct)) for pct in traffic_pcts
        ]
        diff = total_users - sum(variant_users)
        if diff != 0 and variant_users:
            variant_users[0] += diff

        for idx, variant in enumerate(variants):
            users = variant_users[idx]
            is_control = variant.id == control.id

            imp_per_user = self._rng.uniform(_IMP_PER_USER_MIN, _IMP_PER_USER_MAX)
            impressions = int(users * imp_per_user)

            ctr = _CONTROL_CTR_BASE + self._rng.uniform(
                -_CONTROL_CTR_NOISE, _CONTROL_CTR_NOISE
            )
            if not is_control:
                lift = self._rng.uniform(_TREATMENT_LIFT_MIN, _TREATMENT_LIFT_MAX)
                lift += idx * 0.03
                ctr *= lift
            ctr = max(0.005, min(0.50, ctr))
            clicks = max(0, int(impressions * ctr))

            conv_rate = _CONTROL_CONV_BASE + self._rng.uniform(
                -_CONTROL_CONV_NOISE, _CONTROL_CONV_NOISE
            )
            if not is_control:
                lift = self._rng.uniform(_TREATMENT_LIFT_MIN, _TREATMENT_LIFT_MAX)
                lift += idx * 0.02
                conv_rate *= lift
            conv_rate = max(0.003, min(0.30, conv_rate))
            conversions = max(0, int(users * conv_rate))

            rev_per_conv = self._rng.uniform(
                _REVENUE_PER_CONV_MIN, _REVENUE_PER_CONV_MAX
            )
            revenue = round(conversions * rev_per_conv, 2)

            stat = ExperimentDailyStat(
                experiment_id=experiment_id,
                variant_id=variant.id,
                date=target_date,
                users=users,
                impressions=impressions,
                clicks=clicks,
                conversions=conversions,
                revenue=revenue,
            )
            db.add(stat)


experiment_simulator = ExperimentSimulator()
