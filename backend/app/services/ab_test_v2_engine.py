"""Production A/B testing engine.

Features:
- Consistent hash assignment: hash(user_id + experiment_id) % 100.
- Two-sample t-test and Mann-Whitney U test.
- Power analysis, MDE, confidence intervals, p-values.
- Sample size estimation.
"""

import hashlib
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Assignment, Experiment, ExperimentMetric, Variant


@dataclass
class VariantStats:
    """Statistical summary for a variant."""

    variant_id: str
    name: str
    traffic_pct: float
    n: int
    mean: float
    std: float
    sum_value: float


@dataclass
class VariantComparison:
    """Comparison of a treatment variant against control."""

    variant_name: str
    control_name: str
    n_treatment: int
    n_control: int
    mean_treatment: float
    mean_control: float
    diff: float
    relative_lift_pct: float
    p_value_ttest: float
    p_value_mannwhitney: float
    confidence_interval_95: Tuple[float, float]
    power: float
    mde_absolute: float
    recommended_sample_size: int
    is_significant: bool


class ABTestV2Engine:
    """Production A/B test engine with rigorous statistical inference."""

    def _hash_bucket(self, user_id: str, experiment_id: uuid.UUID) -> int:
        """Consistent hash bucket in [0, 99]."""
        key = f"{user_id}:{experiment_id}".encode("utf-8")
        digest = hashlib.md5(key).hexdigest()
        return int(digest, 16) % 100

    async def assign_user(
        self,
        db: AsyncSession,
        experiment_id: uuid.UUID,
        user_id: str,
    ) -> Optional[Tuple[Variant, bool]]:
        """Assign a user to a variant.

        Returns (variant, in_experiment). Returns None if experiment is not running.
        """
        experiment = await db.get(Experiment, experiment_id)
        if experiment is None or experiment.status != "running":
            return None

        variants_result = await db.execute(
            select(Variant).where(Variant.experiment_id == experiment_id)
        )
        variants = list(variants_result.scalars().all())
        if not variants:
            return None

        # Check existing assignment.
        existing = await db.execute(
            select(Assignment)
            .where(Assignment.experiment_id == experiment_id)
            .where(Assignment.user_id == user_id)
        )
        assignment = existing.scalar_one_or_none()
        if assignment:
            variant = next(
                (v for v in variants if v.id == assignment.variant_id), variants[0]
            )
            return variant, True

        bucket = self._hash_bucket(user_id, experiment_id)
        if bucket >= experiment.traffic_allocation:
            # User is outside the experiment; return control experience.
            control = next(
                (v for v in variants if v.name.lower() == "control"), variants[0]
            )
            return control, False

        # Map bucket to variant based on traffic_pct.
        normalized = bucket / experiment.traffic_allocation
        cumulative = 0.0
        selected = variants[-1]
        for variant in variants:
            cumulative += variant.traffic_pct
            if normalized < cumulative:
                selected = variant
                break

        # Persist assignment.
        assignment = Assignment(
            experiment_id=experiment_id,
            variant_id=selected.id,
            user_id=user_id,
            bucket=bucket,
        )
        db.add(assignment)
        await db.commit()

        return selected, True

    async def record_metric(
        self,
        db: AsyncSession,
        experiment_id: uuid.UUID,
        variant_name: str,
        user_id: str,
        metric_name: str,
        metric_value: float,
    ) -> None:
        """Record a metric event for a user/variant."""
        experiment = await db.get(Experiment, experiment_id)
        if experiment is None or experiment.status != "running":
            raise ValueError("Experiment not found or not running")

        variant_result = await db.execute(
            select(Variant)
            .where(Variant.experiment_id == experiment_id)
            .where(Variant.name == variant_name)
        )
        variant = variant_result.scalar_one_or_none()
        if variant is None:
            raise ValueError(f"Variant {variant_name} not found")

        metric = ExperimentMetric(
            experiment_id=experiment_id,
            variant_id=variant.id,
            user_id=user_id,
            metric_name=metric_name,
            metric_value=metric_value,
            event_time=datetime.now(timezone.utc),
        )
        db.add(metric)
        await db.commit()

    async def _fetch_variant_samples(
        self,
        db: AsyncSession,
        experiment_id: uuid.UUID,
        metric_name: str,
    ) -> Dict[str, np.ndarray]:
        """Return metric samples grouped by variant name."""
        result = await db.execute(
            select(ExperimentMetric)
            .where(ExperimentMetric.experiment_id == experiment_id)
            .where(ExperimentMetric.metric_name == metric_name)
        )
        metrics = result.scalars().all()

        samples: Dict[str, List[float]] = {}
        for m in metrics:
            variant = await db.get(Variant, m.variant_id)
            if variant is None:
                continue
            samples.setdefault(variant.name, []).append(m.metric_value)

        return {name: np.array(values, dtype=float) for name, values in samples.items()}

    def _variant_stats(self, samples: np.ndarray) -> VariantStats:
        """Compute descriptive statistics for a sample array."""
        return VariantStats(
            variant_id="",
            name="",
            traffic_pct=0.0,
            n=len(samples),
            mean=float(np.mean(samples)) if len(samples) else 0.0,
            std=float(np.std(samples, ddof=1)) if len(samples) > 1 else 0.0,
            sum_value=float(np.sum(samples)) if len(samples) else 0.0,
        )

    def _ttest(self, control: np.ndarray, treatment: np.ndarray) -> float:
        """Two-sample t-test p-value (unequal variance)."""
        if len(control) < 2 or len(treatment) < 2:
            return 1.0
        _, p_value = stats.ttest_ind(control, treatment, equal_var=False)
        return float(p_value) if not math.isnan(p_value) else 1.0

    def _mann_whitney(self, control: np.ndarray, treatment: np.ndarray) -> float:
        """Mann-Whitney U test p-value (non-parametric)."""
        if len(control) < 2 or len(treatment) < 2:
            return 1.0
        try:
            _, p_value = stats.mannwhitneyu(control, treatment, alternative="two-sided")
            return float(p_value)
        except ValueError:
            return 1.0

    def _confidence_interval(
        self, control: np.ndarray, treatment: np.ndarray, confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Confidence interval for the difference in means."""
        n1, n2 = len(control), len(treatment)
        if n1 < 2 or n2 < 2:
            return (0.0, 0.0)
        mean1, mean2 = float(np.mean(control)), float(np.mean(treatment))
        var1 = float(np.var(control, ddof=1)) if n1 > 1 else 0.0
        var2 = float(np.var(treatment, ddof=1)) if n2 > 1 else 0.0
        se = math.sqrt(var1 / n1 + var2 / n2)
        alpha = 1 - confidence
        z = stats.norm.ppf(1 - alpha / 2)
        diff = mean2 - mean1
        margin = z * se
        return (diff - margin, diff + margin)

    def _power(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        alpha: float = 0.05,
    ) -> float:
        """Approximate power of a two-sample z-test for the observed effect."""
        n1, n2 = len(control), len(treatment)
        if n1 < 2 or n2 < 2:
            return 0.0
        p1 = float(np.mean(control))
        p2 = float(np.mean(treatment))
        delta = abs(p2 - p1)
        if delta == 0:
            return 0.0
        se = math.sqrt(p1 * (1 - p1) / max(n1, 1) + p2 * (1 - p2) / max(n2, 1))
        if se == 0:
            return 1.0
        z = delta / se
        z_alpha = stats.norm.ppf(1 - alpha / 2)
        return float(1 - stats.norm.cdf(z_alpha - z))

    def _mde_absolute(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        alpha: float = 0.05,
        beta: float = 0.2,
    ) -> float:
        """Minimum Detectable Effect (absolute) given current variance."""
        n1, n2 = len(control), len(treatment)
        if n1 < 2 or n2 < 2:
            return 0.0
        var1 = float(np.var(control, ddof=1)) if n1 > 1 else 0.0
        var2 = float(np.var(treatment, ddof=1)) if n2 > 1 else 0.0
        pooled_se = math.sqrt(var1 / n1 + var2 / n2)
        z_alpha = float(stats.norm.ppf(1 - alpha / 2))
        z_beta = float(stats.norm.ppf(1 - beta))
        return (z_alpha + z_beta) * pooled_se

    def _sample_size_per_variant(
        self,
        baseline_mean: float,
        baseline_std: float,
        mde: float,
        alpha: float = 0.05,
        power: float = 0.8,
    ) -> int:
        """Required sample size per variant for a two-sided t-test."""
        if baseline_std <= 0 or mde <= 0:
            return 0
        z_alpha = float(stats.norm.ppf(1 - alpha / 2))
        z_beta = float(stats.norm.ppf(power))
        n = 2 * ((baseline_std * (z_alpha + z_beta) / mde) ** 2)
        return int(math.ceil(n))

    async def analyze(
        self,
        db: AsyncSession,
        experiment_id: uuid.UUID,
        metric_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run full statistical analysis for an experiment."""
        experiment = await db.get(Experiment, experiment_id)
        if experiment is None:
            raise ValueError("Experiment not found")

        metric = metric_name or experiment.metric_name
        samples = await self._fetch_variant_samples(db, experiment_id, metric)

        control_name: Optional[str] = "control"
        if control_name not in samples:
            # Fallback: first variant alphabetical.
            control_name = sorted(samples.keys())[0] if samples else None

        if control_name is None or control_name not in samples:
            raise ValueError("No control variant found")

        control_samples = samples[control_name]
        control_stats = self._variant_stats(control_samples)

        comparisons: List[VariantComparison] = []
        for variant_name, variant_samples in samples.items():
            if variant_name == control_name:
                continue

            treatment_stats = self._variant_stats(variant_samples)
            diff = treatment_stats.mean - control_stats.mean
            relative_lift = (
                (diff / control_stats.mean * 100.0) if control_stats.mean != 0 else 0.0
            )
            ci = self._confidence_interval(control_samples, variant_samples)
            p_ttest = self._ttest(control_samples, variant_samples)
            p_mw = self._mann_whitney(control_samples, variant_samples)
            power = self._power(control_samples, variant_samples)
            mde = self._mde_absolute(control_samples, variant_samples)
            sample_size = self._sample_size_per_variant(
                control_stats.mean, control_stats.std, mde
            )

            comparisons.append(
                VariantComparison(
                    variant_name=variant_name,
                    control_name=control_name,
                    n_treatment=treatment_stats.n,
                    n_control=control_stats.n,
                    mean_treatment=treatment_stats.mean,
                    mean_control=control_stats.mean,
                    diff=diff,
                    relative_lift_pct=relative_lift,
                    p_value_ttest=p_ttest,
                    p_value_mannwhitney=p_mw,
                    confidence_interval_95=ci,
                    power=power,
                    mde_absolute=mde,
                    recommended_sample_size=sample_size,
                    is_significant=p_ttest < 0.05,
                )
            )

        return {
            "experiment_id": str(experiment_id),
            "metric": metric,
            "control": {
                "name": control_name,
                "n": control_stats.n,
                "mean": control_stats.mean,
                "std": control_stats.std,
            },
            "comparisons": [c.__dict__ for c in comparisons],
        }
