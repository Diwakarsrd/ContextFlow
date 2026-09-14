"""Context tracing: records what happened at each stage of a retrieval
call — how many candidates went in and came out of routing, permission/
tenant filtering, reranking, and (for a full Context Pack) compilation —
plus how long each stage took.

This is the real implementation of the "Context Trace" concept from the
original design doc: a query shouldn't be a black box between "search"
and "here are 5 results." See `engine.py`'s `retrieve_with_trace` /
`context_pack_with_trace` for how this gets built, and
`cli/main.py`'s `trace` command for the human-readable rendering.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class TraceStage:
    name: str
    count_in: int
    count_out: int
    duration_ms: float
    details: dict = field(default_factory=dict)


@dataclass
class ContextTrace:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    stages: list[TraceStage] = field(default_factory=list)
    total_duration_ms: float = 0.0
    final_confidence: float | None = None
    final_tokens: int | None = None
    created_at: float = field(default_factory=time.time)

    def add_stage(
        self, name: str, count_in: int, count_out: int, duration_ms: float, **details
    ) -> None:
        self.stages.append(
            TraceStage(
                name=name,
                count_in=count_in,
                count_out=count_out,
                duration_ms=duration_ms,
                details=details,
            )
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "query": self.query,
            "stages": [
                {
                    "name": s.name,
                    "count_in": s.count_in,
                    "count_out": s.count_out,
                    "duration_ms": round(s.duration_ms, 2),
                    "details": s.details,
                }
                for s in self.stages
            ],
            "total_duration_ms": round(self.total_duration_ms, 2),
            "final_confidence": self.final_confidence,
            "final_tokens": self.final_tokens,
            "created_at": self.created_at,
        }


class _Timer:
    """Tiny context manager so instrumentation reads as
    `with _Timer() as t: ...` then `t.elapsed_ms`."""

    def __enter__(self) -> _Timer:  # noqa: PYI034 - typing.Self needs 3.11+, project supports 3.10
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000


class TraceRecorder:
    """In-memory ring buffer of recent traces, so `contextflow trace` and
    the MCP `trace_query` tool can look one up after the fact. Not
    persisted — restarting the process clears it, which is fine for a
    debugging aid but worth knowing if you expect trace history to
    survive a restart (it doesn't, in v0.1)."""

    def __init__(self, capacity: int = 100) -> None:
        self.capacity = capacity
        self._traces: list[ContextTrace] = []

    def record(self, trace: ContextTrace) -> None:
        self._traces.append(trace)
        if len(self._traces) > self.capacity:
            self._traces.pop(0)

    def recent(self, limit: int = 10) -> list[ContextTrace]:
        return list(reversed(self._traces[-limit:]))

    def get(self, trace_id: str) -> ContextTrace | None:
        for trace in self._traces:
            if trace.id == trace_id:
                return trace
        return None
