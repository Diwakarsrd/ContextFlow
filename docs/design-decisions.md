# Design Decisions

## Why retrieval is separated from compression

ContextFlow treats retrieval and compression as strictly independent stages because they have completely different scaling properties and failure modes. 
Retrieval (Elasticsearch/Qdrant) is IO-bound and focuses purely on high-recall semantic distance. Compression, however, is CPU-bound - it requires parsing AST structures, applying mathematical time-decay to confidence scores, and respecting token boundaries. Fusing them into a single step usually leads to "dumb truncation" (e.g., cutting off a chunk halfway through a sentence).

## Why we don't use an LLM for every retrieval operation

While LLMs are excellent at routing, injecting a full LLM call into the inner retrieval loop introduces non-deterministic behavior and 500ms+ latency penalties per hop. For enterprise RBAC and strict governance environments, using predefined rule networks (like our StaticQueryExpander) ensures that permissions and aliases are resolved in sub-millisecond time without hallucination risk. LLMs are reserved strictly for the final synthesis layer.

## Why the cache uses local SQLite by default

Our primary goal with ContextFlow is developer experience (DX). Requiring developers to spin up a Dockerized Redis or Postgres container just to test an agent's memory pipeline creates massive friction. SQLite provides ACID-compliant, thread-safe local persistence with zero external dependencies, allowing developers to run contextflow demo anywhere. We provide adapters to switch to PostgreSQL when moving to production.

## Why 'Context Packs' instead of direct injection

We compile data into immutable JSON 'Context Packs'. If an agent makes a mistake, developers need to point to exactly what context the agent was holding at timestamp T. If agents query databases dynamically, the state is lost. Context Packs act as a reproducible snapshot of the exact memory, graph entities, and RBAC rules the agent had access to at the moment of decision.
