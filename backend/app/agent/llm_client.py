"""LLM client wrapper supporting OpenAI and Anthropic function calling."""

import json
from typing import Any, Dict, List, Optional, cast

from app.core.config import settings


class LLMClient:
    """Unified LLM client for function calling."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL
        self._openai = None
        self._anthropic = None

    def _get_openai(self):
        if self._openai is None:
            from openai import AsyncOpenAI

            self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai

    def _get_anthropic(self):
        if self._anthropic is None:
            from anthropic import AsyncAnthropic

            self._anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._anthropic

    def _fallback_tool_response(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Return a deterministic tool-call response when no API key is configured."""
        if not tools:
            return {
                "role": "assistant",
                "content": "No API key configured; returning default analysis.",
                "tool_calls": [],
            }
        target = tools[0]["function"]["name"]
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "fallback-call",
                    "type": "function",
                    "function": {
                        "name": target,
                        "arguments": json.dumps({"campaign_id": "fallback"}),
                    },
                }
            ],
        }

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Call the LLM with tools and return the assistant message."""
        if self.provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                return self._fallback_tool_response(tools)
            return await self._anthropic_chat(messages, tools, temperature)
        if not settings.OPENAI_API_KEY:
            return self._fallback_tool_response(tools)
        return await self._openai_chat(messages, tools, temperature)

    async def _openai_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        temperature: float,
    ) -> Dict[str, Any]:
        client = self._get_openai()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
        )
        return cast(dict[str, Any], response.choices[0].message.model_dump())

    async def _anthropic_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        temperature: float,
    ) -> Dict[str, Any]:
        client = self._get_anthropic()
        # Convert OpenAI-style messages to Anthropic format.
        system = "You are an expert programmatic advertising bidding agent."
        user_messages = []
        for m in messages:
            if m.get("role") == "system":
                system = m.get("content", system)
            else:
                user_messages.append(m)

        response = await client.messages.create(
            model=self.model,
            system=system,
            messages=user_messages,
            tools=[{"name": t["function"]["name"], **t["function"]} for t in tools],
            tool_choice={"type": "auto"},
            temperature=temperature,
            max_tokens=1024,
        )
        content = response.content[0]
        if content.type == "tool_use":
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": content.id,
                        "type": "function",
                        "function": {
                            "name": content.name,
                            "arguments": json.dumps(content.input),
                        },
                    }
                ],
            }
        return {"role": "assistant", "content": content.text}

    async def create_embedding(self, text: str) -> List[float]:
        """Create an embedding vector for the given text."""
        if not settings.OPENAI_API_KEY:
            # Deterministic zero vector for local dev/tests without an API key.
            return [0.0] * 1536
        if self.provider == "anthropic":
            # Anthropic does not expose embeddings; fall back to OpenAI.
            client = self._get_openai()
        else:
            client = self._get_openai()
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return cast(list[float], response.data[0].embedding)
