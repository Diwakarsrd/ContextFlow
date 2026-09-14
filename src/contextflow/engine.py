"""ContextEngine: the top-level facade most developers interact with.

    from contextflow import ContextEngine

    engine = ContextEngine()
    result = engine.retrieve("What are the latest decisions about the payments service?")
    pack = engine.context_pack(task="prepare customer renewal", entity="Acme")

By default this wires up local-first, dependency-free backends (see
storage/local.py) so it works with zero configuration. Pass explicit
stores/connectors to point it at Postgres, Qdrant, Neo4j, etc.
"""

from __future__ import annotations

from collections.abc import Callable

from contextflow.compiler.compiler import compile_context_pack
from contextflow.connectors.base import Connector
from contextflow.core.context import ContextObject
from contextflow.core.context_pack import ContextPack
from contextflow.core.metadata import GraphStore, MetadataStore, VectorStore
from contextflow.embeddings.base import EmbeddingProvider, LocalHashEmbeddingProvider
from contextflow.governance.permissions import filter_by_tenant, filter_visible
from contextflow.governance.policies import PolicyEngine
from contextflow.graph.builder import build_from_objects
from contextflow.graph.entity_extraction import extract_entities
from contextflow.ingestion.pipeline import process as run_ingestion_pipeline
from contextflow.observability.trace import ContextTrace, TraceRecorder, _Timer
from contextflow.retrieval.hybrid import HybridRetriever
from contextflow.retrieval.keyword import KeywordRetriever
from contextflow.retrieval.reranker import QualityWeightedReranker, Reranker
from contextflow.retrieval.router import RetrievalRouter
from contextflow.retrieval.semantic import SemanticRetriever
from contextflow.storage.local import InMemoryGraphStore, InMemoryMetadataStore, InMemoryVectorStore


def _default_embed_fn(text: str) -> list[float]:
    """Deprecated alias — use `contextflow.embeddings.base.LocalHashEmbeddingProvider`
    directly. Kept so any code holding a reference to the old private
    function keeps working."""
    return LocalHashEmbeddingProvider().embed(text)


def local_workspace(path: str = ".contextflow") -> ContextEngine:
    """Build a ContextEngine backed by the persistent, dependency-free
    local workspace (SQLite metadata + JSON vector/graph files) under
    `path`. This is what the CLI uses by default, so `contextflow ingest`
    and `contextflow search` share state across separate invocations.

    Embedding provider: uses `CONTEXTOS_EMBEDDING_PROVIDER` if set
    (`openai` | `ollama` | `cohere`), falling back to the dependency-free
    hash placeholder otherwise. Set the corresponding API key
    (`$OPENAI_API_KEY` / `$COHERE_API_KEY`) or have Ollama running
    locally. See `contextflow.embeddings` for direct configuration."""
    from contextflow.storage.local_persistent import FileGraphStore, FileVectorStore
    from contextflow.storage.sqlite import SQLiteMetadataStore

    return ContextEngine(
        metadata_store=SQLiteMetadataStore(f"{path}/metadata.db"),
        vector_store=FileVectorStore(f"{path}/vectors.json"),
        graph_store=FileGraphStore(f"{path}/graph.json"),
        embedding_provider=_provider_from_env(),
    )


def _provider_from_env() -> EmbeddingProvider | None:
    import os

    choice = os.environ.get("CONTEXTOS_EMBEDDING_PROVIDER", "").lower()
    if choice == "openai":
        from contextflow.embeddings.openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider()
    if choice == "ollama":
        from contextflow.embeddings.ollama import OllamaEmbeddingProvider

        return OllamaEmbeddingProvider()
    if choice == "cohere":
        from contextflow.embeddings.cohere import CohereEmbeddingProvider

        return CohereEmbeddingProvider()
    if choice == "spacy":
        from contextflow.embeddings.spacy_local import SpacyEmbeddingProvider

        return SpacyEmbeddingProvider()
    return None  # falls back to LocalHashEmbeddingProvider in ContextEngine


