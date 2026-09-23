"""Evaluates ContextFlow as a context engine on MultiHop-RAG (Tang & Yang,
COLING 2024, github.com/yixuantt/MultiHop-RAG) — multi-document
retrieval over a shared corpus of 609 news articles, where each query's
evidence is spread across 2-4 different articles.

Unlike LoCoMo (benchmarks/external/locomo/), which tests conversational
memory, this tests what a context engine is for: pulling the right
pieces out of many long documents.

## Protocol (matches the paper's retrieval evaluation)

- Articles are ingested through ContextFlow's normal pipeline
  (`engine.ingest`), which splits them into ~1000-character chunks —
  about the paper's 256-token chunk size.
- A retrieved chunk counts as a hit if it contains one of the query's
  gold evidence `fact` strings, comparing with all whitespace removed.
- Hits@4, Hits@10, MAP@10 and MRR@10 use the paper's definitions
  (reimplemented here from its `retrieval_evaluate.py`). The 301
  `null_query` questions (no evidence) are excluded, as in the paper.

## What is compared

Same chunks, same embeddings, three ways of choosing context:

1. `vector-only` — naive RAG: top-k chunks by embedding similarity.
2. `contextflow` — `engine.retrieve()`: hybrid semantic + BM25 fusion
   and reranking.
3. `context-pack` — `engine.context_pack()` at a 2,048-token budget,
   scored on how much of the gold evidence ends up in the pack, against
   naive top-k chunks filled to the same budget.

It also reports how many gold facts don't appear verbatim in any chunk
(split across a chunk boundary, or altered by PII redaction). Those
queries can't reach 100% under this metric whatever the retriever does.

## Data license

MultiHop-RAG is released under ODC-BY (attribution). The data is
downloaded at run time, not bundled with this repository.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
import urllib.request
from functools import lru_cache
from pathlib import Path

from contextflow.core.context import ContextObject
from contextflow.embeddings.base import EmbeddingProvider, LocalHashEmbeddingProvider
from contextflow.engine import ContextEngine

DATA_URL = "https://huggingface.co/datasets/yixuantt/MultiHopRAG/resolve/main/{name}"
FILES = ("corpus.json", "MultiHopRAG.json")
PACK_TOKENS = 2048
CHARS_PER_TOKEN = 4  # same estimate the ContextPack compiler uses


def download(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        path = data_dir / name
        if not path.exists():
            print(f"Downloading {name} ...", file=sys.stderr)
            urllib.request.urlretrieve(DATA_URL.format(name=name), path)


def squash(text: str) -> str:
    """The paper's comparison form: all spaces and newlines removed."""
    return text.replace(" ", "").replace("\n", "")


def paper_metrics(retrieved: list[list[str]], gold: list[list[str]]) -> dict[str, float]:
    """Hits@10, Hits@4, MAP@10, MRR@10 as defined by the paper's
    retrieval_evaluate.py: a chunk is relevant if it contains any gold
    fact; MAP credits each gold fact once, at the first rank that
    contains it, normalized by min(#gold, 10)."""
    hits10 = hits4 = 0
    aps: list[float] = []
    rrs: list[float] = []
    for chunks, facts in zip(retrieved, gold, strict=True):
        facts = [squash(f) for f in facts]
        found: set[str] = set()
        first_rank = None
        ap_sum = 0.0
        for rank, chunk in enumerate(chunks[:10], start=1):
            chunk = squash(chunk)
            matched = [f for f in facts if f in chunk]
            if not matched:
                continue
            if first_rank is None:
                first_rank = rank
            new = [f for f in matched if f not in found]
            found.update(new)
            ap_sum += len(new) / rank
        hits10 += first_rank is not None
        hits4 += first_rank is not None and first_rank <= 4
        aps.append(ap_sum / min(len(facts), 10))
        rrs.append(1 / first_rank if first_rank else 0.0)
    n = len(gold)
    return {"Hits@10": hits10 / n, "Hits@4": hits4 / n, "MAP@10": sum(aps) / n, "MRR@10": sum(rrs) / n}


def coverage(texts: list[str], facts: list[str]) -> tuple[float, bool]:
    """Fraction of gold facts contained in the given context, and whether
    all of them are (what a multi-hop answer actually needs)."""
    blob = [squash(t) for t in texts]
    got = sum(any(squash(f) in b for b in blob) for f in facts)
    return got / len(facts), got == len(facts)


