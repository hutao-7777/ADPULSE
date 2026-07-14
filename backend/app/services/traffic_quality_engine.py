"""Traffic quality scoring and fraud detection engine �� SDK platform edition."""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ClickEvent, ConversionEvent, FraudAlert, ImpressionEvent, TrafficQualityScore


class TrafficQualityEngine:
    """Evaluate traffic quality and detect anomalous/fraudulent patterns per ad unit."""

    GRADE_PREMIUM = "premium"
    GRADE_STANDARD = "standard"
    GRADE_LOW = "low"
    GRADE_FRAUD = "fraud"

    def _clamp(self, value: float, low: float = 0.0, high: float = 100.0) -> float:
        return max(low, min(high, value))

    def _score_ctr(self, ctr: float) -> float:
        if 0.01 <= ctr <= 0.05:
            return 100.0
        if ctr < 0.01:
            return self._clamp(ctr / 0.01 * 100.0)
        return self._clamp(100.0 - (ctr - 0.05) / 0.05 * 100.0)

    def _score_cvr(self, cvr: float) -> float:
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

    def _score_interaction(self, rate: float) -> float:
        return self._clamp(rate / 0.30 * 100.0)

    def _map_grade(self, score: float) -> str:
        if score >= 90:
            return self.GRADE_PREMIUM
        if score >= 70:
            return self.GRADE_STANDARD
        if score >= 50:
            return self.GRADE_LOW
        return self.GRADE_FRAUD

    async def assess_from_events(
        self, db: AsyncSession, ad_unit_id: uuid.UUID, since: Optional[datetime] = None
    ) -> Dict:
        """Pull impression/click/conv data from events and compute quality scores."""
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(days=1)

        imp_count = (await db.execute(
            select(func.count(ImpressionEvent.id))
            .where(ImpressionEvent.ad_unit_id == ad_unit_id, ImpressionEvent.created_at >= since)
        )).scalar() or 0

        clk_count = (await db.execute(
            select(func.count(ClickEvent.id))
            .where(ClickEvent.ad_unit_id == ad_unit_id, ClickEvent.created_at >= since)
        )).scalar() or 0

        conv_count = (await db.execute(
            select(func.count(ConversionEvent.id))
            .where(ConversionEvent.ad_unit_id == ad_unit_id, ConversionEvent.created_at >= since)
        )).scalar() or 0

        unique_devices = (await db.execute(
            select(func.count(func.distinct(ImpressionEvent.device_id)))
            .where(ImpressionEvent.ad_unit_id == ad_unit_id, ImpressionEvent.created_at >= since)
        )).scalar() or 1

        ctr = clk_count / imp_count if imp_count > 0 else 0.0
        cvr = conv_count / clk_count if clk_count > 0 else 0.0

        ctr_score = self._score_ctr(ctr)
        cvr_score = self._score_cvr(cvr)
        bounce_score = self._score_bounce(0.5)  # default �� needs real bounce data
        dwell_score = self._score_dwell(20.0)   # default �� needs real dwell data
        interact_score = self._score_interaction(0.15)

        quality = (
            ctr_score * 0.25 + cvr_score * 0.25 +
            bounce_score * 0.2 + dwell_score * 0.15 + interact_score * 0.15
        )
        quality = round(self._clamp(quality), 2)
        grade = self._map_grade(quality)
        flags = self._detect_flags(imp_count, clk_count, conv_count, ctr, cvr)

        result = {
            "ad_unit_id": str(ad_unit_id),
            "date": since.strftime("%Y-%m-%d"),
            "impressions": imp_count,
            "clicks": clk_count,
            "conversions": conv_count,
            "unique_devices": unique_devices,
            "ctr": round(ctr, 6),
            "cvr": round(cvr, 6),
            "quality_score": quality,
            "grade": grade,
            "ctr_score": round(ctr_score, 2),
            "cvr_score": round(cvr_score, 2),
            "bounce_score": round(bounce_score, 2),
            "dwell_score": round(dwell_score, 2),
            "interaction_score": round(interact_score, 2),
            "flags": flags,
        }

        # Persist
        score = TrafficQualityScore(
            ad_unit_id=ad_unit_id,
            date=since,
            quality_score=quality,
            grade=grade,
            ctr=ctr,
            ctr_score=ctr_score,
            cvr_score=cvr_score,
            bounce_score=bounce_score,
            dwell_score=dwell_score,
            interaction_score=interact_score,
            flags=flags,
            anomaly_count=len(flags),
        )
        db.add(score)
        await db.commit()

        return result

    def _detect_flags(
        self, imps: int, clicks: int, convs: int, ctr: float, cvr: float
    ) -> List[str]:
        flags = []
        if imps == 0 or clicks == 0:
            return flags

        if ctr > 0.20 or ctr < 0.0001:
            flags.append("ctr_anomaly")
        if cvr > 0.50:
            flags.append("bot_suspect")
        if imps > 0 and clicks > 0 and ctr > 0.15:
            flags.append("suspect_bot")
        return list(set(flags))

    async def get_trend(
        self, db: AsyncSession, ad_unit_id: uuid.UUID, days: int = 7
    ) -> List[Dict]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(TrafficQualityScore)
            .where(TrafficQualityScore.ad_unit_id == ad_unit_id)
            .where(TrafficQualityScore.date >= since)
            .order_by(TrafficQualityScore.date.asc())
        )
        return [
            {
                "date": s.date.strftime("%Y-%m-%d") if hasattr(s.date, "strftime") else str(s.date),
                "quality_score": s.quality_score,
                "grade": s.grade,
                "ctr_score": s.ctr_score,
                "ctr": s.ctr,
            }
            for s in result.scalars().all()
        ]

    async def get_alerts(
        self, db: AsyncSession, ad_unit_id: uuid.UUID, days: int = 7
    ) -> List[Dict]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(FraudAlert)
            .where(FraudAlert.ad_unit_id == ad_unit_id)
            .where(FraudAlert.detected_at >= since)
            .order_by(FraudAlert.detected_at.desc())
        )
        return [
            {
                "id": str(a.id),
                "alert_type": a.alert_type,
                "severity": a.severity,
                "description": a.description,
                "detected_at": a.detected_at.isoformat(),
                "status": a.status,
            }
            for a in result.scalars().all()
        ]

    async def generate_alerts(
        self, db: AsyncSession, ad_unit_id: uuid.UUID
    ) -> List[FraudAlert]:
        """Assess and generate fraud alerts if quality is low."""
        result = await self.assess_from_events(db, ad_unit_id)
        alerts = []
        if result.get("quality_score", 100) < 60:
            alert = FraudAlert(
                ad_unit_id=ad_unit_id,
                alert_type="low_quality",
                severity="warning",
                description=f"Quality score {result['quality_score']} ({result['grade']}) for ad unit {str(ad_unit_id)[:8]}",
            )
            db.add(alert)
            alerts.append(alert)
        if result.get("quality_score", 100) < 40:
            alert = FraudAlert(
                ad_unit_id=ad_unit_id,
                alert_type="overall_fraud_score",
                severity="critical",
                description=f"Fraud-level quality score: {result['quality_score']}",
            )
            db.add(alert)
            alerts.append(alert)
        for flag in result.get("flags", []):
            if flag in ("ctr_anomaly", "bot_suspect"):
                alert = FraudAlert(
                    ad_unit_id=ad_unit_id,
                    alert_type=flag,
                    severity="critical",
                    description=f"Anomaly detected: {flag}",
                )
                db.add(alert)
                alerts.append(alert)
        if alerts:
            await db.commit()
        return alerts

