"""Traffic quality scoring and fraud detection engine."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FraudAlert, TrafficQualityScore
from app.models.base import utc_now


class TrafficQualityEngine:
    """Evaluate traffic quality and detect anomalous / fraudulent patterns."""

    GRADE_PREMIUM = "premium"
    GRADE_STANDARD = "standard"
    GRADE_LOW = "low"
    GRADE_FRAUD = "fraud"

    def _clamp(self, value: float, low: float = 0.0, high: float = 100.0) -> float:
        return max(low, min(high, value))

    def _score_ctr(self, ctr: float) -> float:
        """Benchmark CTR = 0.02, healthy range [0.01, 0.05]."""
        if 0.01 <= ctr <= 0.05:
            return 100.0
        if ctr < 0.01:
            return self._clamp(ctr / 0.01 * 100.0)
        return self._clamp(100.0 - (ctr - 0.05) / 0.05 * 100.0)

    def _score_cvr(self, cvr: float) -> float:
        """Benchmark CVR = 0.10, healthy range [0.05, 0.20]."""
        if 0.05 <= cvr <= 0.20:
            return 100.0
        if cvr < 0.05:
            return self._clamp(cvr / 0.05 * 100.0)
        return self._clamp(100.0 - (cvr - 0.20) / 0.20 * 100.0)

    def _score_bounce(self, bounce_rate: float) -> float:
        if bounce_rate <= 0.5:
            return 100.0
        if bounce_rate >= 0.9:
            return 0.0
        return 100.0 - (bounce_rate - 0.5) / 0.4 * 100.0

    def _score_dwell(self, avg_dwell_sec: float) -> float:
        if avg_dwell_sec >= 30.0:
            return 100.0
        if avg_dwell_sec <= 2.0:
            return 0.0
        return (avg_dwell_sec - 2.0) / 28.0 * 100.0

    def _score_interaction(self, interaction_rate: float) -> float:
        target = 0.30
        return self._clamp(interaction_rate / target * 100.0)

    def _detect_flags(self, raw_metrics: Dict) -> List[str]:
        flags: List[str] = []
        impressions = raw_metrics.get("impressions", 0)
        clicks = raw_metrics.get("clicks", 0)
        conversions = raw_metrics.get("conversions", 0)
        ctr = clicks / impressions if impressions > 0 else 0.0
        cvr = conversions / clicks if clicks > 0 else 0.0

        click_timestamps = raw_metrics.get("click_timestamps", [])
        if click_timestamps and len(click_timestamps) >= 4:
            sorted_ts = sorted(click_timestamps)
            for i in range(len(sorted_ts)):
                window_end = sorted_ts[i]
                count = sum(
                    1 for ts in sorted_ts if window_end - 60 <= ts <= window_end
                )
                if count > 3:
                    flags.append("suspect_bot")
                    break

        ip_distribution = raw_metrics.get("ip_distribution", {})
        if clicks == 0:
            for ip, count in ip_distribution.items():
                if count > 10:
                    flags.append("low_quality_ip")
                    break

        if ctr > 0.20 or ctr < 0.0001:
            flags.append("ctr_anomaly")

        if cvr > 0.50:
            flags.append("bot_suspect")

        night_ratio = raw_metrics.get("night_ratio", 0.0)
        if night_ratio > 0.5:
            flags.append("night_spike")

        return list(set(flags))

    def _map_grade(self, score: float) -> str:
        if score >= 90:
            return self.GRADE_PREMIUM
        if score >= 70:
            return self.GRADE_STANDARD
        if score >= 50:
            return self.GRADE_LOW
        return self.GRADE_FRAUD

    def assess_traffic(
        self,
        campaign_id: str | uuid.UUID,
        date: datetime,
        raw_metrics: Dict,
    ) -> Dict:
        """Compute traffic quality score from raw metrics."""
        impressions = raw_metrics.get("impressions", 0)
        clicks = raw_metrics.get("clicks", 0)
        conversions = raw_metrics.get("conversions", 0)
        bounce_count = raw_metrics.get("bounce_count", 0)
        total_dwell_sec = raw_metrics.get("total_dwell_sec", 0.0)
        interaction_events = raw_metrics.get("interaction_events", 0)
        unique_users = raw_metrics.get("unique_users", 1)

        ctr = clicks / impressions if impressions > 0 else 0.0
        cvr = conversions / clicks if clicks > 0 else 0.0
        bounce_rate = bounce_count / clicks if clicks > 0 else 0.0
        avg_dwell = total_dwell_sec / unique_users if unique_users > 0 else 0.0
        interaction_rate = interaction_events / impressions if impressions > 0 else 0.0

        ctr_score = self._score_ctr(ctr)
        cvr_score = self._score_cvr(cvr)
        bounce_score = self._score_bounce(bounce_rate)
        dwell_score = self._score_dwell(avg_dwell)
        interaction_score = self._score_interaction(interaction_rate)

        quality_score = (
            ctr_score * 0.2
            + cvr_score * 0.2
            + bounce_score * 0.2
            + dwell_score * 0.2
            + interaction_score * 0.2
        )
        quality_score = round(self._clamp(quality_score), 2)

        flags = self._detect_flags(raw_metrics)
        grade = self._map_grade(quality_score)
        anomaly_count = len(flags)

        return {
            "campaign_id": str(campaign_id),
            "date": date.isoformat() if isinstance(date, datetime) else str(date),
            "geo": raw_metrics.get("geo"),
            "device_type": raw_metrics.get("device_type"),
            "quality_score": quality_score,
            "grade": grade,
            "ctr_score": round(ctr_score, 2),
            "cvr_score": round(cvr_score, 2),
            "bounce_score": round(bounce_score, 2),
            "dwell_score": round(dwell_score, 2),
            "interaction_score": round(interaction_score, 2),
            "flags": flags,
            "anomaly_count": anomaly_count,
            "metrics": {
                "ctr": round(ctr, 6),
                "cvr": round(cvr, 6),
                "bounce_rate": round(bounce_rate, 6),
                "avg_dwell_sec": round(avg_dwell, 2),
                "interaction_rate": round(interaction_rate, 6),
            },
        }

    async def save_assessment(
        self,
        db: AsyncSession,
        campaign_id: str | uuid.UUID,
        date: datetime,
        raw_metrics: Dict,
    ) -> TrafficQualityScore:
        """Assess traffic and persist the quality score record."""
        result = self.assess_traffic(campaign_id, date, raw_metrics)
        score = TrafficQualityScore(
            campaign_id=campaign_id,
            date=date.replace(hour=0, minute=0, second=0, microsecond=0),
            geo=result.get("geo"),
            device_type=result.get("device_type"),
            quality_score=result["quality_score"],
            grade=result["grade"],
            ctr_score=result["ctr_score"],
            cvr_score=result["cvr_score"],
            bounce_score=result["bounce_score"],
            dwell_score=result["dwell_score"],
            interaction_score=result["interaction_score"],
            flags=result["flags"],
            anomaly_count=result["anomaly_count"],
        )
        db.add(score)
        await db.commit()
        await db.refresh(score)
        return score

    async def detect_anomalies(
        self,
        db: AsyncSession,
        campaign_id: str | uuid.UUID,
        hours: int = 24,
    ) -> List[Dict]:
        """Generate fraud alerts from recent quality scores."""
        since = utc_now() - timedelta(hours=hours)
        result = await db.execute(
            select(TrafficQualityScore)
            .where(TrafficQualityScore.campaign_id == campaign_id)
            .where(TrafficQualityScore.date >= since)
            .order_by(TrafficQualityScore.date.desc())
        )
        scores = result.scalars().all()
        alerts: List[Dict] = []

        for score in scores:
            for flag in score.flags:
                severity = (
                    "critical" if flag in {"bot_suspect", "ctr_anomaly"} else "warning"
                )
                alert = FraudAlert(
                    campaign_id=campaign_id,
                    alert_type=flag,
                    severity=severity,
                    description=(
                        f"检测到流量异常标记: {flag}，"
                        f"质量分 {score.quality_score}，等级 {score.grade}。"
                    ),
                )
                db.add(alert)
                alerts.append(
                    {
                        "id": str(alert.id),
                        "campaign_id": str(campaign_id),
                        "alert_type": flag,
                        "severity": severity,
                        "description": alert.description,
                        "detected_at": alert.detected_at.isoformat(),
                        "status": alert.status,
                    }
                )

        if scores and scores[0].quality_score < 50:
            alert = FraudAlert(
                campaign_id=campaign_id,
                alert_type="overall_fraud_score",
                severity="critical",
                description=f"综合质量分低于50 ({scores[0].quality_score})，判定为作弊流量，建议立即过滤。",
            )
            db.add(alert)
            alerts.append(
                {
                    "id": str(alert.id),
                    "campaign_id": str(campaign_id),
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "description": alert.description,
                    "detected_at": alert.detected_at.isoformat(),
                    "status": alert.status,
                }
            )

        await db.commit()
        return alerts

    async def get_campaign_quality_trend(
        self,
        db: AsyncSession,
        campaign_id: str | uuid.UUID,
        days: int = 7,
    ) -> List[Dict]:
        """Return daily quality scores for the past N days."""
        since = utc_now() - timedelta(days=days)
        result = await db.execute(
            select(TrafficQualityScore)
            .where(TrafficQualityScore.campaign_id == campaign_id)
            .where(TrafficQualityScore.date >= since)
            .order_by(TrafficQualityScore.date.asc())
        )
        return [
            {
                "date": score.date.strftime("%Y-%m-%d"),
                "quality_score": score.quality_score,
                "grade": score.grade,
                "ctr_score": score.ctr_score,
                "cvr_score": score.cvr_score,
                "bounce_score": score.bounce_score,
                "dwell_score": score.dwell_score,
                "interaction_score": score.interaction_score,
                "anomaly_count": score.anomaly_count,
                "flags": score.flags,
            }
            for score in result.scalars().all()
        ]
