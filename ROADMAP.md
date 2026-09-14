# Roadmap

This is the project's full plan, from the current scaffold through to
"open context standard." Early phases are scoped tightly on purpose —
a narrow, excellent core beats a big-bang launch. Later phases (5+)
describe direction, not commitments; they need a real team, real
infrastructure, and real user feedback to get right, and the further
down this file you go, the more that's true.

Status legend:  shipped in this scaffold ·  partially built ·
⬜ not started

## Phase 0 — Foundation 

Repo hygiene: README, ARCHITECTURE, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT,
CHANGELOG, LICENSE (Apache 2.0), packaging, CLI skeleton, Docker Compose,
CI (GitHub Actions: test/lint/typecheck, Docker build, release), pytest,
ruff, mypy, pre-commit config, issue/PR templates, Dependabot.

`git clone ... && docker compose up && contextflow --help` all work.

## Phase 1 — v0.1 local context engine  (core) /  (connectors)

- [x] `ContextObject`, `ContextPack`, `Entity`, `Relationship`, `Source`
- [x] Persistent local storage — **the P0 fix**: SQLite metadata store +
      JSON-file vector/graph stores under `.contextflow/`, so
      `contextflow ingest` and `contextflow search` share state across
      separate process invocations (previously in-memory only)
- [x] Retrieval: keyword (BM25), semantic (pluggable embed_fn), hybrid
      (reciprocal rank fusion), quality-weighted reranking
- [x] Ingestion pipeline: parsing, normalization, chunking, dedup
- [x] Filesystem connector (fully working)
- [x] GitHub connector (real REST API implementation — issues, PRs, README)
- [x] PostgreSQL connector — live-tested end-to-end against a real
      running PostgreSQL instance (`tests/test_postgres_live.py`), not
      just unit-tested logic; CI runs it against a Postgres service
      container on every PR
- [x] Python SDK, REST API, CLI (`init/ingest/search/context-pack/serve/mcp/evaluate`)
- [x] TypeScript SDK (`sdk/typescript`) — full client (retrieve,
      contextPack, trace, remember/recall), typed errors, and a real test
      suite that spins up the actual Python REST server as a subprocess
      and hits it over real HTTP (no mocked fetch). Required adding
      REST endpoints for trace and memory that hadn't existed before —
      those are new, tested, and documented too.
- [x] MCP server (search_context, get_context_pack, get_entity,
      get_relationships, get_context_graph, explain_context)
- [x] Evaluation harness — see Phase 9 (ContextBench v0.1) below for the
      real dataset, metrics, and methodology
- [x] "5-minute demo" — `contextflow context-pack "..."` prints a rich,
      readable panel with facts/sources/confidence
- [x] Real embedding providers (OpenAI, Cohere, Ollama) behind a common
      `EmbeddingProvider` interface, selectable via
      `$CONTEXTOS_EMBEDDING_PROVIDER` — replaces the previous "only a
      hashing placeholder" gap. The placeholder (`LocalHashEmbeddingProvider`)
      remains the zero-config default, clearly documented as not
      semantically meaningful.
- [ ] Basic memory (working + session) — interfaces exist, persistence doesn't

## Phase 2 — Production retrieval engine ⬜

Query rewriting/expansion, metadata filters, temporal retrieval,
entity-aware retrieval, parent/child retrieval, multi-hop retrieval,
caching, adaptive top-k, a public benchmark with Recall/Precision/MRR/NDCG
tracked over time.

## Phase 3 — Real knowledge graph ⬜ (naive version )

What's shipped: co-mention graph over regex-based proper-noun extraction
(`graph/entity_extraction.py`) — explicitly a heuristic, not NER — feeding
`engine.get_entity()`, `get_relationships()`, `get_context_graph()`.

What's next: real entity resolution (merge "Acme"/"Acme Corp"/"@acme"),
model-based entity/relationship extraction, typed relationships beyond
co-mention, multi-hop graph retrieval as a first-class retrieval strategy.

## Phase 4 — Context compiler maturity 

What's shipped: token-budgeted compilation, per-item source/confidence/
freshness provenance, a `ConflictingClaim` schema, and real pipeline
tracing/observability (see below) — including `explain_context` now
returning the actual reranker formula (base score + weighted freshness/
confidence/trust = final score) instead of raw fields.

What's next: real conflict detection (claim extraction + comparison —
currently a documented no-op stub), compression/summarization beyond
truncation.

### Tracing / observability 

`engine.retrieve_with_trace()` / `context_pack_with_trace()` record
per-stage candidate counts and timing (route → permission filter →
tenant filter → rerank → limit → compile), exposed via `contextflow trace
"<query>"` and the MCP `trace_query`/`explain_context` tools. In-memory
ring buffer per engine instance, not persisted — see
docs/concepts/tracing.md for what this does and doesn't cover.

