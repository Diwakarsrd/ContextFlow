"""Performance/scale benchmarking: measures real ingestion throughput
and retrieval latency at increasing corpus sizes, against both the
in-memory and persistent (SQLite + file-based) local backends.

This is deliberately NOT a claim about production scale. The honest
scope: `InMemoryVectorStore` and `FileVectorStore` (see storage/local.py,
storage/local_persistent.py) do brute-force cosine similarity — O(n) per
query, no index structure. This module measures exactly how that scales
on real hardware up to a few thousand objects, and stops there rather
than extrapolating to "10M+ documents" claims nobody has tested. See
benchmarks/performance/results.md for actual captured numbers and their
important caveats (single machine, single run, no concurrency).
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field

from contextflow.core.context import ContextObject
from contextflow.engine import ContextEngine

_SAMPLE_QUERIES = [
    "payment decisions",
    "refund policy",
    "authentication failure",
    "support response time",
    "data retention",
]


@dataclass
class LatencyStats:
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float


@dataclass
class ScalePoint:
    corpus_size: int
    ingest_throughput_per_sec: float
    retrieval_latency: LatencyStats
    backend: str


@dataclass
class ScaleSweepResult:
    points: list[ScalePoint] = field(default_factory=list)


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, int(len(sorted_values) * pct))
    return sorted_values[idx]


def _measure_retrieval_latency(engine: ContextEngine, num_queries: int = 30) -> LatencyStats:
    durations_ms: list[float] = []
    for i in range(num_queries):
        query = _SAMPLE_QUERIES[i % len(_SAMPLE_QUERIES)]
        start = time.perf_counter()
        engine.retrieve(query, limit=10)
        durations_ms.append((time.perf_counter() - start) * 1000)

    durations_ms.sort()
    return LatencyStats(
        p50_ms=_percentile(durations_ms, 0.50),
        p95_ms=_percentile(durations_ms, 0.95),
        p99_ms=_percentile(durations_ms, 0.99),
        mean_ms=statistics.mean(durations_ms),
    )


def _make_documents(n: int) -> list[ContextObject]:
    # Deliberately varied content (not identical strings) so BM25/hash
    # embedding indexing does real work per document, not a degenerate
    # case that would flatter throughput numbers.
    topics = ["payments", "refunds", "authentication", "support", "billing", "onboarding"]
    return [
        ContextObject(
            content=(
                f"Document {i} discusses {topics[i % len(topics)]} in the context of "
                f"Acme's platform. This is sample content generated for a scale benchmark, "
                f"varying by index {i} to avoid degenerate deduplication."
            ),
            source="benchmark",
        )
        for i in range(n)
    ]


def benchmark_at_size(corpus_size: int, engine_factory) -> ScalePoint:
    """Ingest `corpus_size` documents into a fresh engine (from
    `engine_factory()`) and measure ingestion throughput + retrieval
    latency against the resulting index."""
    engine = engine_factory()
    documents = _make_documents(corpus_size)

    start = time.perf_counter()
    engine.ingest(documents)
    elapsed = time.perf_counter() - start
    throughput = corpus_size / elapsed if elapsed > 0 else float("inf")

    latency = _measure_retrieval_latency(engine)

    backend = type(engine.vector_store).__name__
    return ScalePoint(
        corpus_size=corpus_size,
        ingest_throughput_per_sec=throughput,
        retrieval_latency=latency,
        backend=backend,
    )


def run_scale_sweep(sizes: list[int], engine_factory) -> ScaleSweepResult:
    result = ScaleSweepResult()
    for size in sizes:
        result.points.append(benchmark_at_size(size, engine_factory))
    return result
