"""Session memory: persists for the duration of a conversation/session,
scoped by session_id. Backed by the shared persistent MemoryStore, so it
survives across separate process invocations, unlike WorkingMemory."""

from __future__ import annotations

from typing import Any

from contextflow.memory.store import MemoryEntry, MemoryStore


class SessionMemory:
    def __init__(self, session_id: str, store: MemoryStore | None = None) -> None:
        self.session_id = session_id
        self.store = store or MemoryStore()

    def remember(self, fact: str, metadata: dict[str, Any] | None = None) -> str:
        return self.store.remember("session", self.session_id, fact, metadata)

    def recall(self, query: str | None = None, limit: int = 10) -> list[MemoryEntry]:
        return self.store.recall("session", self.session_id, query, limit)

    def forget(self, entry_id: str) -> bool:
        return self.store.forget(entry_id)
