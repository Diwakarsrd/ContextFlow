# ContextFlow

**An open-source context engine for AI agents.** It decides what your agent
sees: the right pieces of your documents, filtered by who's asking,
compiled into a token-budgeted Context Pack, and served over MCP to Claude,
Cursor or your own agents. Runs fully locally.

<p>
  <a href="https://github.com/Diwakarsrd/ContextFlow/actions/workflows/ci.yml"><img src="https://github.com/Diwakarsrd/ContextFlow/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/contextflow-engine/"><img src="https://img.shields.io/pypi/v/contextflow-engine?color=blue" alt="PyPI"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/MCP-native-orange" alt="MCP native">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-lightgrey" alt="Apache 2.0"></a>
</p>

[Quick start](#quick-start) · [Use with Claude/Cursor](#use-it-from-claude-cursor-or-any-mcp-agent) · [Benchmarks](#benchmarks) · [Architecture](ARCHITECTURE.md) · [Contributing](CONTRIBUTING.md)

## Why

Naive RAG hands the model the top 5 chunks from a vector database. Real
agents need more than that: evidence from *several* documents, only what
the user is allowed to see, the newest version when sources disagree, and
all of it inside a token budget.

```
Agent ──► ContextFlow ──► Context Pack ──► LLM
             │
             ├── hybrid retrieval (semantic + BM25, rank fusion)
             ├── permissions & tenant isolation
             ├── freshness / confidence / trust reranking
             ├── conflict detection
             ├── knowledge graph & agent memory
             └── token-budgeted compilation
```

## Benchmarks

On **MultiHop-RAG** (COLING 2024), 609 news articles, 2,255 questions
whose evidence spans 2–4 different articles, same chunks and embeddings
in every row:

| | Hits@4 | Hits@10 | MRR@10 |
|---|---|---|---|
| Vector-only RAG (`nomic-embed-text`, local) | 0.577 | 0.768 | 0.449 |
| **ContextFlow** (same embeddings) | **0.675** | **0.830** | **0.540** |
| Paper's best: voyage-02 + bge-reranker-large | 0.663 | 0.747 | 0.586 |

Within the same 2,048-token budget, a Context Pack contains *all* the
evidence a question needs 1.5x as often as naive top-k (23.1% vs 15.4%).

Everything runs on a laptop with a free local model, no API key.
Caveats and methodology (including a MAP@10 figure we don't claim) are
in [benchmarks/external/multihop_rag/RESULTS.md](benchmarks/external/multihop_rag/RESULTS.md).
Conversational-memory results (LoCoMo) are in
[benchmarks/external/locomo/RESULTS.md](benchmarks/external/locomo/RESULTS.md).

## Quick start

```bash
pip install contextflow-engine
contextflow demo
```

`demo` writes sample docs, ingests them, searches, and builds a Context
Pack, with zero configuration.

On your own files:

```bash
contextflow init
contextflow ingest ./docs
contextflow search "how long do refunds take"
contextflow context-pack "how long do refunds take"
contextflow trace "how long do refunds take"   # see what each pipeline stage did
```

Everything persists to `./.contextflow/` (use `--path` for another
workspace); no server process required.

**For real retrieval quality, use real embeddings.** The zero-config
default is a hashing placeholder with no semantic understanding. Local
and free:

```bash
ollama pull nomic-embed-text
export CONTEXTOS_EMBEDDING_PROVIDER=ollama   # or openai / cohere
contextflow ingest ./docs
```

## Use it from Claude, Cursor or any MCP agent

```bash
contextflow ingest ./docs --path /abs/path/to/.contextflow
```

Claude Desktop (`claude_desktop_config.json`) or any MCP client:

```json
{
  "mcpServers": {
    "contextflow": {
      "command": "contextflow",
      "args": ["mcp", "--path", "/abs/path/to/.contextflow"],
      "env": { "CONTEXTOS_EMBEDDING_PROVIDER": "ollama" }
    }
  }
}
```

Tools exposed: `search_context`, `get_context_pack`, `get_entity`,
`get_relationships`, `get_context_graph`, `get_memory`, `remember`,
`get_source`, `explain_context`, `trace_query`. Use `--transport http`
for remote agents (Bearer-token auth via `contextflow auth create-key`).

A REST API serves the same workspace: `contextflow serve --path ...`
(TypeScript client in [`sdk/typescript`](sdk/typescript)).

## Python

```python
from contextflow import ContextEngine, ContextObject
from contextflow.embeddings.ollama import OllamaEmbeddingProvider

engine = ContextEngine(embedding_provider=OllamaEmbeddingProvider())
engine.ingest([
    ContextObject(
        content="Finance decided to switch payment processors to Stripe in March.",
        source="notion",
        permissions=["alice"],  # only alice may see this
    ),
    ContextObject(
        content="The payments migration to Stripe-native subscriptions ships in Q4.",
        source="slack",
    ),
])

pack = engine.context_pack("What did we decide about payments?", principal="bob")
# bob's pack contains only the Slack message; alice's would include both.
```

## What's in the box

| Area | Status |
|---|---|
| Retrieval | Hybrid semantic + BM25 with reciprocal rank fusion, reranking, tracing |
| Embeddings | Ollama, OpenAI, Cohere, spaCy, or zero-config hash placeholder |
| Governance | Per-object permissions, RBAC roles, tenant isolation, PII redaction, audit log |
| Compilation | Token-budgeted Context Packs with dedup and conflict detection |
| Memory | Session / user / agent / org memory, cross-agent handoff |
| Connectors | Filesystem, GitHub, PostgreSQL (as a source), Slack, Notion, GitLab, Jira, Discord |
| Interfaces | CLI, MCP (stdio + HTTP), REST API, Python, TypeScript SDK |
| Storage | Local: SQLite metadata + local vector/graph files (numpy-vectorized search) |

**Not built yet** (see [ROADMAP.md](ROADMAP.md)): Qdrant / pgvector / Neo4j
storage backends, a learned reranker, and LLM-graded answer evaluation.
The Slack, Notion, GitLab, Jira and Discord connectors are tested
against mocked APIs, not live workspaces.

## Status

v0.2, alpha. The API may change. Issues and PRs welcome: see
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0, see [LICENSE](LICENSE). Benchmark datasets are downloaded at
run time under their own licenses (MultiHop-RAG: ODC-BY; LoCoMo: CC
BY-NC 4.0) and are not redistributed.
