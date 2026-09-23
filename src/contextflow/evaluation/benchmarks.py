"""Runs a benchmark suite (see benchmarks/) end-to-end against a fresh
ContextEngine and reports aggregate retrieval metrics.

Benchmark file format (YAML) — see benchmarks/README.md for the full
ContextBench methodology:

    version: 1
    name: acme_support_v1
    corpus:
      - id: doc1
        content: "..."
    queries:
      - query: "..."
        relevant_ids: [doc1]          # binary relevance, OR:
        relevance: {doc1: 3, doc2: 1}  # graded relevance (0-3 typical)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from contextflow.core.context import ContextObject
from contextflow.engine import ContextEngine, _provider_from_env
from contextflow.evaluation.retrieval import (
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    relevance_from_query,
)


@dataclass
class BenchmarkResult:
    name: str
    recall: float
    precision: float
    mrr: float
    ndcg: float
    avg_tokens: float
    num_queries: int


def run_benchmark(benchmark_path: str, k: int = 5) -> BenchmarkResult:
    with open(benchmark_path) as f:
        data = yaml.safe_load(f)

    corpus = data.get("corpus", [])
    queries = data.get("queries", [])
    name = data.get("name", Path(benchmark_path).stem)
    if not corpus or not queries:
        raise ValueError(f"{benchmark_path} must define both `corpus` and `queries`")

    # Use explicit corpus IDs as ContextObject IDs so relevance judgments
    # (which reference those IDs) line up with retrieval results.
    # Honor CONTEXTOS_EMBEDDING_PROVIDER like the rest of the CLI, so the
    # benchmark measures the provider users actually configured.
    engine = ContextEngine(embedding_provider=_provider_from_env())
    for entry in corpus:
        obj = ContextObject(id=entry["id"], content=entry["content"], source="benchmark")
        engine._semantic.index(obj)
        engine._keyword.index(obj)

    recalls, precisions, mrrs, ndcgs, token_counts = [], [], [], [], []
    for q in queries:
        relevant = set(q.get("relevant_ids", q.get("relevance", {}).keys()))
        relevance_map = relevance_from_query(q)
        results = engine.retrieve(q["query"], limit=max(k, 10))
        retrieved_ids = [obj.id for obj in results]

        recalls.append(recall_at_k(retrieved_ids, relevant, k))
        precisions.append(precision_at_k(retrieved_ids, relevant, k))
        mrrs.append(mean_reciprocal_rank(retrieved_ids, relevant))
        ndcgs.append(ndcg_at_k(retrieved_ids, relevance_map, k))
        pack = engine.context_pack(task=q["query"], max_tokens=1000)
        token_counts.append(pack.tokens_used or 0)

    n = len(queries)
    return BenchmarkResult(
        name=name,
        recall=sum(recalls) / n,
        precision=sum(precisions) / n,
        mrr=sum(mrrs) / n,
        ndcg=sum(ndcgs) / n,
        avg_tokens=sum(token_counts) / n,
        num_queries=n,
    )


def save_result(result: BenchmarkResult, path: str) -> None:
    Path(path).write_text(json.dumps(asdict(result), indent=2))


def load_result(path: str) -> BenchmarkResult:
    return BenchmarkResult(**json.loads(Path(path).read_text()))


def compare_results(baseline: BenchmarkResult, candidate: BenchmarkResult) -> dict[str, float]:
    """Returns {metric: delta} for each numeric metric, candidate minus
    baseline — positive means the candidate improved that metric."""
    deltas = {}
    for metric in ("recall", "precision", "mrr", "ndcg"):
        deltas[metric] = getattr(candidate, metric) - getattr(baseline, metric)
    deltas["avg_tokens"] = candidate.avg_tokens - baseline.avg_tokens
    return deltas
