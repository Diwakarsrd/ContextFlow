"""Organization memory: durable, org-wide facts (decisions, policies)
that outlive any single user, agent, or session. Backed by the shared
persistent MemoryStore, scoped to an org_id."""

from __future__ import annotations

from typing import Any

from contextflow.memory.store import MemoryEntry, MemoryStore


class OrganizationMemory:
    def __init__(self, org_id: str, store: MemoryStore | None = None) -> None:
        self.org_id = org_id
        self.store = store or MemoryStore()

    def remember(self, fact: str, metadata: dict[str, Any] | None = None) -> str:
        return self.store.remember("org", self.org_id, fact, metadata)

    def recall(self, query: str | None = None, limit: int = 10) -> list[MemoryEntry]:
        return self.store.recall("org", self.org_id, query, limit)

    def forget(self, entry_id: str) -> bool:
        return self.store.forget(entry_id)
