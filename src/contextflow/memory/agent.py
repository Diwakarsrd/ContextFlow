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

    def forget(self, entry_id: str) -> bool:
        return self.store.forget(entry_id)
