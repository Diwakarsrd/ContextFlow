# Getting Started

## Install

```bash
git clone https://github.com/yourorg/contextflow
cd contextflow
pip install -e .
```

This has been verified to work from a genuinely clean clone into a
fresh virtualenv (no dependencies pre-installed, no editable-install
tricks) — see the note at the bottom of this page.

## See it work: `contextflow demo`

```bash
contextflow demo
```

Writes sample docs to `./contextflow-demo/docs`, ingests them, runs a
search, and builds a Context Pack — the whole flow, zero configuration,
one command. Delete `./contextflow-demo/` when you're done looking at it.

## Local-first quickstart, with your own data

```bash
contextflow init
contextflow ingest ./docs
contextflow search "payments architecture"
contextflow context-pack "What decisions were made about payments?"
```

`ingest`, `search`, and `context-pack` are separate CLI invocations. They
persist to `.contextflow/` (SQLite metadata + JSON vector/graph files), so
state carries across processes — you don't need one long-running process.
Use `--path <dir>` on any of these (plus `trace`) to point at a workspace
other than `./.contextflow` — this is how `contextflow demo` keeps its sample
workspace separate from your real one.

## Python

```python
from contextflow import ContextEngine

engine = ContextEngine()
engine.ingest([...])            # list[ContextObject], or use a connector
results = engine.retrieve("your question")
pack = engine.context_pack(task="prepare customer renewal", entity="Acme")
```

## Using a connector

```python
from contextflow import ContextEngine
from contextflow.connectors.filesystem.connector import FilesystemConnector

engine = ContextEngine()
engine.sync(FilesystemConnector(config={"path": "./docs"}))
```

## Running the REST API

```bash
contextflow serve
curl -X POST localhost:8000/v1/search -d '{"query": "refund policy"}'
```

With no API keys configured, this runs in **open mode** (full access, no
credential) — fine for local dev, not for anything reachable beyond
localhost. Generate a key and use it before exposing the API further:

```bash
contextflow auth create-key alice
# Created key for 'alice': sk_...

curl -X POST localhost:8000/v1/search \
  -H "Authorization: Bearer sk_..." \
  -d '{"query": "refund policy"}'
```

The principal for permission-aware retrieval always comes from the
verified key, never from the request body.

## Running the MCP server

```bash
contextflow mcp
```

Point any MCP-compatible agent (Claude, Cursor, custom agents) at it and
call `search_context`, `get_context_pack`, etc. — see the root README's
"MCP native" section for the full tool list. Over the default stdio
transport, no additional auth applies — the trust boundary is "who can
run this process," the same as any local CLI tool.

For remote agents, run it over HTTP instead — this enforces the same
Bearer-token auth as the REST API once keys are configured:

```bash
contextflow mcp --transport http --port 8765
```

## Scaling beyond local-first

```bash
docker compose up -d postgres qdrant
```

```python
from contextflow import ContextEngine
from contextflow.storage.postgres import PostgresMetadataStore   # community-contributed
from contextflow.storage.qdrant import QdrantVectorStore          # community-contributed

engine = ContextEngine(
    metadata_store=PostgresMetadataStore(dsn="postgresql://..."),
    vector_store=QdrantVectorStore(url="http://localhost:6333"),
)
```

(Postgres/Qdrant backend implementations are tracked in `ROADMAP.md` —
see `CONTRIBUTING.md` if you'd like to build one.)

## Next steps

- [Performance/scale results](../benchmarks/performance/results.md) — real measured numbers, not estimates
- [Context tracing](concepts/tracing.md) — debug why a query returned what it did
- [Embedding providers](concepts/embeddings.md) — configure real semantic search
- [Architecture](../ARCHITECTURE.md)
- [Roadmap](../ROADMAP.md)
- [Contributing](../CONTRIBUTING.md)

## Clean-room verification

The exact sequence below has been run end-to-end in a genuinely fresh
environment — a real `git clone` of a real commit into a scratch
directory, a brand-new virtualenv with nothing pre-installed, no dev
extras:

```bash
git clone <repo> repo && cd repo
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/contextflow demo
.venv/bin/contextflow init
.venv/bin/contextflow ingest mydocs
.venv/bin/contextflow search "..."
.venv/bin/contextflow context-pack "..."
.venv/bin/pip install pytest
.venv/bin/python -m pytest -q
```

Result: install succeeded with no workarounds, every command produced
correct output on the first try, and `pytest` reported 123 passed (one
test gracefully skips with a clear message if the `postgres` extra
isn't installed — that's by design, not a failure — and passes too once
it is, against a live database). This is what prompted adding the
`demo` command and the `--path` flag in the first place: neither existed
until this exact verification exposed the gap.
