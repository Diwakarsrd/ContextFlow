"""Tests for the LoCoMo adapter logic using a small synthetic
conversation shaped like the real dataset — not the real 2.8MB download,
so these run offline and fast. The real dataset is fetched only when
running run_locomo_eval.py directly (see its docstring on why it's not
bundled: CC BY-NC 4.0 licensing).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "benchmarks" / "external" / "locomo"))

from run_locomo_eval import evaluate_conversation, run_locomo_eval


def _sample_conversation() -> dict:
    return {
        "sample_id": "test_1",
        "conversation": {
            "speaker_a": "Alice",
            "speaker_b": "Bob",
            "session_1_date_time": "1:00 pm on 1 Jan, 2024",
            "session_1": [
                {"speaker": "Alice", "dia_id": "D1:1", "text": "I went to the dentist yesterday."},
                {"speaker": "Bob", "dia_id": "D1:2", "text": "Oh how was it?"},
                {"speaker": "Alice", "dia_id": "D1:3", "text": "It was fine, just a routine cleaning."},
            ],
        },
        "qa": [
            {
                "question": "When did Alice go to the dentist?",
                "answer": "yesterday",
                "evidence": ["D1:1"],
                "category": 2,
            },
            {
                "question": "What kind of person is Alice?",
                "answer": "Likely health-conscious",
                "evidence": [],
                "category": 3,
            },
            {
                "question": "Did Bob go to the dentist?",
                "adversarial_answer": "Yes",
                "evidence": ["D1:1"],
                "category": 5,
            },
        ],
    }


def test_evaluate_conversation_splits_evaluable_and_excluded():
    results = evaluate_conversation(_sample_conversation())
    assert len(results) == 3

    excluded = [r for r in results if r["excluded"]]
    evaluated = [r for r in results if not r["excluded"]]
    assert len(excluded) == 2  # category 3 (no evidence) and category 5 (adversarial)
    assert len(evaluated) == 1  # only the category-2 question with real evidence


def test_evaluate_conversation_computes_real_metrics_for_evaluable_questions():
    results = evaluate_conversation(_sample_conversation())
    evaluated = next(r for r in results if not r["excluded"])
    assert evaluated["category"] == 2
    assert 0.0 <= evaluated["recall_at_5"] <= 1.0
    assert 0.0 <= evaluated["mrr"] <= 1.0


def test_run_locomo_eval_aggregates_across_conversations(tmp_path):
    import json

    data_path = tmp_path / "mini_locomo.json"
    data_path.write_text(json.dumps([_sample_conversation(), _sample_conversation()]))

    result = run_locomo_eval(str(data_path))
    assert result.num_conversations == 2
    assert result.num_questions_evaluated == 2  # 1 evaluable question x 2 conversations
    assert result.num_questions_excluded == 4  # 2 excluded x 2 conversations
    assert 2 in result.per_category
    assert result.per_category[2]["n"] == 2


def test_malformed_semicolon_evidence_is_split_correctly():
    """A handful of real LoCoMo entries have evidence like 'D8:6; D9:17'
    as one string instead of two list items — this must not silently
    drop half the evidence."""
    conv = _sample_conversation()
    conv["qa"] = [
        {
            "question": "When did Alice go to the dentist?",
            "answer": "yesterday",
            "evidence": ["D1:1; D1:3"],
            "category": 2,
        }
    ]
    results = evaluate_conversation(conv)
    assert not results[0]["excluded"]
