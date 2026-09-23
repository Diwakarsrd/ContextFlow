"""Offline tests for the MultiHop-RAG adapter's scoring, checked against
hand-computed values for the paper's metric definitions. The real
dataset is only downloaded when running the eval script directly."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "benchmarks" / "external" / "multihop_rag"))

from run_multihop_rag_eval import coverage, fill_budget, paper_metrics


def test_paper_metrics_hand_computed():
    gold = [["fact A", "fact B"]]
    # rank 1 miss, rank 2 has A, rank 3 has A again (no new credit), rank 5 has B
    retrieved = [["noise", "xx fact A xx", "fact A", "noise", "yy factB yy"]]
    m = paper_metrics(retrieved, gold)
    assert m["Hits@4"] == 1.0
    assert m["Hits@10"] == 1.0
    assert m["MRR@10"] == pytest.approx(1 / 2)
    # AP = (1/2 + 1/5) / min(2, 10); whitespace is ignored ("factB" matches "fact B")
    assert m["MAP@10"] == pytest.approx((1 / 2 + 1 / 5) / 2)


def test_paper_metrics_counts_a_miss_and_late_hit():
    gold = [["needle"], ["needle"]]
    retrieved = [["hay"] * 10, ["hay"] * 5 + ["needle"]]
    m = paper_metrics(retrieved, gold)
    assert m["Hits@10"] == 0.5
    assert m["Hits@4"] == 0.0
    assert m["MRR@10"] == pytest.approx((0 + 1 / 6) / 2)


def test_coverage_and_budget():
    facts = ["alpha beta", "gamma"]
    assert coverage(["x alphabeta x", "gamma!"], facts) == (1.0, True)
    assert coverage(["alpha beta"], facts) == (0.5, False)
    # 40 chars ~ 10 tokens each: only two fit in a 25-token budget
    assert fill_budget(["a" * 40, "b" * 40, "c" * 40], 25) == ["a" * 40, "b" * 40]
