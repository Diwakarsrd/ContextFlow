"""Semantic (embedding-based) retrieval."""

from __future__ import annotations

from collections.abc import Callable

from contextflow.core.context import ContextObject
from contextflow.core.metadata import MetadataStore, VectorStore


class SemanticRetriever:
    def __init__(
        self,
        vector_store: VectorStore,
        metadata_store: MetadataStore,
        embed_fn: Callable[[str], list[float]],
    ) -> None:
        self.vector_store = vector_store
        self.metadata_store = metadata_store
        self.embed_fn = embed_fn

    def index(self, obj: ContextObject) -> None:
        embedding = self.embed_fn(obj.content)
        self.vector_store.upsert(obj.id, embedding, payload={"source": obj.source})
        self.metadata_store.put(obj)

    def index_batch(self, objects: list[ContextObject]) -> None:
        """Batch version of `index` — computes all embeddings, then
        writes to the vector store and metadata store once each via
        their batch APIs, instead of once per object. See
        `core/metadata.py: VectorStore.upsert_batch` for why this
        matters for file-backed stores."""
        items = [
            (obj.id, self.embed_fn(obj.content), {"source": obj.source}) for obj in objects
        ]
        self.vector_store.upsert_batch(items)
        self.metadata_store.put_batch(objects)

    def retrieve(self, query: str, limit: int = 10) -> list[ContextObject]:
        query_embedding = self.embed_fn(query)
        hits = self.vector_store.search(query_embedding, limit=limit)
        results = []
        for obj_id, score in hits:
            obj = self.metadata_store.get(obj_id)
            if obj is not None:
                obj.metadata["_semantic_score"] = score
                results.append(obj)
        return results
