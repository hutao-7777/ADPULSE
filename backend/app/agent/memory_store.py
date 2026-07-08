"""Vector memory store backed by PostgreSQL pgvector."""

import uuid
from typing import List, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm_client import LLMClient
from app.models.models import AgentMemory


class MemoryStore:
    """Long-term memory for the bidding agent using pgvector similarity search."""

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
        embedding = await self.llm.create_embedding(content)
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
        embedding = await self.llm.create_embedding(query)
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        stmt = select(AgentMemory).order_by(
            AgentMemory.embedding.cosine_distance(embedding_str)
        )
        if user_id:
            stmt = stmt.where(AgentMemory.user_id == user_id)

        result = await db.execute(stmt.limit(top_k))
        return list(result.scalars().all())

    async def ensure_extension(self, db: AsyncSession) -> None:
        """Ensure the pgvector extension exists (PostgreSQL only)."""
        await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await db.commit()
