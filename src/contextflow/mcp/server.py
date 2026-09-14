"""ContextFlow MCP server.

Exposes the engine to any MCP-compatible agent (Claude, Cursor, custom
agents, ...) via the tools listed in README.md's "MCP native" section.

Run with:

    contextflow mcp

or directly:

    python -m contextflow.mcp.server
"""

from __future__ import annotations

from contextflow.engine import ContextEngine
from contextflow.memory.store import MemoryStore

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError as exc:  # pragma: no cover
    raise ImportError("The MCP server requires the `mcp` package (pip install mcp)") from exc


def build_server(
    engine: ContextEngine | None = None, memory_store: MemoryStore | None = None
) -> FastMCP:
    engine = engine or ContextEngine()
    memory_store = memory_store or MemoryStore()
    server = FastMCP("contextflow")

    @server.tool()
    def search_context(query: str, limit: int = 10) -> list[dict]:
        """Search all connected sources and return matching context objects."""
        return [obj.model_dump(mode="json") for obj in engine.retrieve(query, limit=limit)]

    @server.tool()
    def get_context_pack(task: str, entity: str | None = None, max_tokens: int = 3000) -> dict:
        """Build a compiled, agent-ready Context Pack for a task (optionally
        scoped to an entity like a customer or project)."""
        pack = engine.context_pack(task=task, entity=entity, max_tokens=max_tokens)
        return pack.model_dump(mode="json")

    @server.tool()
    def get_entity(entity_id: str) -> dict:
        """Look up a single entity by ID from the context graph."""
        result = engine.get_entity(entity_id)
        return result or {"error": "not found"}

    @server.tool()
    def get_relationships(entity_id: str, depth: int = 1) -> list[dict]:
        """Traverse the context graph outward from an entity."""
        return engine.get_relationships(entity_id, depth=depth)

    @server.tool()
    def get_context_graph(entity_id: str, depth: int = 2) -> dict:
        """Return an entity plus its full graph neighborhood."""
        return engine.get_context_graph(entity_id, depth=depth)

    @server.tool()
    def get_memory(
        scope: str, scope_id: str, query: str | None = None, limit: int = 10
    ) -> list[dict]:
        """Recall facts from memory. `scope` is one of session/user/agent/org;
        `scope_id` identifies which session/user/agent/org. Ranked by
        keyword relevance if `query` is given, else most-recent-first."""
        entries = memory_store.recall(scope, scope_id, query, limit)
        return [
            {"id": e.id, "content": e.content, "metadata": e.metadata, "created_at": e.created_at}
            for e in entries
        ]

    @server.tool()
    def remember(scope: str, scope_id: str, fact: str, metadata: dict | None = None) -> dict:
        """Store a fact in memory, scoped to session/user/agent/org."""
        entry_id = memory_store.remember(scope, scope_id, fact, metadata)
        return {"id": entry_id}

    @server.tool()
    def get_source(source_name: str) -> dict:
        """Return metadata about a connected source (sync status, config)."""
        raise NotImplementedError("get_source requires Source persistence — see ROADMAP.md")

    @server.tool()
    def explain_context(context_object_id: str) -> dict:
        """Explain why a given context object was retrieved/ranked: the
        raw retrieval score (semantic or keyword, whichever produced it),
        the freshness/confidence/trust signals, the reranker's weights,
        and the resulting final score — the actual formula
        QualityWeightedReranker used, not just the raw fields."""
        obj = engine.metadata_store.get(context_object_id)
        if obj is None:
            return {"error": "not found"}

        base_score = (
            obj.metadata.get("_semantic_score") or obj.metadata.get("_keyword_score") or 0.0
        )
        reranker = engine.reranker
        freshness_weight = getattr(reranker, "freshness_weight", None)
        confidence_weight = getattr(reranker, "confidence_weight", None)
        trust_weight = getattr(reranker, "trust_weight", None)
        weights = {
            "freshness_weight": freshness_weight,
            "confidence_weight": confidence_weight,
            "trust_weight": trust_weight,
        }
        final_score = base_score
        if (
            freshness_weight is not None
            and confidence_weight is not None
            and trust_weight is not None
        ):
            final_score = (
                base_score
                + freshness_weight * obj.freshness
                + confidence_weight * obj.confidence
                + trust_weight * obj.trust
            )

        return {
            "id": obj.id,
            "source": obj.source,
            "base_retrieval_score": base_score,
            "signals": {
                "freshness": obj.freshness,
                "confidence": obj.confidence,
                "trust": obj.trust,
            },
            "reranker_weights": weights,
            "final_score": final_score,
        }

    @server.tool()
    def trace_query(query: str, limit: int = 10) -> dict:
        """Run a search with full pipeline tracing: how many candidates
        went in/out of routing, filtering, and reranking, plus timing per
        stage. Use this to debug why a query returned what it did."""
        _, trace = engine.retrieve_with_trace(query, limit=limit)
        return trace.to_dict()

    return server


def main(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8765) -> None:
    server = build_server()
    if transport == "stdio":
        server.run()
    elif transport == "http":
        from contextflow.auth.api_keys import APIKeyStore
        from contextflow.mcp.http_transport import run_http

        run_http(server, APIKeyStore.from_env_and_file(), host=host, port=port)
    else:
        raise ValueError(f"Unknown transport: {transport!r} (expected 'stdio' or 'http')")


if __name__ == "__main__":
    main()