def fill_budget(texts: list[str], max_tokens: int) -> list[str]:
    """Naive-RAG baseline for the budget comparison: take top-ranked
    chunks in order until the token budget is spent."""
    out, used = [], 0
    for t in texts:
        cost = max(1, len(t) // CHARS_PER_TOKEN)
        if used + cost > max_tokens:
            continue
        out.append(t)
        used += cost
    return out


class _QueryCache(EmbeddingProvider):
    """Wraps a provider so each query is embedded once, even though the
    three configurations each ask for it."""

    def __init__(self, inner: EmbeddingProvider) -> None:
        self.inner = inner
        self.dimensions = inner.dimensions
        self.embed_query = lru_cache(maxsize=None)(inner.embed_query)  # type: ignore[method-assign]

    def embed(self, text: str) -> list[float]:
        return self.inner.embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self.inner.embed_batch(texts)


def build_engine(corpus: list[dict], provider: EmbeddingProvider) -> ContextEngine:
    engine = ContextEngine(embedding_provider=provider)
    engine.ingest(
        [
            ContextObject(
                id=f"article-{i}",
                content=article["body"],
                source=article["source"],
                metadata={"title": article["title"], "published_at": article["published_at"]},
            )
            for i, article in enumerate(corpus)
        ]
    )
    return engine


def evaluate(engine: ContextEngine, queries: list[dict]) -> dict:
    all_chunks = [squash(o.content) for o in engine.metadata_store.all()]
    gold = [[e["fact"] for e in q["evidence_list"]] for q in queries]
    unreachable = sum(
        not any(squash(f) in c for c in all_chunks) for facts in gold for f in facts
    )

    naive, flow = [], []
    pack_cov, pack_all, naive_cov, naive_all = [], [], [], []
    for q, facts in zip(queries, gold, strict=True):
        text = q["query"]
        naive_hits = [o.content for o in engine._semantic.retrieve(text, limit=20)]
        naive.append(naive_hits[:10])
        flow.append([o.content for o in engine.retrieve(text, limit=10)])

        pack = engine.context_pack(text, max_tokens=PACK_TOKENS, limit=20)
        pack_texts = [
            item["content"]
            for bucket in ("facts", "documents", "conversations", "risks")
            for item in getattr(pack, bucket)
        ]
        c, a = coverage(pack_texts, facts)
        pack_cov.append(c)
        pack_all.append(a)
        c, a = coverage(fill_budget(naive_hits, PACK_TOKENS), facts)
        naive_cov.append(c)
        naive_all.append(a)

    return {
        "num_queries": len(queries),
        "num_chunks": len(all_chunks),
        "unreachable_facts": unreachable,
        "total_facts": sum(len(f) for f in gold),
        "vector-only": paper_metrics(naive, gold),
        "contextflow": paper_metrics(flow, gold),
        f"budget@{PACK_TOKENS}": {
            "vector-only": {
                "evidence_recall": statistics.mean(naive_cov),
                "all_evidence": statistics.mean(naive_all),
            },
            "context-pack": {
                "evidence_recall": statistics.mean(pack_cov),
                "all_evidence": statistics.mean(pack_all),
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--data-dir", default=str(Path(tempfile.gettempdir()) / "multihop_rag"))
    parser.add_argument("--provider", choices=["hash", "ollama"], default="hash")
    parser.add_argument("--model", default="nomic-embed-text", help="Ollama model")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate the first N answerable queries")
    parser.add_argument("--output", default=None, help="Save results as JSON")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    download(data_dir)
    corpus = json.loads((data_dir / "corpus.json").read_text(encoding="utf-8"))
    queries = [
        q
        for q in json.loads((data_dir / "MultiHopRAG.json").read_text(encoding="utf-8"))
        if q["question_type"] != "null_query"
    ][: args.limit]

    if args.provider == "ollama":
        from contextflow.embeddings.ollama import OllamaEmbeddingProvider

        inner: EmbeddingProvider = OllamaEmbeddingProvider(model=args.model, timeout=300)
    else:
        inner = LocalHashEmbeddingProvider()
    provider = _QueryCache(inner)

    t0 = time.perf_counter()
    engine = build_engine(corpus, provider)
    t1 = time.perf_counter()
    result = evaluate(engine, queries)
    t2 = time.perf_counter()
    result["provider"] = args.provider + (f" ({args.model})" if args.provider == "ollama" else "")
    result["seconds"] = {"ingest": round(t1 - t0, 1), "evaluate": round(t2 - t1, 1)}

    print(f"\nMultiHop-RAG — provider={result['provider']}, "
          f"{result['num_queries']} queries, {result['num_chunks']} chunks")
    print(f"Gold facts not verbatim in any chunk: {result['unreachable_facts']}/{result['total_facts']}")
    print(f"\n{'':<14}{'Hits@4':>9}{'Hits@10':>9}{'MAP@10':>9}{'MRR@10':>9}")
    for name in ("vector-only", "contextflow"):
        m = result[name]
        print(f"{name:<14}{m['Hits@4']:>9.4f}{m['Hits@10']:>9.4f}{m['MAP@10']:>9.4f}{m['MRR@10']:>9.4f}")
    budget = result[f"budget@{PACK_TOKENS}"]
    print(f"\nWithin a {PACK_TOKENS}-token budget:{'evidence recall':>18}{'all evidence':>14}")
    for name, m in budget.items():
        print(f"  {name:<30}{m['evidence_recall']:>18.1%}{m['all_evidence']:>14.1%}")
    print(f"\nTime: ingest {result['seconds']['ingest']}s, evaluate {result['seconds']['evaluate']}s")

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
