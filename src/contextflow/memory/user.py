"""User memory: durable facts/preferences about a specific user, carried
across sessions. Backed by the shared persistent MemoryStore."""

from __future__ import annotations

from typing import Any

from contextflow.memory.store import MemoryEntry, MemoryStore


class UserMemory:
    def __init__(self, user_id: str, store: MemoryStore | None = None) -> None:
        self.user_id = user_id
        self.store = store or MemoryStore()

    def remember(self, fact: str, metadata: dict[str, Any] | None = None) -> str:
        return self.store.remember("user", self.user_id, fact, metadata)

    def recall(self, query: str | None = None, limit: int = 10) -> list[MemoryEntry]:
        return self.store.recall("user", self.user_id, query, limit)

    def forget(self, entry_id: str) -> bool:
        return self.store.forget(entry_id)