## Phase 5 — Memory system  (v1 shipped, no learning yet)

What's shipped: working memory (L1, in-process/ephemeral, by design —
never persisted) plus session/user/agent/organization memory (L2-L5),
all backed by one shared, persistent, thread-safe `MemoryStore`
(`memory/store.py`) — SQLite-backed, survives across separate process
invocations, recall ranked by BM25 keyword relevance. Exposed via
`contextflow memory remember/recall` and the MCP `remember`/`get_memory`
tools.

Finding and fixing this shipped a real bug, not just a feature: the
`mcp` package runs tool calls in a worker-thread pool, and a naive
SQLite connection isn't safe across threads. Both `MemoryStore` and
`SQLiteMetadataStore` now use `check_same_thread=False` plus an explicit
lock, with a regression test that reproduces the original crash
(`tests/test_sqlite_thread_safety.py`).

What's next: **consolidation** (merging/summarizing related facts over
time), **decay** (deprioritizing or forgetting stale facts
automatically), **importance scoring**, and **conflict resolution**
between contradictory facts. These need real usage data to design well —
v1 recall is keyword relevance + recency, deliberately nothing smarter.

## Phase 6 — Connectors platform 

What's shipped:

- **Slack** (channels + thread replies, pagination, channel-name
  resolution) and **Notion** (pages with block text, database rows,
  search-based discovery) — both real implementations, both tested
  end-to-end against mocked APIs (`tests/test_slack_connector.py`,
  `tests/test_notion_connector.py`), **neither yet verified against a
  live workspace** (`slack.com`/`api.notion.com` aren't reachable from
  this project's development environment — unlike Postgres, which got a
  real live server). If you run either against production, please
  report back what you find.

What's next: Jira, Confluence, GitLab, Discord, Linear, Google Drive,
S3, Snowflake, BigQuery, Databricks, MongoDB — each behind the existing
`Connector` interface. Goal: most of these come from the community, not
from a single team building 20 integrations.

## Phase 7 — Governance & security  (real, not RBAC-complete)

What's shipped:

- Object-level allow-lists (`ContextObject.permissions`) plus role-based
  access (`ContextObject.allowed_roles` + `RoleStore`/`PolicyEngine`),
  enforced *before* ranking, not after (`governance/permissions.py`)
- `contextflow auth assign-role <principal> <role>` / `auth roles <principal>`
- Tenant isolation: `ContextObject.tenant_id` + `engine.retrieve(tenant_id=...)`
  — untenanted content stays global/shared, tenant-scoped content is
  isolated per tenant
- Pattern-based PII/secret detection with redaction
  (`governance/pii.py`: email, phone, SSN, Luhn-validated credit cards,
  AWS keys, generic API-key-shaped secrets) — not wired into ingestion
  automatically yet; call `redact_pii()` explicitly until an
  ingestion-time policy hook lands
- API key authentication shared by the REST API and MCP-over-HTTP
  (`contextflow auth create-key`), principal always derived server-side
  from a verified key — fixing a real spoofing gap where v0.1's REST API
  trusted a client-supplied `principal` field in the request body
- Keys are **hashed at rest** (SHA-256, never plaintext), support
  optional expiry, and can be revoked (`contextflow auth revoke-key`)
- Per-IP rate limiting on failed auth attempts on the REST API
  (`auth/rate_limit.py`) — in-memory/single-process, see its docstring
  for the multi-replica-deployment caveat
- Structured audit logging with querying (`contextflow audit query`),
  wired into both REST endpoints
- A written [security self-review](docs/security_review.md) — self-assessed,
  not independently audited

What's next: real ABAC (condition-based policies beyond role membership),
data masking as an ingestion-time policy rather than a manual call,
per-key scoping (today a key grants everything its principal can see), a
distributed rate limiter for multi-replica deployments, SOC2-oriented
architecture review, and an actual **third-party** security audit — the
self-review above was written by the same person who wrote the code it
reviews. This phase still needs a security-focused contributor or team,
not a single coding pass.

## Phase 8 — Real-time context ⬜

Webhooks, CDC, an event bus, incremental indexing, real-time cache
invalidation. Requires running infrastructure (Kafka or equivalent) that
doesn't exist yet.

## Phase 9 — ContextBench  (v0.1 shipped)

What's shipped: `benchmarks/datasets/acme_support_v1.yaml` — an 18-query,
30-document synthetic dataset with deliberate topically-similar
distractors (not trivially solvable by keyword match alone), Recall@k/
Precision@k/MRR/NDCG@k all implemented and correctness-tested (NDCG
checked against an independently hand-derived value), graded-relevance
support, and `contextflow evaluate --output/--compare-to` for tracking
regressions/improvements across changes. Full construction methodology
and honest limitations documented in `benchmarks/README.md` — most
importantly: **this dataset is synthetic, not derived from real user
queries**, because no production usage exists yet to draw from.

