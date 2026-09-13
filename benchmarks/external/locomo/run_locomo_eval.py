# ruff: noqa
"""Evaluates ContextFlow against LoCoMo (Maharana et al., ACL 2024) —
a real, externally-authored, widely-used benchmark, unlike
ContextBench (benchmarks/datasets/acme_support_v1.yaml), which we wrote
ourselves.

## Why this exists

ContextBench v0.1's own dataset is honestly disclosed as synthetic and
self-authored. That's fine for regression tracking during development,
but it says nothing about how ContextFlow compares to real competitors
(Mem0, Zep, Letta) who all report numbers against LoCoMo and/or
LongMemEval. This script closes that gap for LoCoMo.

## What this measures — and what it does NOT

LoCoMo's official protocol has an LLM (e.g. GPT-4o-mini) generate an
answer from retrieved context, then an LLM judge scores it against the
gold answer (F1/accuracy). **This script does not do that.** It has no
LLM-judge pipeline (see evaluation/faithfulness.py — that's a
documented stub) and no API key configured in this environment.

Instead, this measures **retrieval coverage**: for each question, does
ContextFlow's retrieve() surface the dialogue turn(s) LoCoMo's authors
annotated as evidence, in the top-k? This is the same honest framing
used by other retrieval-only systems benchmarked against LoCoMo (e.g.
the published "Engram" results, which report R@5/R@10/NDCG@5 and
explicitly note they are not comparable to F1-based numbers from
systems with an answer-generation stage). If you plug in a real
embedding provider (OpenAI/Cohere/Ollama — see
docs/concepts/embeddings.md) and add an LLM-judge answering stage on
top of these results, you could reproduce the official protocol; this
script does not attempt that.

## Scope: which questions are evaluated

LoCoMo's `qa` entries have five categories:
  1 = single-hop, 2 = temporal reasoning, 3 = commonsense/open-ended,
  4 = multi-hop, 5 = adversarial (no real answer exists).

Only categories 1, 2, and 4 have a non-empty `evidence` list pointing
to real dialogue turn IDs — those are the only ones "did retrieval find
the evidence turn" is a meaningful question for. Category 3 questions
are largely open-ended commonsense reasoning with no cited turn, and
category 5 questions are adversarial (the premise is false, evidence
points to an unrelated fact) — evaluating retrieval coverage against
either would not mean what it looks like it means, so both are
excluded and reported as excluded, not silently dropped.

## Data license

LoCoMo (github.com/snap-research/locomo) is released under
**CC BY-NC 4.0 — non-commercial**. This script downloads it at run time
rather than bundling it in the repo, so ContextFlow's own Apache 2.0
license never has to touch LoCoMo's non-commercial terms. Don't
redistribute the downloaded file as part of this project.
"""

from __future__ import annotations

import json
import statistics
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from contextflow.core.context import ContextObject
from contextflow.engine import ContextEngine
from contextflow.evaluation.retrieval import mean_reciprocal_rank, ndcg_at_k, recall_at_k

LOCOMO_URL = "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"
EVALUABLE_CATEGORIES = {1, 2, 4}  # see module docstring for why 3 and 5 are excluded
CATEGORY_NAMES = {1: "single-hop", 2: "temporal", 4: "multi-hop"}


@dataclass
class LocomoResult:
    num_conversations: int
    num_questions_evaluated: int
    num_questions_excluded: int
    recall_at_5: float
    recall_at_10: float
    mrr: float
    ndcg_at_5: float
    per_category: dict[int, dict[str, float]] = field(default_factory=dict)


