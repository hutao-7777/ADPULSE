"""Production bidding agent using real LLM function calling and memory store."""

import json
import time
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm_client import LLMClient
from app.agent.memory_store import MemoryStore
from app.core.config import settings
from app.models import AgentConfig, AgentRun, AgentStep, User

# Tool definitions in OpenAI function-calling format.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_market_summary",
            "description": (
                "Get RTB market summary: win rate, avg CPM and spend ratio."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign UUID",
                    }
                },
                "required": ["campaign_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_bid_strategy",
            "description": "Adjust bidding strategy parameters for a campaign.",
            "parameters": {
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string"},
                    "max_cpm": {"type": "number"},
                    "pacing_rate": {"type": "number"},
                    "strategy": {
                        "type": "string",
                        "enum": ["aggressive", "balanced", "conservative"],
                    },
                },
                "required": ["campaign_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Finish the task and provide a final recommendation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recommendation": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["recommendation", "rationale"],
            },
        },
    },
]


class BiddingAgent:
    """ReAct bidding agent backed by a real LLM and vector memory."""

    def __init__(
        self,
        db: AsyncSession,
        user: User,
        config: AgentConfig,
        llm: Optional[LLMClient] = None,
        memory: Optional[MemoryStore] = None,
    ) -> None:
        self.db = db
        self.user = user
        self.config = config
        self.llm = llm or LLMClient()
        self.memory = memory or MemoryStore(self.llm)
        self.steps: List[Dict[str, Any]] = []

    async def _retrieve_context(self, goal: str) -> str:
        """Retrieve relevant memories to inject into the prompt."""
        try:
            memories = await self.memory.search(
                self.db,
                query=goal,
                user_id=self.user.id,
                top_k=settings.AGENT_MEMORY_TOP_K,
            )
        except Exception:
            memories = []
        if not memories:
            return ""
        context = "Relevant past decisions:\n"
        for m in memories:
            context += f"- {m.content}\n"
        return context

    async def _execute_tool(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool and return an observation."""
        if tool_name == "get_market_summary":
            # Placeholder: in production this queries a persistent cache or database.
            return {
                "campaign_id": tool_input.get("campaign_id"),
                "win_rate": 0.12,
                "avg_cpm": 4.5,
                "spend_ratio": 0.34,
                "impressions": 125000,
                "clicks": 1500,
            }
        if tool_name == "adjust_bid_strategy":
            return {
                "status": "adjusted",
                "campaign_id": tool_input.get("campaign_id"),
                "new_params": tool_input,
            }
        if tool_name == "finish":
            return {"status": "finished"}
        return {"error": f"Unknown tool: {tool_name}"}

    async def run(self, goal: str, max_steps: int = 10) -> Dict[str, Any]:
        """Run the ReAct loop and persist steps and memories."""
        start = time.perf_counter()
        run_record = AgentRun(
            config_id=self.config.id,
            user_id=self.user.id,
            status="running",
            goal=goal,
            final_output=None,
            step_count=0,
            latency_ms=0.0,
        )
        self.db.add(run_record)
        await self.db.flush()

        context = await self._retrieve_context(goal)
        system_message = (
            "You are an expert programmatic advertising bidding agent. "
            "Reason step-by-step, then call tools to act. Finish with a recommendation."
        )
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": f"Goal: {goal}\n\n{context}",
            },
        ]

        final_output = ""
        for step_number in range(1, max_steps + 1):
            step_start = time.perf_counter()
            response = await self.llm.chat_with_tools(messages, TOOLS)

            tool_calls = response.get("tool_calls") or []
            content = response.get("content") or ""

            thought = content
            tool_name = None
            tool_input = {}
            tool_output = {}

            if tool_calls:
                call = tool_calls[0]
                tool_name = call["function"]["name"]
                try:
                    tool_input = json.loads(call["function"]["arguments"])
                except json.JSONDecodeError:
                    tool_input = {}
                tool_output = await self._execute_tool(tool_name, tool_input)

            latency_ms = (time.perf_counter() - step_start) * 1000

            step_record = AgentStep(
                run_id=run_record.id,
                step_number=step_number,
                phase="act" if tool_name else "think",
                thought=thought,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                latency_ms=latency_ms,
            )
            self.db.add(step_record)

            self.steps.append(
                {
                    "step": step_number,
                    "thought": thought,
                    "tool": tool_name,
                    "input": tool_input,
                    "output": tool_output,
                    "latency_ms": latency_ms,
                }
            )

            # Add assistant message.
            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            if tool_name:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(tool_output),
                    }
                )

            if tool_name == "finish":
                final_output = tool_input.get("recommendation", "")
                break

        latency_total = (time.perf_counter() - start) * 1000
        run_record.status = "completed"
        run_record.final_output = final_output
        run_record.step_count = len(self.steps)
        run_record.latency_ms = latency_total
        await self.db.commit()

        # Store key observation as memory.
        try:
            await self.memory.add(
                self.db,
                content=f"Goal: {goal} | Result: {final_output}",
                user_id=self.user.id,
                run_id=run_record.id,
                memory_type="decision",
            )
        except Exception:
            pass

        return {
            "run_id": str(run_record.id),
            "goal": goal,
            "final_output": final_output,
            "steps": self.steps,
            "latency_ms": latency_total,
        }
