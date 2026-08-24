# Performance / Scale Benchmark Results

Run via `contextflow benchmark-scale`, backed by
`src/contextflow/evaluation/performance.py`. Every number below was
actually measured in this project's development environment — none of
this is estimated or extrapolated beyond what's explicitly marked as
such.

## Test environment (matters — see "How to read these numbers")

- 1 vCPU, 3.9 GiB RAM, Linux x86_64
- Python 3.12.3, CPython (no PyPy/JIT)
- Single process, no concurrent load
- Default `LocalHashEmbeddingProvider` (hashing-trick placeholder — see
  docs/concepts/embeddings.md). A real embedding provider (OpenAI/
  Cohere/Ollama) would have different (likely higher) per-document
  embedding cost, changing ingestion throughput; retrieval latency
  characteristics (brute-force cosine similarity cost) would be
  unaffected since that depends only on vector count and dimensionality.

## In-memory backend (`InMemoryVectorStore`)

| Corpus size | Ingest (docs/s) | Retrieval p50 | p95 | p99 |
|---|---|---|---|---|
| 100 | 38,934 | 0.79ms | 0.84ms | 37.09ms* |
| 500 | 38,641 | 3.91ms | 4.35ms | 7.40ms |
| 1,000 | 24,565 | 8.64ms | 9.14ms | 15.60ms |
| 2,000 | 32,638 | 17.48ms | 20.69ms | 33.66ms |
| 5,000 | 26,442 | 39.21ms | 45.54ms | 82.48ms |

\* The N=100 p99 spike is a real, reproducible, explained anomaly, not
noise: the very first retrieval call in a process pays a one-time ~37ms
cost from `rank_bm25`'s lazy import inside `KeywordRetriever` (Python
module import + its own internal setup), confirmed by running 5
sequential queries against a fresh engine: 37.04ms, then 0.50ms, 0.45ms,
0.46ms, 0.43ms. At small sample sizes (30 queries per benchmark point)
this one-time cost visibly skews p99; at larger N it's amortized away.
This is a real characteristic of the current benchmark harness and the
`rank_bm25` dependency, not a bug worth chasing — but reported here
rather than quietly excluded, since a benchmark that hides its own
artifacts is worse than no benchmark.

**Retrieval latency scales roughly linearly with corpus size** (p50:
0.8ms → 39ms from N=100 to N=5,000, roughly 8x per 10x growth once past
the cold-start noise) — expected and confirmed, not assumed: both
`InMemoryVectorStore` (brute-force cosine similarity, see
`storage/local.py`) and `KeywordRetriever` (BM25 over the full in-memory
corpus) are O(n) per query with no index structure. This is the correct,
honest characterization of "what will happen at 100K+ documents":
retrieval latency will keep growing linearly, not a cliff, but a real
approach-a-real-vector-database problem well before that point for any
latency-sensitive use case.

## Persistent backend (`SQLiteMetadataStore` + `FileVectorStore` + `FileGraphStore`)

### A real bug found and fixed during this benchmarking work

The first run of this benchmark against the persistent backend showed
ingestion throughput **dropping** as corpus size grew — 568 → 231 → 135
docs/s from N=100 to N=1,000. That's backwards; throughput should be
roughly flat or improve slightly with amortized fixed costs, not
collapse. The cause: `FileVectorStore.upsert()` and
`FileGraphStore.add_entity()`/`add_relationship()` rewrote their entire
JSON file to disk on **every single call** — O(n) work per write, O(n²)
total for ingesting n objects.

Fixed by adding batch write APIs (`upsert_batch`,
`add_entities_batch`, `add_relationships_batch` — see
`core/metadata.py`) that update in-memory state for the whole batch and
write to disk once, and wiring `ContextEngine.ingest()` to use them
(`tests/test_batch_writes.py` covers correctness: batched writes produce
identical results to the old per-item loop).

**Before the fix:**

| Corpus size | Ingest (docs/s) |
|---|---|
| 100 | 568 |
| 500 | 232 |
| 1,000 | 136 |

**After the fix** (same machine, same run methodology):

| Corpus size | Ingest (docs/s) | Retrieval p50 | p95 |
|---|---|---|---|
| 100 | 17,870 | 1.50ms | 1.72ms |
| 500 | 13,038 | 4.91ms | 5.26ms |
| 1,000 | 9,160 | 8.80ms | 10.31ms |
| 2,000 | 6,292 | 17.97ms | 19.58ms |

Roughly **30-70x higher throughput**, and it no longer collapses as
corpus size grows — the residual downward trend from 17,870 to 6,292
docs/s is expected and correct: one full-file JSON write per `ingest()`
call means each individual bulk-ingest call's write cost is O(n) in
however many objects that specific engine already holds, so calling
`ingest()` repeatedly against a growing workspace still costs more per
call as the file grows. Ingesting everything in one `ingest()` call (as
this benchmark does) avoids the old O(n²) *total* cost across many
small ingests, but a single very large ingest into an already-large
existing workspace still pays for rewriting the whole file. A real fix
for that (incremental/append-friendly persistent storage, or a real
embedded database) is Phase 13 (Scale) territory — see ROADMAP.md.

## What this does NOT tell you

- **Nothing here is tested past 5,000 objects.** Extrapolating these
  curves to "10M+ documents" (a real phrase from this project's
  aspirational roadmap) would be guessing, not measuring — Phase 13
  explicitly has not been attempted.
- **No concurrent load was tested.** All numbers are single-process,
  single-query-at-a-time. Real production traffic (many simultaneous
  requests) would show different — likely worse — latency due to lock
  contention (`SQLiteMetadataStore`/`MemoryStore`'s `threading.Lock`,
  see `docs/concepts/memory.md`) and GIL-bound Python execution.
- **No PostgreSQL/Qdrant/Neo4j backends were benchmarked here** — this
  covers only the local-first default backends. Real production
  deployments swapping in those backends would have entirely different
  (and likely much better at scale) characteristics, untested in this
  document.
- **Single run, single machine.** No statistical repeats, no variance
  reported beyond the percentiles already shown per run. Treat these as
  directionally informative, not precise benchmarks suitable for
  capacity planning.

## Reproducing these numbers

```bash
contextflow benchmark-scale --sizes 100,500,1000,2000,5000
contextflow benchmark-scale --sizes 100,500,1000,2000 --persistent
```

## Contributing

Benchmarking a different backend, a real embedding provider, or
concurrent load are all welcome contributions — see CONTRIBUTING.md. Any
new numbers should include the same level of methodology/caveat
disclosure as above; a performance number without its measurement
conditions is not more useful than no number.
