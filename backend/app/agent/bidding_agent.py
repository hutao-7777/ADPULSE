"""ReAct bidding agent for campaign optimization."""

import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agent.tools import (
    adjust_bid,
    get_auction_history,
    get_campaign_performance,
    get_creative_performance,
    get_market_benchmark,
)


class BiddingAgent:
    """Rule-based ReAct agent for programmatic bid optimization.

    The agent follows a Think -> Act -> Observe loop. Each step is logged so
    the full reasoning chain can be visualized by the frontend.
    """

    def __init__(
        self,
        campaign_id: str,
        llm_client: Optional[Any] = None,
        strategy: Optional[Dict[str, float]] = None,
    ) -> None:
        self.campaign_id = campaign_id
        self.llm_client = llm_client  # reserved for future LLM integration
        self.strategy = strategy or {
            "target_cpa": 50.0,
            "max_cpm": 20.0,
            "daily_budget": 1000.0,
        }
        self.memory: deque[Dict[str, Any]] = deque(maxlen=20)
        self.current_state = "idle"
        self.last_action: Optional[str] = None

    def _creative_id_for_campaign(self) -> Optional[str]:
        """Placeholder: in a full schema creatives would be linked to campaigns."""
        # Derive a stable fake creative id from campaign id for deterministic demos.
        try:
            uuid.UUID(self.campaign_id)
        except ValueError:
            return None
        # Deterministic UUIDv5-ish derivation using namespace + campaign id
        namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
        derived = uuid.uuid5(namespace, f"creative-for-{self.campaign_id}")
        return str(derived)

    async def think(self) -> Dict[str, Any]:
        """Gather data and produce an analysis of campaign health."""
        self.current_state = "thinking"

        performance = await get_campaign_performance(self.campaign_id)
        auctions = await get_auction_history(self.campaign_id, hours=24)
        benchmark = await get_market_benchmark(
            geo="tier1", ad_format="banner_300x250", category="ecommerce"
        )

        creative_id = self._creative_id_for_campaign()
        creative = await get_creative_performance(creative_id) if creative_id else {}

        # Compute derived auction metrics
        total_auctions = len(auctions)
        wins = [a for a in auctions if a["winning_dsp"]]
        win_rate = len(wins) / total_auctions if total_auctions > 0 else 0.0
        avg_winning_cpm = (
            sum(a["winning_bid_cpm"] for a in wins if a["winning_bid_cpm"]) / len(wins)
            if wins
            else 0.0
        )

        analysis_parts = [
            f"Campaign {self.campaign_id} 过去7天获得 {performance['impressions']} 次展示, "
            f"{performance['clicks']} 次点击, CTR {performance['ctr']:.4f}.",
            f"总花费 ${performance['spend']:.2f}, 收入 ${performance['revenue']:.2f}, "
            f"ROI {performance['roi']:.2f}, 预算消耗率 {performance['spend_ratio']:.1%}.",
            f"近24小时拍卖 {total_auctions} 次, 胜出 {len(wins)} 次, 胜率 {win_rate:.1%}, "
            f"平均获胜CPM ${avg_winning_cpm:.2f}.",
            f"市场基准 CTR {benchmark['avg_ctr']:.4f}, 平均CPM ${benchmark['avg_cpm']:.2f}, "
            f"竞争强度 {benchmark['competition_level']}.",
        ]

        if creative.get("exists"):
            analysis_parts.append(
                f"关联创意 '{creative.get('name')}' AI评分 {creative.get('ai_score')}, "
                f"疲劳度 {creative.get('fatigue_score')}, CTR {creative.get('ctr'):.4f}."
            )
        else:
            analysis_parts.append("未找到关联创意数据。")

        # Add interpretation
        issues = []
        if performance["ctr"] < benchmark["avg_ctr"] * 0.8:
            issues.append("CTR低于市场基准20%以上")
        if win_rate < 0.3:
            issues.append("胜率低于30%")
        if performance["spend_ratio"] > 0.9:
            issues.append("预算消耗超过90%")
        if performance["roi"] > 2.0:
            issues.append("ROI表现优异")
        if creative.get("fatigue_score", 0) > 0.7:
            issues.append("创意疲劳度较高")

        if issues:
            analysis_parts.append("关键发现: " + "; ".join(issues) + "。")
        else:
            analysis_parts.append("当前各项指标处于正常区间，建议保持当前策略。")

        data = {
            "performance": performance,
            "auctions": auctions,
            "benchmark": benchmark,
            "creative": creative,
            "derived": {
                "win_rate": round(win_rate, 4),
                "avg_winning_cpm": round(avg_winning_cpm, 4),
                "auction_count": total_auctions,
            },
        }

        return {"analysis": " ".join(analysis_parts), "data": data}

    async def act(self, analysis: str) -> Dict[str, Any]:
        """Make a bidding decision based on the analysis."""
        self.current_state = "acting"

        # Re-gather data for decision (lightweight, cached by DB + small data)
        performance = await get_campaign_performance(self.campaign_id)
        auctions = await get_auction_history(self.campaign_id, hours=24)
        benchmark = await get_market_benchmark(
            geo="tier1", ad_format="banner_300x250", category="ecommerce"
        )
        creative_id = self._creative_id_for_campaign()
        creative = await get_creative_performance(creative_id) if creative_id else {}

        total_auctions = len(auctions)
        wins = [a for a in auctions if a["winning_dsp"]]
        win_rate = len(wins) / total_auctions if total_auctions > 0 else 0.0
        fatigue = creative.get("fatigue_score", 0.0) or 0.0

        # Decision priority: budget control > creative fatigue > win rate > ROI > CTR
        if performance["spend_ratio"] > 0.9:
            action = "decrease_bid"
            params = {"bid_adjustment_pct": -0.2}
            reasoning = (
                f"预算消耗率已达 {performance['spend_ratio']:.1%}, 需要降低出价控制花费, "
                "避免预算过早耗尽。"
            )
        elif fatigue > 0.7:
            action = "switch_creative"
            params = {}
            reasoning = (
                f"创意疲劳度 {fatigue:.2f} 超过0.7阈值, 建议更换新创意以恢复广告效果。"
            )
        elif win_rate < 0.3:
            action = "increase_bid"
            params = {"bid_adjustment_pct": 0.15}
            reasoning = (
                f"胜率仅 {win_rate:.1%}, 低于健康线30%, 需要提高出价获取更多曝光。"
            )
        elif performance["roi"] > 2.0:
            action = "increase_bid"
            params = {"bid_adjustment_pct": 0.1}
            reasoning = f"ROI {performance['roi']:.2f} 大于2.0, 广告效益良好, 建议适度加大投入。"
        elif performance["ctr"] < benchmark["avg_ctr"] * 0.8 and fatigue < 0.5:
            action = "optimize_creative"
            params = {"bid_adjustment_pct": -0.1}
            reasoning = (
                f"CTR {performance['ctr']:.4f} 低于市场基准 {benchmark['avg_ctr']:.4f} 的80%, "
                "且创意未疲劳, 建议优化创意并小幅降低出价观察效果。"
            )
        else:
            action = "maintain_strategy"
            params = {}
            reasoning = "当前各项指标处于健康区间, 建议保持当前策略继续观察。"

        self.last_action = action
        return {"action": action, "parameters": params, "reasoning": reasoning}

    async def observe(self, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate the outcome of an action and store it in memory."""
        self.current_state = "observing"

        action = action_result.get("action", "unknown")
        params = action_result.get("parameters", {})
        result = action_result.get("result", {})

        expected_ctr_change = result.get("expected_ctr_change_pct", 0.0) / 100.0
        expected_impressions_change = (
            result.get("expected_impressions_change_pct", 0.0) / 100.0
        )

        # Simulate "actual" outcome based on expected with small noise
        import random

        actual_ctr_change = expected_ctr_change * random.uniform(0.8, 1.2)
        actual_impressions_change = expected_impressions_change * random.uniform(
            0.8, 1.2
        )

        expected_vs_actual = {
            "expected_ctr_change_pct": round(expected_ctr_change * 100.0, 2),
            "actual_ctr_change_pct": round(actual_ctr_change * 100.0, 2),
            "expected_impressions_change_pct": round(
                expected_impressions_change * 100.0, 2
            ),
            "actual_impressions_change_pct": round(
                actual_impressions_change * 100.0, 2
            ),
        }

        if action == "switch_creative":
            observation = "建议更换创意, 预期新创意上线后 CTR 可提升 10%-20%。"
            learned = "创意疲劳时更换素材是恢复效果最直接的手段。"
        elif action == "maintain_strategy":
            observation = "保持当前策略, 持续监控核心指标变化。"
            learned = "指标健康时避免频繁调整, 让模型/数据稳定积累。"
        else:
            observation = (
                f"执行 {action} 后, 预估 impressions 变化 "
                f"{expected_vs_actual['expected_impressions_change_pct']}%, "
                f"实际预估反馈 {expected_vs_actual['actual_impressions_change_pct']}%; "
                f"CTR 预估变化 {expected_vs_actual['expected_ctr_change_pct']}%。"
            )
            if actual_impressions_change > 0:
                learned = "出价提升带来了更多曝光机会, 但需关注 ROI 是否同步改善。"
            else:
                learned = "出价下调有助于控制成本, 需观察流量质量是否保持稳定。"

        memory_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "parameters": params,
            "result": result,
            "expected_vs_actual": expected_vs_actual,
            "learned": learned,
        }
        self.memory.append(memory_entry)

        return {
            "observation": observation,
            "expected_vs_actual": expected_vs_actual,
            "learned": learned,
        }

    async def run_loop(self, max_iterations: int = 3) -> List[Dict[str, Any]]:
        """Execute the ReAct loop for up to max_iterations."""
        iterations: List[Dict[str, Any]] = []

        for i in range(max_iterations):
            thought = await self.think()
            action = await self.act(thought["analysis"])

            if action["action"] == "maintain_strategy":
                observation = await self.observe(
                    {
                        "action": action["action"],
                        "parameters": action["parameters"],
                        "result": {},
                    }
                )
                iterations.append(
                    {
                        "iteration": i + 1,
                        "thought": thought,
                        "action": action,
                        "observation": observation,
                    }
                )
                break

            # Simulate tool execution
            if action["action"] in {
                "increase_bid",
                "decrease_bid",
                "optimize_creative",
            }:
                result = await adjust_bid(
                    self.campaign_id,
                    action["parameters"].get("bid_adjustment_pct", 0.0),
                )
            elif action["action"] == "switch_creative":
                result = {"creative_switch_recommended": True, "simulated": True}
            else:
                result = {}

            observation = await self.observe(
                {
                    "action": action["action"],
                    "parameters": action["parameters"],
                    "result": result,
                }
            )

            iterations.append(
                {
                    "iteration": i + 1,
                    "thought": thought,
                    "action": action,
                    "observation": observation,
                }
            )

        self.current_state = "idle"
        return iterations

    def get_memory(self) -> List[Dict[str, Any]]:
        """Return the recent decision memory."""
        return list(self.memory)

    def get_status(self) -> Dict[str, Any]:
        """Return current agent status."""
        return {
            "campaign_id": self.campaign_id,
            "strategy": self.strategy,
            "memory_size": len(self.memory),
            "current_state": self.current_state,
            "last_action": self.last_action,
        }

    def update_strategy(self, strategy: Dict[str, float]) -> None:
        """Update the agent's strategy targets."""
        self.strategy.update(strategy)
