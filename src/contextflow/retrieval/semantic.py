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
        embed_batch_fn: Callable[[list[str]], list[list[float]]] | None = None,
        embed_query_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.metadata_store = metadata_store
        self.embed_fn = embed_fn
        self.embed_batch_fn = embed_batch_fn
        self.embed_query_fn = embed_query_fn or embed_fn

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
        texts = [obj.content for obj in objects]
        if self.embed_batch_fn is not None:
            # One provider round trip per batch instead of per object —
            # the difference between seconds and minutes for API-backed
            # providers on a large ingest.
            embeddings = self.embed_batch_fn(texts)
        else:
            embeddings = [self.embed_fn(text) for text in texts]
        items = [
            (obj.id, emb, {"source": obj.source})
            for obj, emb in zip(objects, embeddings, strict=True)
        ]
        self.vector_store.upsert_batch(items)
        self.metadata_store.put_batch(objects)

    def retrieve(self, query: str, limit: int = 10) -> list[ContextObject]:
        query_embedding = self.embed_query_fn(query)
        hits = self.vector_store.search(query_embedding, limit=limit)
        results = []
        for obj_id, score in hits:
            obj = self.metadata_store.get(obj_id)
            if obj is not None:
                # Score a per-query copy: writing into the stored object
                # would leak this query's score into later queries.
                metadata = {**obj.metadata, "_semantic_score": score}
                results.append(obj.model_copy(update={"metadata": metadata}))
        return results
