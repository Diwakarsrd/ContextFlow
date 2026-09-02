import math

from contextflow.evaluation.retrieval import (
    dcg_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    relevance_from_query,
)


def test_recall_at_k_basic():
    assert recall_at_k(["a", "b", "c"], {"a", "z"}, k=3) == 0.5
    assert recall_at_k(["a"], set(), k=3) == 0.0


def test_precision_at_k_basic():
    assert precision_at_k(["a", "b", "c"], {"a"}, k=3) == 1 / 3
    assert precision_at_k([], {"a"}, k=3) == 0.0


def test_mrr_basic():
    assert mean_reciprocal_rank(["x", "a", "b"], {"a"}) == 0.5
    assert mean_reciprocal_rank(["a"], {"a"}) == 1.0
    assert mean_reciprocal_rank(["x", "y"], {"a"}) == 0.0


def test_ndcg_perfect_ranking_is_one():
    # If the retrieved order exactly matches the ideal order, NDCG = 1.0.
    relevance = {"a": 3.0, "b": 2.0, "c": 1.0}
    assert ndcg_at_k(["a", "b", "c"], relevance, k=3) == 1.0


def test_ndcg_worse_ranking_scores_lower_than_perfect():
    relevance = {"a": 3.0, "b": 2.0, "c": 1.0}
    perfect = ndcg_at_k(["a", "b", "c"], relevance, k=3)
    worse = ndcg_at_k(["c", "b", "a"], relevance, k=3)
    assert worse < perfect
    assert 0.0 < worse < 1.0


def test_ndcg_against_independently_verified_value():
    # relevances [3, 2, 3, 0, 1, 2] in retrieved order, with the
    # exponential-gain DCG formula this module uses: (2^rel - 1) / log2(rank + 1).
    # Expected value hand-derived independently (see the PR/commit adding
    # this test for the worked arithmetic) — NOT the ~0.9608 figure
    # commonly cited for this input, which is for the *linear*-gain DCG
    # variant (Järvelin & Kekäläinen's original formula), a different
    # (also standard) formula this module does not use.
    relevance = {"d1": 3, "d2": 2, "d3": 3, "d4": 0, "d5": 1, "d6": 2}
    retrieved = ["d1", "d2", "d3", "d4", "d5", "d6"]
    result = ndcg_at_k(retrieved, relevance, k=6)
    assert abs(result - 0.94881) < 0.0001


def test_ndcg_with_no_relevant_docs_in_relevance_map_is_zero():
    assert ndcg_at_k(["a", "b"], {}, k=2) == 0.0


def test_dcg_ignores_docs_not_in_relevance_map():
    # An "unknown" doc (not in the relevance map) contributes zero gain
    # but still occupies a rank position, shifting the discount applied
    # to whatever comes after it — this checks that shift is correct,
    # not that the unknown doc is invisible to ranking.
    with_unknown_first = dcg_at_k(["unknown", "a"], {"a": 1.0}, k=2)
    expected = (2**1 - 1) / math.log2(3)  # "a" at rank 2
    assert abs(with_unknown_first - expected) < 1e-9


def test_relevance_from_query_supports_graded_and_binary():
    graded = relevance_from_query({"relevance": {"doc1": 3, "doc2": 1}})
    assert graded == {"doc1": 3.0, "doc2": 1.0}

    binary = relevance_from_query({"relevant_ids": ["doc1", "doc2"]})
    assert binary == {"doc1": 1.0, "doc2": 1.0}
