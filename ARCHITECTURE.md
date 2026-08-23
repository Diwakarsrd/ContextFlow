# Architecture

## Overview

```
                    ┌─────────────────────┐
                    │    AI AGENT / LLM    │
                    └──────────┬───────────┘
                               │
                         MCP / SDK / API
                               │
                    ┌──────────▼───────────┐
                    │    CONTEXT ENGINE     │
                    │                       │
                    │ Context Retrieval     │
                    │ Context Graph         │
                    │ Context Memory        │
                    │ Context Compiler      │
                    │ Context Governance    │
                    │ Context Evaluation    │
                    └──────────┬───────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
        PostgreSQL          Qdrant             Neo4j
        Metadata            Vectors             Graph
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                     CONNECTOR FRAMEWORK
                               │
        ┌─────────┬────────┬───┼────┬─────────┬────────┐
        │         │        │        │         │        │
      GitHub    Slack    Jira     Docs    Postgres    APIs
```

## Design principles

1. **Modular.** Every subsystem (vector store, graph store, connector,
   reranker) is an interface. Nothing is hard-coded to one vendor.
2. **MCP-native.** The engine is useful to any MCP-compatible agent, not
   just consumers of the Python/TypeScript SDK.
3. **Local-first.** `contextflow init` should work with zero cloud
   dependencies. Production backends (Postgres, Qdrant, Neo4j) are opt-in.
4. **Permission-aware retrieval, not post-hoc filtering.** Policy is applied
   *before* content reaches a ranking or compilation step, not after.
5. **Context Objects are the standard.** Any connector, any retriever,
   any compiler speaks the same `ContextObject` schema.

## Data flow

```
Query
 ↓
Intent detection
 ↓
Query expansion
 ↓
Parallel retrieval
 ├── Vector
 ├── BM25
 ├── Graph
 └── Metadata
 ↓
Merge
 ↓
Rerank
 ↓
Policy / permission filter
 ↓
Deduplicate
 ↓
Compress
 ↓
Context Pack
 ↓
Agent / LLM
```

## Core objects

### ContextObject

The atomic unit produced by every connector.

```python
ContextObject(
    id="...",
    type="document",
    content="...",
    source="github",
    entities=[],
    relationships=[],
    metadata={},
    permissions=[],
    freshness=0.97,
    confidence=0.91,
    trust=0.95,
)
```

### ContextPack

The compiled, agent-ready output of a retrieval + compilation pass. See
`src/contextflow/core/context_pack.py`.

## Storage interfaces

```python
class VectorStore:
    def search(self, query, limit): ...

class GraphStore:
    def traverse(self, entity): ...

class MetadataStore:
    def get(self, id): ...
```

Backend implementations live under a `storage/` adapter per interface (see
`ROADMAP.md` for which backends ship in which release).

## Connector interface

```python
class Connector:
    def authenticate(self): ...
    def discover(self): ...
    def fetch(self): ...
    def normalize(self): ...
    def emit(self): ...
```

New connectors only need to implement this interface — see
`CONTRIBUTING.md` for the connector contribution guide.

## Layers, in one picture

```
                         CONTEXTOS
                             │
       ┌─────────────────────┼─────────────────────┐
       │                     │                     │
   INGESTION             UNDERSTANDING          MEMORY
       │                     │                     │
  connectors             Entity Resolution     User Memory
       │                 Knowledge Graph        Agent Memory
       │                 Ontology               Org Memory
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                             │
                       RETRIEVAL ENGINE
                             │
             ┌───────────────┼───────────────┐
             │               │               │
          Semantic         Graph           Keyword
             │               │               │
             └───────────────┼───────────────┘
                             │
                         RERANKER
                             │
                       GOVERNANCE
                             │
                     CONTEXT COMPILER
                             │
                       CONTEXT PACK
                             │
                 ┌───────────┴───────────┐
                 │                       │
                MCP                     SDK
                 │                       │
                 └───────────┬───────────┘
                             │
                        AI AGENTS
```
