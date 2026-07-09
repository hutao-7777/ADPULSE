"""Agent memory store with simple in-memory similarity over JSON embeddings."""

import math
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm_client import LLMClient
from app.models import AgentMemory


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class MemoryStore:
    """Long-term memory for the bidding agent using JSON-stored embeddings."""

    def __init__(self, llm: Optional[LLMClient] = None) -> None:
        self.llm = llm or LLMClient()

    async def add(
        self,
        db: AsyncSession,
        content: str,
        user_id: Optional[uuid.UUID] = None,
        run_id: Optional[uuid.UUID] = None,
        memory_type: str = "observation",
        metadata: Optional[dict] = None,
    ) -> AgentMemory:
        """Embed and store a memory."""
        try:
            embedding = await self.llm.create_embedding(content)
        except Exception:
            embedding = []
        memory = AgentMemory(
            user_id=user_id,
            run_id=run_id,
            content=content,
            embedding=embedding,
            memory_type=memory_type,
            metadata=metadata or {},
        )
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        return memory

    async def search(
        self,
        db: AsyncSession,
        query: str,
        user_id: Optional[uuid.UUID] = None,
        top_k: int = 5,
    ) -> List[AgentMemory]:
        """Return the most similar memories for a query."""
        try:
            query_embedding = await self.llm.create_embedding(query)
        except Exception:
            query_embedding = []

        stmt = select(AgentMemory)
        if user_id:
            stmt = stmt.where(AgentMemory.user_id == user_id)

        result = await db.execute(stmt)
        memories = list(result.scalars().all())

        if not query_embedding:
            return memories[:top_k]

        scored = []
        for memory in memories:
            emb = memory.embedding or []
            score = _cosine_similarity(query_embedding, emb)
            scored.append((score, memory))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:top_k]]
