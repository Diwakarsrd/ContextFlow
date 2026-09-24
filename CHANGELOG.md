# Changelog

All notable changes to this project are documented in this file.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-09-24

Upgrade note: re-ingest existing workspaces. Chunk ids, chunk
boundaries, BM25 tokenization and (for `nomic-embed-text`/`mxbai`)
Ollama embeddings all changed.

### Fixed
- **Long documents kept only their last chunk.** Chunks shared their
  parent's id and overwrote each other; they now get `<id>#chunk-<n>`.
- **`contextflow mcp` crashed on start**: the code targeted the MCP SDK 2.x
  API while `mcp==1.0.0` was pinned. Now requires `mcp>=2.0,<3`.
- `contextflow mcp` and `contextflow serve` started an empty engine
  instead of the ingested workspace; both now take `--path`.
- Retrieval scores leaked between queries through the stored objects.
- The reranker ignored hybrid rank fusion and compared raw cosine vs.
  BM25 scores.
- `contextflow evaluate` ignored `CONTEXTOS_EMBEDDING_PROVIDER`.
- Discord/GitLab/Jira connectors imported the undeclared `requests`.

### Changed
- Sentence-aware chunking (no more mid-word cuts).
- BM25: Unicode tokens, stopwords, possessive/plural folding.
- Vector search numpy-vectorized (3.3 s -> 3.5 ms at 7k vectors).
- Embedding providers are batched on ingest; Ollama uses `/api/embed`
  and model-specific query/document prefixes (`embed_query`).
- Dependency bumps (pydantic, fastapi, qdrant-client, pytest, actions v7,
  TypeScript 7).

### Added
- MultiHop-RAG benchmark (`benchmarks/external/multihop_rag/`).
- `--provider ollama` for the LoCoMo benchmark.

## [0.1.0]

### Added
- Initial project scaffold: core objects, ingestion, retrieval, MCP
  server, REST API, CLI, Python SDK, Docker Compose, evaluation harness.
