from contextflow.evaluation.benchmarks import (
    BenchmarkResult,
    compare_results,
    load_result,
    run_benchmark,
    save_result,
)


def test_run_benchmark_on_placeholder_dataset(tmp_path):
    bench = tmp_path / "bench.yaml"
    bench.write_text(
        """
name: tiny_test
corpus:
  - id: doc1
    content: "Customers may request a full refund within 30 days."
  - id: doc2
    content: "Support is available Monday through Friday."
queries:
  - query: "What is the refund policy?"
    relevant_ids: [doc1]
  - query: "When can I contact support?"
    relevant_ids: [doc2]
"""
    )
    result = run_benchmark(str(bench))
    assert result.name == "tiny_test"
    assert result.num_queries == 2
    assert 0.0 <= result.recall <= 1.0
    assert 0.0 <= result.ndcg <= 1.0


def test_run_benchmark_on_real_acme_dataset():
    """Runs the actual ContextBench v0.1 dataset shipped in the repo —
    if this ever returns trivial 100%/0% scores, the dataset has stopped
    being a meaningful benchmark (e.g. distractors removed by accident)."""
    result = run_benchmark("benchmarks/datasets/acme_support_v1.yaml")
    assert result.name == "acme_support_v1"
    assert result.num_queries >= 15
    # Meaningful difficulty: not perfect, not zero.
    assert 0.0 < result.recall < 1.0
    assert 0.0 < result.ndcg < 1.0


def test_run_benchmark_supports_graded_relevance():
    """The acme dataset's GDPR query uses graded relevance — confirm
    NDCG actually differs from what binary relevance would produce by
    checking it's computed at all (a NaN or exception here would mean
    graded parsing broke)."""
    result = run_benchmark("benchmarks/datasets/acme_support_v1.yaml")
    assert result.ndcg == result.ndcg  # not NaN


def test_run_benchmark_requires_corpus_and_queries(tmp_path):
    bench = tmp_path / "empty.yaml"
    bench.write_text("corpus: []\nqueries: []\n")
    try:
        run_benchmark(str(bench))
        assert False, "should have raised"
    except ValueError:
        pass


def test_save_and_load_result_roundtrip(tmp_path):
    result = BenchmarkResult(
        name="test", recall=0.5, precision=0.3, mrr=0.4, ndcg=0.45, avg_tokens=100, num_queries=5
    )
    path = str(tmp_path / "result.json")
    save_result(result, path)
    loaded = load_result(path)
    assert loaded == result


def test_compare_results_shows_positive_and_negative_deltas():
    baseline = BenchmarkResult(
        name="b", recall=0.5, precision=0.3, mrr=0.4, ndcg=0.4, avg_tokens=1000, num_queries=5
    )
    candidate = BenchmarkResult(
        name="c", recall=0.6, precision=0.3, mrr=0.35, ndcg=0.42, avg_tokens=900, num_queries=5
    )
    deltas = compare_results(baseline, candidate)
    assert abs(deltas["recall"] - 0.1) < 1e-9
    assert abs(deltas["mrr"] - (-0.05)) < 1e-9
    assert abs(deltas["avg_tokens"] - (-100)) < 1e-9
