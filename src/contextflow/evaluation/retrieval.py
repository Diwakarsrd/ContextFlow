"""Retrieval quality metrics: recall, precision, MRR, and NDCG against a
labeled benchmark set. See benchmarks/README.md for the dataset format.
"""

from __future__ import annotations

import math


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    hits = set(retrieved_ids[:k]) & relevant_ids
    return len(hits) / len(relevant_ids)


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = set(top_k) & relevant_ids
    return len(hits) / len(top_k)


def mean_reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def dcg_at_k(retrieved_ids: list[str], relevance: dict[str, float], k: int) -> float:
    """DCG using the exponential-gain formula: sum of (2^rel - 1) /
    log2(rank + 1) over the top k. This is the formula used by sklearn's
    `ndcg_score`, TensorFlow Ranking, and most modern IR benchmarks —
    not the older linear-gain formula (rel_1 + sum(rel_i / log2(i))) from
    Järvelin & Kekäläinen's original paper, which gives different
    numeric values for the same input. Both are standard; this module
    uses exponential gain throughout, so don't compare its NDCG numbers
    directly against a linear-gain implementation elsewhere."""
    dcg = 0.0
    for rank, doc_id in enumerate(retrieved_ids[:k], start=1):
        rel = relevance.get(doc_id, 0.0)
        if rel > 0:
            dcg += (2**rel - 1) / math.log2(rank + 1)
    return dcg


def ndcg_at_k(retrieved_ids: list[str], relevance: dict[str, float], k: int) -> float:
    """Normalized DCG: DCG@k divided by the DCG of the ideal ranking
    (all relevant docs sorted by relevance, best first). 0.0 if nothing
    in `relevance` has a positive grade."""
    dcg = dcg_at_k(retrieved_ids, relevance, k)
    ideal_order = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum((2**rel - 1) / math.log2(rank + 1) for rank, rel in enumerate(ideal_order, start=1) if rel > 0)
    if idcg == 0:
        return 0.0
    return dcg / idcg


def relevance_from_query(query: dict) -> dict[str, float]:
    """Build a {doc_id: relevance_grade} map from a benchmark query
    entry. Supports graded relevance (`relevance: {doc_id: grade}`) or
    falls back to binary relevance from `relevant_ids` (grade 1 each)."""
    if "relevance" in query:
        return {k: float(v) for k, v in query["relevance"].items()}
    return {doc_id: 1.0 for doc_id in query.get("relevant_ids", [])}
