# Contributing to ContextFlow

Thanks for considering a contribution. ContextFlow is deliberately architected
so most contributions don't require touching the core engine.

## Easiest ways to contribute

### 1. Build a connector

Implement the `Connector` interface (`src/contextflow/connectors/base.py`):

```python
class Connector:
    def authenticate(self): ...
    def discover(self): ...
    def fetch(self): ...
    def normalize(self): ...
    def emit(self): ...
```

Drop it in `src/contextflow/connectors/<your_service>/`, add tests, add a doc
page under `docs/integrations/`, and open a PR. Wanted connectors are
tracked with the `connector` label — Slack, Discord, Linear, Notion,
Confluence, GitLab, Google Drive, OneDrive, S3, BigQuery, Snowflake,
Databricks are all open.

### 2. Add a storage backend

Implement one of `VectorStore`, `GraphStore`, or `MetadataStore`
(`src/contextflow/core/`). Wanted backends: pgvector, Milvus, Weaviate,
Pinecone (vector); Memgraph (graph); MongoDB, SQLite (metadata).

### 3. Improve retrieval

Add a new strategy under `src/contextflow/retrieval/` (semantic, keyword,
graph, hybrid, temporal) or a new reranker. Submit benchmark numbers from
`contextflow eval` alongside your PR — see `benchmarks/`.

### 4. Add a framework integration

Adapters for LangGraph, LangChain, LlamaIndex, CrewAI, AutoGen, or OpenAI
Agents live under `examples/` and `sdk/python/contextflow_sdk/integrations/`.

### 5. Documentation and examples

`examples/` should be real, runnable projects (`docker compose up` and
it works), not toy snippets. `docs/` improvements are always welcome.

## Labels to look for

`good first issue` · `help wanted` · `connector` · `retrieval` · `graph` ·
`memory` · `mcp` · `evaluation` · `performance` · `documentation` ·
`examples` · `security` · `sdk` · `integration`

## Development setup

```bash
git clone https://github.com/yourorg/contextflow
cd contextflow
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
docker compose up -d   # Postgres / Qdrant / Neo4j for integration tests
pytest
```

### Running the live PostgreSQL tests

`tests/test_postgres_live.py` connects to a real database and is skipped
automatically if none is reachable — most contributors won't need to
touch this. To run it locally:

```bash
pip install -e ".[dev,postgres]"
docker compose up -d postgres
export CONTEXTOS_TEST_POSTGRES_DSN=postgresql://contextflow:contextflow@localhost:5432/contextflow
pytest tests/test_postgres_live.py -v
```

CI runs these against a real Postgres service container on every PR —
see `.github/workflows/ci.yml`.

## Pull request checklist

- [ ] Tests added/updated (`pytest`)
- [ ] Lint passes (`ruff check .`)
- [ ] Types pass (`mypy src`)
- [ ] Docs updated if you touched a public interface
- [ ] If retrieval-related: benchmark numbers included in the PR description

## Code of conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
