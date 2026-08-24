# ContextBench v0.1

`contextflow evaluate` runs retrieval quality metrics (Recall@k,
Precision@k, MRR, NDCG@k) against a labeled dataset here, and can save/
compare results so a PR can honestly claim "improved retrieval recall by
4.2%" instead of just asserting it.

```bash
contextflow evaluate --benchmark benchmarks/datasets/acme_support_v1.yaml
contextflow evaluate --benchmark benchmarks/datasets/acme_support_v1.yaml --output baseline.json
contextflow evaluate --benchmark benchmarks/datasets/acme_support_v1.yaml --compare-to baseline.json
```

## Datasets

### `acme_support_v1` (18 queries, 30 documents)

A synthetic customer-support + engineering knowledge base for a
fictional company. See "Construction methodology" below for exactly how
and why it was built this way.

## Construction methodology (read this before trusting the numbers)

**This dataset is synthetic, not derived from real user queries or a
real support corpus.** Nobody has validated that these queries resemble
what real users actually ask, because there is no production usage yet
to draw from. That's stated plainly here rather than left implicit,
because a benchmark's credibility depends entirely on knowing what it
is and isn't measuring.

What it *does* verify: whether retrieval can distinguish between
topically-similar documents rather than trivially matching on one
obviously-unique keyword. Every query has at least one **deliberate
distractor** in the corpus — a document that shares vocabulary or topic
with the correct answer but isn't the right one (e.g.
`doc_refund_policy` vs. `doc_refund_exceptions`, or the two incident
postmortems). A benchmark where every query has exactly one
lexically-unique matching document would trivially score 100% recall
under BM25 alone, which would test nothing.

**Evidence this actually has meaningful difficulty**: running it against
the default `LocalHashEmbeddingProvider` (see docs/concepts/embeddings.md
— a placeholder with no real semantic understanding) produces
Recall@5 ≈ 61%, not 100% or 0%. Real embedding providers should score
meaningfully higher; if a future change to retrieval logic doesn't move
these numbers when it should, or moves them when it shouldn't, that's a
signal to look closer.

One query (`GDPR data deletion`) uses **graded relevance** to
demonstrate the NDCG metric distinguishing a directly-responsive
document from a topically-related-but-less-relevant one — see the
`relevance:` field in that query's YAML entry.

## Dataset format

```yaml
version: 1
name: my_benchmark_v1
corpus:
  - id: doc1
    content: "..."
queries:
  - query: "What is the refund policy?"
    relevant_ids: [doc1]          # binary relevance
  - query: "..."
    relevance: {doc1: 3, doc2: 1}  # graded relevance (0-3 typical);
                                    # used for NDCG, and for
                                    # recall/precision/MRR any doc with
                                    # a positive grade counts as relevant
```

## Metrics

- **Recall@k** / **Precision@k** — standard.
- **MRR** — reciprocal rank of the first relevant result.
- **NDCG@k** — uses the exponential-gain formula `(2^rel - 1) /
  log2(rank + 1)` (same as sklearn's `ndcg_score`, TensorFlow Ranking),
  not the older linear-gain formula from the original Järvelin &
  Kekäläinen paper — the two give different numbers for the same input,
  so don't compare this module's NDCG against an implementation that
  uses linear gain without checking which formula it uses.

See `src/contextflow/evaluation/retrieval.py` for the implementations —
each metric has a correctness test in `tests/test_evaluation_metrics.py`,
including NDCG checked against an independently hand-derived value (not
just "does the function return something").

## What ContextBench v0.1 does NOT cover

- **Faithfulness** (does a generated answer actually reflect the
  retrieved context?) — `evaluation/faithfulness.py` is still a stub
  requiring an LLM-judge implementation.
- **Agent task success** — whether an agent given this context actually
  completes the task correctly. That requires running real agents, not
  just retrieval.
- **Latency/throughput at scale** — this dataset is small (30 docs) by
  design, to keep the benchmark fast and its difficulty easy to reason
  about. It says nothing about retrieval quality or speed at 100,000+
  documents.
- **Real-world query distribution** — see "Construction methodology"
  above.

## Contributing a benchmark

New domain-specific benchmark sets (code search, legal, real support
ticket exports with PII scrubbed) are welcome — open a PR adding a new
`.yaml` file under `datasets/` plus a methodology note in this file
covering: how the corpus was built, how relevance judgments were
assigned and by whom, and what the dataset does and doesn't test. A
benchmark without a stated methodology is not more trustworthy than no
benchmark — see CONTRIBUTING.md ("Improve retrieval").