class ContextEngine:
    def __init__(
        self,
        metadata_store: MetadataStore | None = None,
        vector_store: VectorStore | None = None,
        graph_store: GraphStore | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        embed_fn: Callable[[str], list[float]] | None = None,
        reranker: Reranker | None = None,
        connectors: list[Connector] | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self.policy_engine = policy_engine
        self.traces = TraceRecorder()
        self.metadata_store = metadata_store or InMemoryMetadataStore()
        self.vector_store = vector_store or InMemoryVectorStore()
        self.graph_store = graph_store or InMemoryGraphStore()

        if embedding_provider is not None and embed_fn is not None:
            raise ValueError("Pass either embedding_provider or embed_fn, not both")
        self.embed_fn: Callable[[str], list[float]]
        if embedding_provider is not None:
            self.embed_fn = embedding_provider.embed
        elif embed_fn is not None:
            self.embed_fn = embed_fn
        else:
            # No provider configured — falls back to a dependency-free
            # placeholder with no real semantic understanding. See
            # LocalHashEmbeddingProvider's docstring. Pass
            # embedding_provider=OpenAIEmbeddingProvider(...) (or Ollama/
            # Cohere) for anything beyond a zero-config smoke test.
            self.embed_fn = LocalHashEmbeddingProvider().embed

        self.reranker = reranker or QualityWeightedReranker()
        self.connectors = connectors or []

        self._semantic = SemanticRetriever(self.vector_store, self.metadata_store, self.embed_fn)
        self._keyword = KeywordRetriever()
        self._hybrid = HybridRetriever(self._semantic, self._keyword)
        self._router = RetrievalRouter(self._hybrid)

        # If the metadata store is persistent (SQLite, Postgres, ...), the
        # keyword index is still in-process only — rebuild it from
        # whatever was already stored so `search` works immediately after
        # a fresh `ContextEngine()` against an existing workspace.
        try:
            for obj in self.metadata_store.all():
                self._keyword.index(obj)
        except NotImplementedError:
            pass

    # --- Ingestion -----------------------------------------------------

    def ingest(self, objects: list[ContextObject]) -> int:
        """Run objects through the ingestion pipeline, extract entities,
        index for retrieval, and update the context graph. Returns the
        number of chunks indexed.

        Indexing is batched (`index_batch`, `add_entities_batch`, etc.)
        rather than done one object at a time — see
        `core/metadata.py`'s batch method docstrings for why: a real
        performance benchmark found the naive per-object loop caused an
        O(n^2) ingestion cost against the file-backed local workspace."""
        processed = run_ingestion_pipeline(objects)
        for obj in processed:
            obj.entities = extract_entities(obj.content)
            self._keyword.index(obj)
        self._semantic.index_batch(processed)
        build_from_objects(processed, self.graph_store)
        return len(processed)

    def sync(self, connector: Connector) -> int:
        """Run a connector's full sync pipeline and ingest the results."""
        objects = list(connector.sync())
        return self.ingest(objects)

    def sync_all(self) -> int:
        return sum(self.sync(c) for c in self.connectors)

    # --- Retrieval -------------------------------------------------------

    def retrieve(
        self,
        query: str,
        limit: int = 10,
        principal: str | None = None,
        tenant_id: str | None = None,
    ) -> list[ContextObject]:
        results, _ = self._retrieve_impl(query, limit, principal, tenant_id, trace=None)
        return results

    def retrieve_with_trace(
        self,
        query: str,
        limit: int = 10,
        principal: str | None = None,
        tenant_id: str | None = None,
    ) -> tuple[list[ContextObject], ContextTrace]:
        """Same as `retrieve()`, but also returns a `ContextTrace`
        recording how many candidates went in/out of routing, permission/
        tenant filtering, and reranking, plus per-stage timing. The trace
        is also recorded in `self.traces` (a bounded ring buffer) so it
        can be looked up later via `get_trace(trace_id)`."""
        trace_in = ContextTrace(query=query)
        with _Timer() as total:
            results, trace_out = self._retrieve_impl(query, limit, principal, tenant_id, trace_in)
        assert (
            trace_out is not None
        )  # we passed a real trace in, _retrieve_impl returns it unchanged
        trace_out.total_duration_ms = total.elapsed_ms
        self.traces.record(trace_out)
        return results, trace_out

    def _retrieve_impl(
        self,
        query: str,
        limit: int,
        principal: str | None,
        tenant_id: str | None,
        trace: ContextTrace | None,
    ) -> tuple[list[ContextObject], ContextTrace | None]:
        with _Timer() as t:
            candidates = self._router.route(query, limit=limit * 3)
        if trace is not None:
            trace.add_stage(
                "route", count_in=0, count_out=len(candidates), duration_ms=t.elapsed_ms
            )

        if principal is not None:
            count_in = len(candidates)
            with _Timer() as t:
                candidates = filter_visible(candidates, principal, self.policy_engine)
            if trace is not None:
                trace.add_stage(
                    "permission_filter",
                    count_in,
                    len(candidates),
                    t.elapsed_ms,
                    principal=principal,
                )

        if tenant_id is not None:
            count_in = len(candidates)
            with _Timer() as t:
                candidates = filter_by_tenant(candidates, tenant_id)
            if trace is not None:
                trace.add_stage(
                    "tenant_filter", count_in, len(candidates), t.elapsed_ms, tenant_id=tenant_id
                )

        count_in = len(candidates)
        with _Timer() as t:
            ranked = self.reranker.rerank(query, candidates)
        if trace is not None:
            trace.add_stage("rerank", count_in, len(ranked), t.elapsed_ms)

        results = ranked[:limit]
        if trace is not None:
            trace.add_stage("limit", len(ranked), len(results), 0.0, limit=limit)

        return results, trace

    # --- Compilation -----------------------------------------------------

    def context_pack(
        self,
        task: str,
        entity: str | None = None,
        max_tokens: int = 3000,
        limit: int = 20,
        principal: str | None = None,
        tenant_id: str | None = None,
    ) -> ContextPack:
        objects = self.retrieve(task, limit=limit, principal=principal, tenant_id=tenant_id)
        return compile_context_pack(
            task=task, objects=objects, entity=entity, max_tokens=max_tokens
        )

    def context_pack_with_trace(
        self,
        task: str,
        entity: str | None = None,
        max_tokens: int = 3000,
        limit: int = 20,
        principal: str | None = None,
        tenant_id: str | None = None,
    ) -> tuple[ContextPack, ContextTrace]:
        """Same as `context_pack()`, but also returns the retrieval trace
        with a `compile` stage appended, and records the final pack's
        confidence/token usage on the trace."""
        objects, trace = self.retrieve_with_trace(
            task, limit=limit, principal=principal, tenant_id=tenant_id
        )
        with _Timer() as t:
            pack = compile_context_pack(
                task=task, objects=objects, entity=entity, max_tokens=max_tokens
            )
        trace.add_stage("compile", len(objects), 1, t.elapsed_ms, max_tokens=max_tokens)
        trace.total_duration_ms += t.elapsed_ms
        trace.final_confidence = pack.confidence
        trace.final_tokens = pack.tokens_used
        return pack, trace

    def get_trace(self, trace_id: str) -> ContextTrace | None:
        return self.traces.get(trace_id)

    # --- Knowledge graph -------------------------------------------------

    def get_entity(self, entity_id: str) -> dict | None:
        """Look up a single entity's stored attributes."""
        try:
            return self.graph_store.get_entity(entity_id)
        except NotImplementedError:
            return None

    def get_relationships(self, entity_id: str, depth: int = 1) -> list[dict]:
        """Return edges reachable from an entity within `depth` hops."""
        return self.graph_store.traverse(entity_id, depth=depth)

    def get_context_graph(self, entity_id: str, depth: int = 2) -> dict:
        """Return an entity plus its neighborhood, for agents that want
        the graph shape rather than a flat edge list."""
        edges = self.get_relationships(entity_id, depth=depth)
        neighbor_ids = sorted({e["target"] for e in edges} | {entity_id})
        return {
            "entity": entity_id,
            "attributes": self.get_entity(entity_id),
            "nodes": neighbor_ids,
            "edges": edges,
        }
