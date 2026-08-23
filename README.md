# ContextFlow

**Open-source context infrastructure for AI agents.**

Give your agents the right context at the right time — regardless of which
LLM, agent framework, or data stack you use.

[Quick Start](#quick-start) · [Docs](docs/getting_started.md) · [Architecture](ARCHITECTURE.md) · [Contributing](CONTRIBUTING.md)

---

## Why ContextFlow

**Before — naive RAG**

```
Agent → Vector DB → Top 5 chunks → LLM
```

**With ContextFlow**

```
Agent → Context Engine → Context Pack → LLM
              │
              ├── Semantic Search
              ├── Knowledge Graph
              ├── Memory
              ├── Permissions
              ├── Freshness
              ├── Conflict Detection
              └── Context Compiler
```

AI agents don't primarily need more tokens. They need the right context at
the right time.

## Quick Start

```bash
git clone https://github.com/yourorg/contextflow
cd contextflow
pip install -e .
contextflow demo
```

That's the whole thing — `contextflow demo` writes sample docs, ingests
them, runs a search, and builds a Context Pack, so you see the full
flow work with zero configuration before touching your own data. This
has been verified end-to-end from a clean clone into a fresh virtualenv
with no pre-existing dependencies — see `docs/getting_started.md` for
the exact commands.

For your own data:

```bash
contextflow init
contextflow ingest ./your-docs
contextflow search "your query"
contextflow context-pack "your question"
```

`ingest`, `search`, and `context-pack` are separate commands that
persist to `.contextflow/` on disk — no long-running process required.

For Postgres/Qdrant/Neo4j instead of the local-first defaults:

```bash
cp .env.example .env
docker compose up
```

```python
from contextflow import ContextEngine

engine = ContextEngine()

context = engine.retrieve(
    query="Why did our revenue drop last quarter?"
)

print(context)
```

> **Note on retrieval quality:** with no configuration, semantic search
> uses a dependency-free hashing placeholder with no real language
> understanding — fine for the quickstart above, not for real retrieval
> quality. Set `CONTEXTOS_EMBEDDING_PROVIDER=openai` (or `ollama` /
> `cohere`) plus the matching API key before ingesting real data:
>
> ```bash
> export CONTEXTOS_EMBEDDING_PROVIDER=openai
> export OPENAI_API_KEY=sk-...
> contextflow ingest ./docs
> ```
>
> See `src/contextflow/embeddings/` — Ollama runs fully locally if you'd
> rather not use a hosted API.

### Other local-first commands

```bash
contextflow trace "your query"    # see exactly what the retrieval pipeline did
contextflow mcp                   # expose an MCP server to Claude, Cursor, etc.
```

`context-pack` prints a readable panel:

```
╭──────────────────────────── Context Pack ────────────────────────────╮
│ Query: What decisions were made about payments?                      │
│                                                                        │
│ Documents                                                             │
│   • Stripe was selected as the payment processor. The migration…     │
│                                                                        │
│ Sources                                                                │
│   • filesystem                                                        │
│                                                                        │
│ Confidence: 100%                                                      │
╰────────────────────────────────────────────────────────────────────────╯
```

Swap in Postgres, Qdrant, and Neo4j later when you need to scale — see
[docs/deployment](docs/getting_started.md).

## The core abstraction: Context Pack

Instead of raw chunks:

```python
context = engine.context_pack(
    task="prepare customer renewal",
    entity="Acme",
)
```

```json
{
  "entity": "Acme",
  "facts": [],
  "people": [],
  "projects": [],
  "conversations": [],
  "documents": [],
  "decisions": [],
  "risks": [],
  "relationships": [],
  "sources": [],
  "conflicts": [],
  "confidence": 0.94
}
```

## MCP native

ContextFlow ships an MCP server out of the box, so any MCP-compatible agent
(Claude, Cursor, custom agents, ...) can call:

```
search_context()
get_entity()
get_context_pack()
get_relationships()
get_memory()
get_source()
explain_context()
```

```bash
contextflow mcp
```

## Modular by design

Don't want the knowledge graph? Don't install it. Every subsystem is an
interface with swappable backends:

| Layer     | Interface        | Built-in backends                  |
|-----------|-------------------|-------------------------------------|
| Vector    | `VectorStore`     | pgvector, Qdrant                    |
| Graph     | `GraphStore`      | Neo4j (optional)                    |
| Metadata  | `MetadataStore`   | SQLite, PostgreSQL                  |
| Connector | `Connector`       | GitHub, PostgreSQL, filesystem      |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full picture and
[ROADMAP.md](ROADMAP.md) for what's built vs. planned in v0.1.

## Repository layout

```
src/contextflow/
├── core/          # Context Object, Context Pack, Entity, Relationship
├── ingestion/      # Parsing, chunking, normalization, dedup
├── retrieval/      # Semantic, keyword, graph, hybrid, reranking
├── graph/          # Graph building, entity resolution, traversal
├── memory/         # Working / session / user / agent / org memory
├── compiler/       # Context compilation, compression, conflict detection
├── governance/      # Permissions, policies, PII detection, audit
├── evaluation/      # Retrieval + faithfulness benchmarks
├── connectors/      # GitHub, PostgreSQL, filesystem (+ Connector SDK)
├── mcp/             # MCP server and tools
├── api/             # REST API
└── cli/             # `contextflow` command-line tool
```

## Status

ContextFlow is v0.1 — early, opinionated, and built for contribution. What's
real today: persistent local storage, hybrid retrieval, real embedding
providers (OpenAI/Cohere/Ollama), API key auth shared by the REST API and
MCP-over-HTTP, RBAC + tenant isolation + pattern-based PII detection +
queryable audit logging, five-tier memory (session/user/agent/org
persisted, working ephemeral by design), real pipeline tracing/
observability (`contextflow trace`), a real TypeScript SDK (`sdk/typescript`)
tested against a live server, ContextBench v0.1 (a real, non-trivial
retrieval benchmark with Recall/Precision/MRR/NDCG and an honestly
documented synthetic-data methodology), real measured performance/scale
benchmarks that found and fixed a genuine O(n²) ingestion bug
(`contextflow benchmark-scale`), GitHub/PostgreSQL/filesystem
connectors proven end-to-end against real infrastructure, Slack and
Notion connectors proven against mocked APIs but not yet live workspaces,
a naive-but-functional knowledge graph, a runnable evaluation harness, and
the CLI/REST/MCP surfaces above.

**The honest gap:** benchmarked against LoCoMo (a real external benchmark
also used by Mem0/Zep/Letta — see `benchmarks/external/locomo/`), the
zero-config default scored 8.5% Recall@5. The best configuration tested
in this environment — `SpacyEmbeddingProvider` with `en_core_web_lg`,
fully local, zero API keys — reached **27.3%**, a real ~3.2x improvement.
**This does not beat the benchmark**: a comparable published system
reports 93.9% on the same dataset. The remaining gap has two specific,
identified causes (no trained sentence encoder or LLM-based fact
extraction was accessible in this sandbox), not a mystery — see
`benchmarks/external/locomo/RESULTS.md` for the full honest accounting.

See [ROADMAP.md](ROADMAP.md) for the full
phased plan — including what's shipped, what's partially built, and what's
still just direction — and [CONTRIBUTING.md](CONTRIBUTING.md) for how to
help.

## License

Apache 2.0 — see [LICENSE](LICENSE).
