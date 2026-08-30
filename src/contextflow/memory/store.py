"""Shared, persistent memory store underlying session/user/agent/
organization memory.

One SQLite table, scoped by (scope, scope_id) — "session"/"abc123",
"user"/"alice", "agent"/"research-bot", "org"/"acme". Each tier's class
in this package (`SessionMemory`, `UserMemory`, ...) is a thin,
type-hinted wrapper over this store scoped to its own `scope` string —
see their docstrings for what's tier-specific vs. shared.

What v1 deliberately does NOT do (see ROADMAP.md "Phase 5 — Memory
system" for the honest list): memory consolidation (merging/summarizing
related facts over time), decay (forgetting stale facts automatically),
importance scoring, or conflict resolution between contradictory facts.
Those need real usage data to design well, not just code — recall
ranks by keyword relevance (BM25) and recency, nothing smarter yet.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MemoryEntry:
    id: str
    scope: str
    scope_id: str
    content: str
    metadata: dict[str, Any]
    created_at: float


class MemoryStore:
    def __init__(self, path: str = ".contextflow/memory.db") -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        # check_same_thread=False + an explicit lock: the MCP server runs
        # tool calls in a worker-thread pool (anyio.to_thread), so a
        # connection created on one thread gets used from another. SQLite
        # connections aren't safe for concurrent use even with that flag,
        # so every access below is serialized through `self._lock`.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_scope ON memory(scope, scope_id)"
            )
            self._conn.commit()

    def remember(
        self, scope: str, scope_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> str:
        entry_id = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                "INSERT INTO memory (id, scope, scope_id, content, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (entry_id, scope, scope_id, content, json.dumps(metadata or {}), time.time()),
            )
            self._conn.commit()
        return entry_id

    def forget(self, entry_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM memory WHERE id = ?", (entry_id,))
            self._conn.commit()
        return cur.rowcount > 0

    def all(self, scope: str, scope_id: str) -> list[MemoryEntry]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, scope, scope_id, content, metadata, created_at FROM memory "
                "WHERE scope = ? AND scope_id = ? ORDER BY created_at DESC",
                (scope, scope_id),
            ).fetchall()
        return [
            MemoryEntry(
                id=r[0], scope=r[1], scope_id=r[2], content=r[3], metadata=json.loads(r[4]),
                created_at=r[5],
            )
            for r in rows
        ]

    def recall(
        self, scope: str, scope_id: str, query: str | None = None, limit: int = 10
    ) -> list[MemoryEntry]:
        """Recall facts for a scope, ranked by keyword relevance (BM25)
        if `query` is given, otherwise most-recent-first."""
        entries = self.all(scope, scope_id)
        if not query or not entries:
            return entries[:limit]

        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            # Fall back to a simple substring filter if rank_bm25 isn't
            # installed for some reason — still functional, just less
            # smart about ranking.
            matches = [e for e in entries if query.lower() in e.content.lower()]
            return matches[:limit] or entries[:limit]

        tokenized = [e.content.lower().split() for e in entries]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(query.lower().split())
        ranked = sorted(zip(entries, scores), key=lambda pair: pair[1], reverse=True)
        return [entry for entry, score in ranked[:limit] if score > 0] or entries[:limit]
