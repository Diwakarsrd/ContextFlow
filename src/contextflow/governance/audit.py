"""Audit logging: records who retrieved what, when, and why, and
supports querying it back.

Append-only JSONL file — no external dependency, easy to ship to a real
log pipeline (just tail/ingest the file). Structured filtering here
covers the common cases (by principal, action, or time range); anything
fancier (full-text search over audit entries, retention policies) is a
v0.2+ target — see ROADMAP.md.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, path: str = ".contextflow/audit.log") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, principal: str, action: str, details: dict[str, Any]) -> None:
        entry = {"ts": time.time(), "principal": principal, "action": action, **details}
        with self.path.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def query(
        self,
        principal: str | None = None,
        action: str | None = None,
        since: float | None = None,
    ) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        entries = []
        with self.path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entries.append(json.loads(line))

        if principal is not None:
            entries = [e for e in entries if e.get("principal") == principal]
        if action is not None:
            entries = [e for e in entries if e.get("action") == action]
        if since is not None:
            entries = [e for e in entries if e.get("ts", 0) >= since]
        return entries
