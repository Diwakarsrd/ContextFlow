"""Regression test for a real bug: the `mcp` package runs tool calls in
a worker-thread pool (anyio.to_thread.run_sync), so a SQLite connection
created on the main thread gets used from a different thread on the
first tool call. Both SQLite-backed stores create their connection with
check_same_thread=False and serialize access with a lock — this test
reproduces the original failure mode directly (create on one thread,
use from another) rather than only through the MCP layer.
"""

from __future__ import annotations

import threading

from contextflow.core.context import ContextObject
from contextflow.memory.store import MemoryStore
from contextflow.storage.sqlite import SQLiteMetadataStore


def test_sqlite_metadata_store_usable_from_another_thread(tmp_path):
    store = SQLiteMetadataStore(str(tmp_path / "metadata.db"))
    errors: list[Exception] = []

    def worker() -> None:
        try:
            store.put(ContextObject(content="from another thread", source="test"))
        except Exception as e:  # noqa: BLE001 - want to see any exception, not just sqlite3's
            errors.append(e)

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    assert not errors, f"cross-thread access failed: {errors}"
    assert store.count() == 1


def test_memory_store_usable_from_another_thread(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.db"))
    errors: list[Exception] = []

    def worker() -> None:
        try:
            store.remember("user", "alice", "from another thread")
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    assert not errors, f"cross-thread access failed: {errors}"
    assert len(store.all("user", "alice")) == 1


def test_memory_store_concurrent_writes_from_many_threads(tmp_path):
    """Not just usable from another thread, but safe under concurrent
    access from several — the scenario an MCP server under real load
    would hit."""
    store = MemoryStore(str(tmp_path / "memory.db"))
    errors: list[Exception] = []

    def worker(i: int) -> None:
        try:
            store.remember("user", "alice", f"fact {i}")
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent access failed: {errors}"
    assert len(store.all("user", "alice")) == 20
