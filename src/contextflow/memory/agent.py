"""Agent memory: what a given agent has learned/decided across tasks,
independent of any one user or session. Backed by the shared persistent
MemoryStore — same mechanism as user/session memory, scoped to an
agent_id instead."""

from __future__ import annotations

from typing import Any

from contextflow.memory.store import MemoryEntry, MemoryStore


class AgentMemory:
    def __init__(self, agent_id: str, store: MemoryStore | None = None) -> None:
        self.agent_id = agent_id
        self.store = store or MemoryStore()

    def remember(self, fact: str, metadata: dict[str, Any] | None = None) -> str:
        return self.store.remember("agent", self.agent_id, fact, metadata)

    def recall(self, query: str | None = None, limit: int = 10) -> list[MemoryEntry]:
        return self.store.recall("agent", self.agent_id, query, limit)


    def recall_shared(self, query: str | None = None, limit: int = 10) -> list[MemoryEntry]:
        """Recall globally shared agent context (namespace 'shared')."""
        return self.store.recall("agent", "shared", query, limit)
        
    def handoff_to(self, target_agent_id: str, entry_id: str) -> str:
        """Explicitly push a memory context block to another agent's private namespace."""
        return self.store.share_memory(entry_id, "agent", target_agent_id)
        
    def publish_shared(self, entry_id: str) -> str:
        """Promote a private memory to the global agent shared namespace."""
        return self.store.share_memory(entry_id, "agent", "shared")

    def forget(self, entry_id: str) -> bool:
        return self.store.forget(entry_id)