def download_locomo(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if Path(path).exists():
        return
    print(f"Downloading LoCoMo from {LOCOMO_URL} ...", file=sys.stderr)
    urllib.request.urlretrieve(LOCOMO_URL, path)


def _turn_content(turn: dict) -> str:
    return f"{turn['speaker']}: {turn['text']}"


def evaluate_conversation(conv: dict, engine_factory=None) -> list[dict]:
    """Ingest one LoCoMo conversation's dialogue turns and evaluate every
    evaluable QA pair against it. Returns one result dict per question.
    `engine_factory` defaults to a fresh ContextEngine() (the honest
    zero-config baseline); pass e.g.
    `lambda: ContextEngine(embedding_provider=SpacyEmbeddingProvider())`
    to test a real embedding provider instead."""
    engine = engine_factory() if engine_factory else ContextEngine()
    conversation = conv["conversation"]
    session_keys = sorted(
        (k for k in conversation if k.startswith("session_") and not k.endswith("_date_time")),
        key=lambda k: int(k.split("_")[1]),
    )

    objects = []
    for session_key in session_keys:
        for turn in conversation[session_key]:
            objects.append(
                ContextObject(id=turn["dia_id"], content=_turn_content(turn), source="locomo")
            )
    engine.ingest(objects)

    results = []
    for qa in conv["qa"]:
        category = qa.get("category")
        if category not in EVALUABLE_CATEGORIES:
            results.append({"excluded": True, "category": category})
            continue
        evidence = qa.get("evidence", [])
        # A handful of evidence entries are malformed in the source data
        # (e.g. "D8:6; D9:17" as one string instead of two list items) —
        # split defensively rather than skip the question outright.
        evidence_ids: set[str] = set()
        for e in evidence:
            evidence_ids.update(x.strip() for x in e.split(";"))
        if not evidence_ids:
            results.append({"excluded": True, "category": category})
            continue

        retrieved = engine.retrieve(qa["question"], limit=10)
        retrieved_ids = [obj.id for obj in retrieved]

        results.append(
            {
                "excluded": False,
                "category": category,
                "recall_at_5": recall_at_k(retrieved_ids, evidence_ids, 5),
                "recall_at_10": recall_at_k(retrieved_ids, evidence_ids, 10),
                "mrr": mean_reciprocal_rank(retrieved_ids, evidence_ids),
                "ndcg_at_5": ndcg_at_k(retrieved_ids, {e: 1.0 for e in evidence_ids}, 5),
            }
        )
    return results


def run_locomo_eval(
    data_path: str, limit_conversations: int | None = None, engine_factory=None
) -> LocomoResult:
    data = json.loads(Path(data_path).read_text())
    if limit_conversations:
        data = data[:limit_conversations]

    all_results = []
    for conv in data:
        all_results.extend(evaluate_conversation(conv, engine_factory))

    evaluated = [r for r in all_results if not r["excluded"]]
    excluded = [r for r in all_results if r["excluded"]]

    per_category: dict[int, dict[str, float]] = {}
    for cat in EVALUABLE_CATEGORIES:
        cat_results = [r for r in evaluated if r["category"] == cat]
        if not cat_results:
            continue
        per_category[cat] = {
            "n": len(cat_results),
            "recall_at_5": statistics.mean(r["recall_at_5"] for r in cat_results),
            "recall_at_10": statistics.mean(r["recall_at_10"] for r in cat_results),
            "mrr": statistics.mean(r["mrr"] for r in cat_results),
            "ndcg_at_5": statistics.mean(r["ndcg_at_5"] for r in cat_results),
        }

    return LocomoResult(
        num_conversations=len(data),
        num_questions_evaluated=len(evaluated),
        num_questions_excluded=len(excluded),
        recall_at_5=statistics.mean(r["recall_at_5"] for r in evaluated),
        recall_at_10=statistics.mean(r["recall_at_10"] for r in evaluated),
        mrr=statistics.mean(r["mrr"] for r in evaluated),
        ndcg_at_5=statistics.mean(r["ndcg_at_5"] for r in evaluated),
        per_category=per_category,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("data_path", nargs="?", default="/tmp/locomo10.json")
    parser.add_argument(
        "--provider",
        choices=["hash", "spacy"],
        default="hash",
        help="Embedding provider: 'hash' (zero-config placeholder, default) or "
        "'spacy' (real local semantic embeddings, requires: pip install spacy && "
        "python -m spacy download <model>)",
    )
    parser.add_argument(
        "--model",
        default="en_core_web_md",
        help="spaCy model to use with --provider spacy (default: en_core_web_md). "
        "en_core_web_lg scores substantially higher in testing (see RESULTS.md) "
        "at the cost of a ~400MB download: python -m spacy download en_core_web_lg",
    )
    args = parser.parse_args()

    download_locomo(args.data_path)

    engine_factory = None
    if args.provider == "spacy":
        from contextflow.embeddings.spacy_local import SpacyEmbeddingProvider

        provider = SpacyEmbeddingProvider(model=args.model)
        engine_factory = lambda: ContextEngine(embedding_provider=provider)

    result = run_locomo_eval(args.data_path, engine_factory=engine_factory)

    model_suffix = f", model={args.model}" if args.provider == "spacy" else ""
    print(f"\nLoCoMo retrieval-coverage evaluation ({result.num_conversations} conversations, "
          f"provider={args.provider}{model_suffix})")
    print(f"Evaluated: {result.num_questions_evaluated} questions "
          f"(categories 1/2/4 with real evidence)")
    print(f"Excluded: {result.num_questions_excluded} questions (category 3/5, or no evidence)")
    print(f"\n{'Metric':<15}{'Value':>10}")
    print(f"{'Recall@5':<15}{result.recall_at_5:>10.1%}")
    print(f"{'Recall@10':<15}{result.recall_at_10:>10.1%}")
    print(f"{'MRR':<15}{result.mrr:>10.3f}")
    print(f"{'NDCG@5':<15}{result.ndcg_at_5:>10.3f}")
    print("\nPer category:")
    for cat, stats in sorted(result.per_category.items()):
        print(f"  {CATEGORY_NAMES[cat]:<12} (n={stats['n']:>4.0f})  "
              f"R@5={stats['recall_at_5']:.1%}  R@10={stats['recall_at_10']:.1%}  "
              f"MRR={stats['mrr']:.3f}  NDCG@5={stats['ndcg_at_5']:.3f}")
