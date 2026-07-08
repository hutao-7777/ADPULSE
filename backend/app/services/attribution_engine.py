"""Multi-touch attribution engine.

Supports first/last/linear/time-decay/U-shaped/Shapley models.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AttributionResult, Touchpoint


class AttributionEngine:
    """Rule-based and data-driven multi-touch attribution calculator."""

    MODEL_TYPES = [
        "first_touch",
        "last_touch",
        "linear",
        "time_decay",
        "position_based",
        "shapley",
    ]

    async def build_user_journey(
        self,
        db: AsyncSession,
        user_id: str,
        campaign_id: str | uuid.UUID,
        days: int = 30,
    ) -> List[Dict]:
        """Return the chronological touchpoint journey for a user in a campaign."""
        since = datetime.utcnow() - timedelta(days=days)
        result = await db.execute(
            select(Touchpoint)
            .where(Touchpoint.user_id == user_id)
            .where(Touchpoint.campaign_id == campaign_id)
            .where(Touchpoint.event_time >= since)
            .order_by(Touchpoint.touchpoint_seq.asc(), Touchpoint.event_time.asc())
        )
        return [self._touchpoint_to_dict(tp) for tp in result.scalars().all()]

    def _touchpoint_to_dict(self, tp: Touchpoint) -> Dict:
        return {
            "id": str(tp.id),
            "seq": tp.touchpoint_seq,
            "channel": tp.channel,
            "event_type": tp.event_type,
            "event_time": tp.event_time.isoformat() if tp.event_time else None,
            "conversion_event_id": (
                str(tp.conversion_event_id) if tp.conversion_event_id else None
            ),
        }

    def _channels(self, journey: List[Dict]) -> List[str]:
        return list({tp["channel"] for tp in journey})

    def calculate_first_touch(self, journey: List[Dict]) -> Dict[str, float]:
        """First touch receives 100% credit."""
        if not journey:
            return {}
        channels = self._channels(journey)
        first_channel = journey[0]["channel"]
        return {ch: 1.0 if ch == first_channel else 0.0 for ch in channels}

    def calculate_last_touch(self, journey: List[Dict]) -> Dict[str, float]:
        """Last touch receives 100% credit."""
        if not journey:
            return {}
        channels = self._channels(journey)
        last_channel = journey[-1]["channel"]
        return {ch: 1.0 if ch == last_channel else 0.0 for ch in channels}

    def calculate_linear(self, journey: List[Dict]) -> Dict[str, float]:
        """Equal credit across all touchpoints."""
        if not journey:
            return {}
        channels = self._channels(journey)
        n = len(journey)
        credit = {ch: 0.0 for ch in channels}
        for tp in journey:
            credit[tp["channel"]] += 1.0 / n
        return credit

    def calculate_time_decay(
        self,
        journey: List[Dict],
        conversion_time: Optional[datetime] = None,
        half_life_days: float = 7.0,
    ) -> Dict[str, float]:
        """Weight decays by half every half_life_days before conversion."""
        if not journey:
            return {}
        channels = self._channels(journey)
        conv_time = conversion_time or self._parse_time(journey[-1]["event_time"])
        if conv_time is None:
            return self.calculate_linear(journey)

        weights: Dict[str, float] = {ch: 0.0 for ch in channels}
        for tp in journey:
            tp_time = self._parse_time(tp["event_time"])
            if tp_time is None:
                continue
            delta_days = max(0.0, (conv_time - tp_time).total_seconds() / 86400.0)
            weight = 0.5 ** (delta_days / half_life_days)
            weights[tp["channel"]] += weight

        total = sum(weights.values()) or 1.0
        return {ch: round(v / total, 6) for ch, v in weights.items()}

    def calculate_position_based(
        self,
        journey: List[Dict],
        first_pct: float = 0.4,
        last_pct: float = 0.4,
    ) -> Dict[str, float]:
        """U-shaped: first and last share 40% each, middle touches split the rest."""
        if not journey:
            return {}
        channels = self._channels(journey)
        n = len(journey)
        credit: Dict[str, float] = {ch: 0.0 for ch in channels}

        if n == 1:
            credit[journey[0]["channel"]] = 1.0
        elif n == 2:
            credit[journey[0]["channel"]] = 0.5
            credit[journey[-1]["channel"]] = 0.5
        else:
            middle_pct = 1.0 - first_pct - last_pct
            middle_share = middle_pct / (n - 2)
            credit[journey[0]["channel"]] += first_pct
            credit[journey[-1]["channel"]] += last_pct
            for tp in journey[1:-1]:
                credit[tp["channel"]] += middle_share

        return credit

    def calculate_shapley_approx(self, journey: List[Dict]) -> Dict[str, float]:
        """Simplified Shapley-style approximation using weighted positional
        frequency.
        """
        if not journey:
            return {}
        channels = self._channels(journey)
        weights: Dict[str, float] = {ch: 0.0 for ch in channels}
        for tp in journey:
            seq = max(1, tp.get("seq", 1))
            weights[tp["channel"]] += 1.0 / seq
        total = sum(weights.values()) or 1.0
        return {ch: round(v / total, 6) for ch, v in weights.items()}

    def compare_models(
        self,
        journey: List[Dict],
        conversion_value: float,
        conversion_time: Optional[datetime] = None,
        models: Optional[List[str]] = None,
    ) -> Dict:
        """Run selected attribution models and return value-weighted comparison."""
        selected = models or self.MODEL_TYPES
        credits: Dict[str, Dict[str, float]] = {}

        if "first_touch" in selected:
            credits["first_touch"] = self.calculate_first_touch(journey)
        if "last_touch" in selected:
            credits["last_touch"] = self.calculate_last_touch(journey)
        if "linear" in selected:
            credits["linear"] = self.calculate_linear(journey)
        if "time_decay" in selected:
            credits["time_decay"] = self.calculate_time_decay(journey, conversion_time)
        if "position_based" in selected:
            credits["position_based"] = self.calculate_position_based(journey)
        if "shapley" in selected:
            credits["shapley"] = self.calculate_shapley_approx(journey)

        model_values: Dict[str, Dict[str, float]] = {}
        for model, credit in credits.items():
            model_values[model] = {
                ch: round(c * conversion_value, 4) for ch, c in credit.items()
            }

        summary = self._build_summary(journey, model_values)

        return {
            "journey": journey,
            "conversion_value": conversion_value,
            "models": model_values,
            "model_credits": credits,
            "summary": summary,
        }

    def _build_summary(
        self, journey: List[Dict], model_values: Dict[str, Dict[str, float]]
    ) -> str:
        if not journey:
            return "无可用触点路径。"
        first = journey[0]["channel"]
        last = journey[-1]["channel"]
        channels = self._channels(journey)

        lines = [
            f"用户旅程包含 {len(journey)} 个触点，涉及渠道: {', '.join(channels)}。",
            f"首次触点: {first}，末次触点: {last}。",
        ]

        for model, values in model_values.items():
            top_channel = max(values, key=lambda k: values[k]) if values else "无"
            top_value = values.get(top_channel, 0.0)
            lines.append(
                f"{self._model_label(model)} 下，{top_channel} 贡献最高 (¥{top_value:.2f})。"
            )

        return " ".join(lines)

    def _model_label(self, model: str) -> str:
        labels = {
            "first_touch": "首次触点模型",
            "last_touch": "末次触点模型",
            "linear": "线性归因模型",
            "time_decay": "时间衰减模型",
            "position_based": "U型位置模型",
            "shapley": "Shapley近似模型",
        }
        return labels.get(model, model)

    def _parse_time(self, value) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return None

    async def persist_results(
        self,
        db: AsyncSession,
        conversion_event_id: uuid.UUID,
        model_values: Dict[str, Dict[str, float]],
    ) -> None:
        """Persist attribution credits for each model to the database."""
        for model_type, credits in model_values.items():
            result = AttributionResult(
                conversion_event_id=conversion_event_id,
                model_type=model_type,
                channel_credits=credits,
            )
            db.add(result)
        await db.commit()