**A real external comparison, not just a self-authored one:**
`benchmarks/external/locomo/` evaluates ContextFlow against LoCoMo
(Maharana et al., ACL 2024) — a real, externally-authored benchmark that
Mem0/Zep/Letta also report against. Three configurations measured, same
1,444 questions: the zero-config hash default (8.5% Recall@5), spaCy
word vectors — `en_core_web_md` (15.8%) and `en_core_web_lg` (**27.3%**,
roughly 3.2x the baseline, achieved with zero API keys). **This does
not beat the benchmark** — a published comparable retrieval-only system
reports 93.9% on the same dataset, and 27.3% is not a close gap. Two
specific, identified reasons the rest of the gap wasn't closeable in
this session: no access to a trained sentence encoder (Hugging Face
isn't reachable from this sandbox, no OpenAI/Cohere API key or running
Ollama available), and no observation/fact-extraction preprocessing
step (what LoCoMo's own paper and the higher-scoring systems actually
do instead of retrieving over raw dialogue turns — typically needs an
LLM call, also unavailable here). Full numbers, per-category breakdown,
and the honest "no, we didn't beat it, and here's exactly why" in
`benchmarks/external/locomo/RESULTS.md`.

What's next: testing OpenAI/Cohere/Ollama (already-built providers,
still untested against this benchmark) and an observation-extraction
preprocessing step are the two concrete, identified, highest-leverage
next experiments — not vague aspirations. Also: faithfulness evaluation
(still a stub — needs an LLM-judge implementation), agent task success
(needs real agents running against this, not just retrieval), a public
leaderboard, and a benchmark built from a real (PII-scrubbed) support
corpus once one exists.

## Phase 10 — Adaptive retrieval ⬜

Learned ranking from usage signals (`context_used`/`context_ignored`/
`context_helpful`) instead of the static heuristic weights in
`retrieval/reranker.py`. This is a research direction, not a scoped
engineering task — it needs real usage data first.

## Phase 11 — Multi-agent context ⬜

Agent namespaces, shared vs. private memory, context handoff between
agents. Depends on Phase 5 (memory) landing first.

## Phase 12 — ContextFlow runtime ⬜

Treat the engine as a runtime rather than a library: gRPC alongside REST/
MCP, a Go SDK, formalized plugin loading for retrievers/connectors/
rerankers/storage backends discovered at runtime rather than imported.

## Phase 13 — Scale  (measured up to 5,000 objects, not beyond)

What's shipped: real performance/scale benchmarking
(`contextflow benchmark-scale`, `src/contextflow/evaluation/performance.py`)
measuring actual ingestion throughput and retrieval latency percentiles,
not estimates. Full results, methodology, and caveats in
`benchmarks/performance/results.md`. This work found and fixed a real
O(n²) ingestion bug in the persistent local backend (every write
rewrote the entire file to disk) — batch write APIs
(`upsert_batch`/`add_entities_batch`/`add_relationships_batch`) improved
measured throughput roughly 30-70x, verified with before/after numbers
on the same machine, not just claimed.

What's confirmed but NOT solved: both `InMemoryVectorStore` and
`FileVectorStore` do brute-force cosine similarity with no index
structure, so retrieval latency scales linearly with corpus size —
measured up to 5,000 objects, where p50 retrieval latency was already
~39ms. This will keep degrading well before "10M+ documents"; a real
vector index (the Qdrant/pgvector backends already sketched as
interfaces — see Phase 1) is the actual fix, untested here.

What's next: everything at real scale — distributed ingestion and
retrieval, sharding, multi-region, concurrent-load testing (this
benchmark is single-process/single-query only), and P50/P95/P99 targets
at 10M+ entity / 100M+ document scale. Out of scope for any single
contributor session — this is infrastructure engineering work for
whenever usage demands it, and the honest baseline above is exactly
what "usage demands it" should be measured against.

## Phase 14 — Open-source ecosystem ⬜

Split into `contextflow-core`, `-connectors`, `-sdks`, `-plugins`,
`-benchmarks`, `-examples` once each has enough independent contributors
to warrant its own release cadence. Community program: Hacktoberfest
participation, monthly releases, community calls.

## Phase 15 — Become a standard ⬜

A formal Context Object / Context Pack / Context Graph / MCP tool
specification that other runtimes could implement independently of this
codebase. This is an aspiration to work toward once the project has
real adoption — not something one team can declare into existence.

---

## How to contribute

Every unchecked box above is meant to become a `good first issue` or
`help wanted` GitHub issue. See [CONTRIBUTING.md](CONTRIBUTING.md) —
connectors, storage backends, and retrieval strategies are the
highest-leverage places to land a PR without touching core internals.
