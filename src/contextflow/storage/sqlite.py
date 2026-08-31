"""SQLite-backed MetadataStore.

This is the default persistent backend for `contextflow init` / the CLI's
local-first workspace — it's what fixes the "ingest in one process,
search in another finds nothing" bug from v0.1. No external database
required; the whole thing lives in a single `.contextflow/metadata.db`
file.

Swap in PostgreSQL (`contextflow.connectors.postgres`, used as a
MetadataStore backend too — see CONTRIBUTING.md) once you outgrow a
single file.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

from contextflow.core.context import ContextObject
from contextflow.core.metadata import MetadataStore


class SQLiteMetadataStore(MetadataStore):
    def __init__(self, path: str = ".contextflow/metadata.db") -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        # check_same_thread=False + an explicit lock: the MCP server runs
        # tool calls in a worker-thread pool (anyio.to_thread), so a
        # connection created on one thread can get used from another.
        # SQLite connections aren't safe for concurrent use even with
        # that flag, so every access below is serialized through a lock
        # (found via a real MCP tool call raising sqlite3.ProgrammingError
        # before this fix — see tests/test_sqlite_thread_safety.py).
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS objects (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    source TEXT,
                    data TEXT
                )
                """
            )
            self._conn.commit()

    def get(self, id: str) -> ContextObject | None:
        with self._lock:
            row = self._conn.execute("SELECT data FROM objects WHERE id = ?", (id,)).fetchone()
        if row is None:
            return None
        return ContextObject.model_validate_json(row[0])

    def put(self, obj: ContextObject) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO objects (id, type, source, data) VALUES (?, ?, ?, ?)",
                (obj.id, obj.type, obj.source, obj.model_dump_json()),
            )
            self._conn.commit()

    def put_batch(self, objects: list[ContextObject]) -> None:
        """One transaction for the whole batch instead of one commit per
        row — meaningfully faster for bulk ingestion (fsync overhead per
        commit adds up), though the per-row version was never the O(n^2)
        bug that FileVectorStore/FileGraphStore had (a single-row INSERT
        is O(1), not O(n))."""
        with self._lock:
            self._conn.executemany(
                "INSERT OR REPLACE INTO objects (id, type, source, data) VALUES (?, ?, ?, ?)",
                [(obj.id, obj.type, obj.source, obj.model_dump_json()) for obj in objects],
            )
            self._conn.commit()

    def delete(self, id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM objects WHERE id = ?", (id,))
            self._conn.commit()

    def filter(self, **criteria: Any) -> list[ContextObject]:
        objects = self.all()
        for key, value in criteria.items():
            objects = [o for o in objects if getattr(o, key, None) == value]
        return objects

    def all(self) -> list[ContextObject]:
        with self._lock:
            rows = self._conn.execute("SELECT data FROM objects").fetchall()
        return [ContextObject.model_validate_json(row[0]) for row in rows]

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM objects").fetchone()[0]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
