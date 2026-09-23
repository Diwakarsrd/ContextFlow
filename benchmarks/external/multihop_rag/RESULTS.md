# ContextFlow on MultiHop-RAG — multi-document retrieval

[MultiHop-RAG](https://github.com/yixuantt/MultiHop-RAG) (Tang & Yang,
COLING 2024) is an external benchmark for exactly what a context engine
does: a corpus of 609 long news articles (~1.06M words), and 2,255
answerable questions whose evidence is spread across 2–4 *different*
articles. It tests whether the right pieces come out of many long
documents, which LoCoMo (conversational memory) does not.

Run it: `python benchmarks/external/multihop_rag/run_multihop_rag_eval.py --provider ollama`
(downloads the dataset; see the script docstring for the protocol).

## Results (2,255 queries, 7,259 chunks)

Same chunks and same embeddings in every row of a block; only how the
context is selected changes.

**Ollama `nomic-embed-text` (local, no API key)**

| | Hits@4 | Hits@10 | MAP@10 | MRR@10 |
|---|---|---|---|---|
| Vector-only (naive RAG) | 0.5774 | 0.7681 | 0.2135 | 0.4488 |
| **ContextFlow** (`engine.retrieve`) | **0.6745** | **0.8297** | **0.2687** | **0.5398** |

**Zero-config default (hash placeholder, no embedding model)**

| | Hits@4 | Hits@10 | MAP@10 | MRR@10 |
|---|---|---|---|---|
| Vector-only | 0.0111 | 0.0226 | 0.0029 | 0.0074 |
| **ContextFlow** | **0.4652** | **0.7233** | **0.1205** | **0.2544** |

**Context Pack vs. naive top-k, same 2,048-token budget** (Ollama)

| | Evidence recall | All evidence in context |
|---|---|---|
| Vector-only top-k, filled to budget | 41.4% | 15.4% |
| **Context Pack** | **50.2%** | **23.1%** |

"All evidence" is the share of questions for which *every* gold fact
fits in the context, which is what a multi-hop answer actually needs:
the Context Pack delivers complete evidence 1.5x as often as naive RAG
in the same token budget.

## Against the paper's published numbers

From the paper's retrieval table (256-token chunks, top-10, null
queries excluded):

| Paper configuration | Hits@4 | Hits@10 | MRR@10 |
|---|---|---|---|
| bge-large-en-v1.5 (best without reranker) | 0.5221 | 0.6718 | 0.4298 |
| voyage-02 + bge-reranker-large (best Hits with reranker) | 0.6625 | 0.7467 | 0.5860 |
| **ContextFlow + nomic-embed-text, no reranker model** | **0.6745** | **0.8297** | 0.5398 |

ContextFlow's Hits@4 and Hits@10 are higher than every configuration in
the paper, including those with a cross-encoder reranker, using a free
local embedding model. MRR is above every no-reranker configuration and
below the best reranked ones.

**Read these caveats before quoting the comparison:**

- **MAP@10 doesn't line up and isn't claimed.** Ours (0.27) is below
  the paper's (0.34–0.48) even though our Hits are higher, using the
  metric as defined in the paper's `retrieval_evaluate.py` (reimplemented
  here and unit-tested against hand-computed cases). We haven't found
  the cause; until we do, compare Hits and MRR, not MAP.
- **Different pipelines.** The paper used LlamaIndex's sentence splitter
  (256 tokens); ContextFlow's own chunker packs whole sentences into
  ~1000-character chunks. Chunking affects every metric.
- **Keyword search does a lot of the work here.** Queries name outlets
  and people ("as reported by The Verge and TechCrunch"), which BM25
  matches exactly — that's why even the zero-config hash setup reaches
  Hits@10 0.72. The paper's table covers embedding-only retrievers (its
  repo has since added BM25/hybrid scripts, not reported there). With the
  same embeddings, the hybrid design is what lifts ContextFlow over
  vector-only (0.768 -> 0.830 Hits@10).
- **Retrieval only.** No answer generation or LLM judging.
- 102 of 6,084 gold facts (1.7%) don't appear verbatim in any chunk
  (split across a chunk boundary or changed by PII redaction), so those
  questions can't score on them.
- One run, one machine (CPU-only Windows laptop, 8 GB RAM). Ollama run:
  ingest 8.5 min, evaluation 33 min.

## Bugs this benchmark found (fixed in the same change)

- **Chunks of a document overwrote each other.** Every chunk kept its
  parent's id and the stores are keyed by id, so only the *last* chunk
  of any document over ~1,000 characters was retrievable. Chunks now get
  `<id>#chunk-<n>` ids with `parent_id` metadata.
- **The chunker cut mid-word and mid-sentence.** It now packs whole
  sentences, so a fact isn't split between two chunks.
- **Vector search was a pure-Python loop**: 3.3 s per search at 7,259
  768-d vectors. It's now numpy-vectorized: 3.5 ms.
