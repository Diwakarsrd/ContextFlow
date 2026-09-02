"""Smoke tests for the performance harness itself — these check the
harness runs and returns sane structure at small N. They deliberately
do NOT assert on specific latency/throughput numbers: performance
varies by machine, load, and Python version, so a hard threshold here
would be flaky by design. For actual captured numbers and their
methodology, see benchmarks/performance/results.md.
"""

from contextflow.engine import ContextEngine
from contextflow.evaluation.performance import benchmark_at_size, run_scale_sweep


def test_benchmark_at_size_returns_sane_structure():
    point = benchmark_at_size(20, lambda: ContextEngine())
    assert point.corpus_size == 20
    assert point.ingest_throughput_per_sec > 0
    assert point.retrieval_latency.p50_ms >= 0
    assert point.retrieval_latency.p95_ms >= point.retrieval_latency.p50_ms
    assert point.backend == "InMemoryVectorStore"


def test_run_scale_sweep_produces_one_point_per_size():
    result = run_scale_sweep([10, 20], lambda: ContextEngine())
    assert len(result.points) == 2
    assert [p.corpus_size for p in result.points] == [10, 20]


def test_batched_ingestion_does_not_change_correctness_at_small_scale():
    """The batch-write refactor changed *how* ingestion writes data, not
    what ends up stored — this checks retrieval still finds what was
    ingested at a size small enough to run in every CI invocation."""
    engine = ContextEngine()
    point = benchmark_at_size(15, lambda: engine)
    assert point.corpus_size == 15
    results = engine.retrieve("payments", limit=5)
    assert len(results) > 0
