"""Storage interfaces every backend implements.

These three interfaces (VectorStore, GraphStore, MetadataStore) are the
seams contributors add new backends against. See CONTRIBUTING.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from contextflow.core.context import ContextObject


class MetadataStore(ABC):
    """Stores and retrieves ContextObjects and their metadata.

    Built-in backends: SQLite (default, local-first), PostgreSQL.
    """

    @abstractmethod
    def get(self, id: str) -> ContextObject | None: ...

    @abstractmethod
    def put(self, obj: ContextObject) -> None: ...

    def put_batch(self, objects: list[ContextObject]) -> None:
        """Insert many objects at once. Default: loop over `put`.
        Override for backends where batching reduces per-call overhead
        (e.g. one transaction commit instead of one per row)."""
        for obj in objects:
            self.put(obj)

    @abstractmethod
    def delete(self, id: str) -> None: ...

    @abstractmethod
    def filter(self, **criteria: Any) -> list[ContextObject]: ...

    def all(self) -> list[ContextObject]:
        """Return every stored object. Used to rebuild in-process indices
        (e.g. the BM25 keyword index) on startup against a persistent
        backend. Optional — override where cheap to support."""
        raise NotImplementedError


class VectorStore(ABC):
    """Stores embeddings and performs similarity search.

    Built-in backends: local (in-process, default), Qdrant, pgvector.
    """

    @abstractmethod
    def upsert(self, id: str, embedding: list[float], payload: dict[str, Any]) -> None: ...

    def upsert_batch(self, items: list[tuple[str, list[float], dict[str, Any]]]) -> None:
        """Insert many vectors at once. Default: loop over `upsert`.
        File-backed implementations should override this to write to
        disk once at the end rather than once per item — see
        `storage/local_persistent.py: FileVectorStore` for why this
        matters (a real O(n^2) ingestion bug was found and fixed there
        by adding this override)."""
        for id, embedding, payload in items:
            self.upsert(id, embedding, payload)

    @abstractmethod
    def search(self, query_embedding: list[float], limit: int = 10) -> list[tuple[str, float]]:
        """Returns a list of (id, score) pairs, highest score first."""
        ...


class GraphStore(ABC):
    """Stores and traverses the entity/relationship graph.

    Built-in backends: none by default (v0.1); Neo4j lands in v0.2.
    """

    @abstractmethod
    def add_entity(self, entity_id: str, attributes: dict[str, Any]) -> None: ...

    @abstractmethod
    def add_relationship(
        self, source_id: str, target_id: str, rel_type: str, weight: float = 1.0
    ) -> None: ...

    def add_entities_batch(self, entities: list[tuple[str, dict[str, Any]]]) -> None:
        """Add many entities at once. Default: loop over `add_entity`.
        Override for backends where batching reduces per-call overhead."""
        for entity_id, attributes in entities:
            self.add_entity(entity_id, attributes)

    def add_relationships_batch(
        self, relationships: list[tuple[str, str, str, float]]
    ) -> None:
        """Add many relationships at once. Default: loop over
        `add_relationship`. Override for backends where batching reduces
        per-call overhead (see `FileGraphStore` — the same O(n^2)
        full-file-rewrite-per-call bug found in `FileVectorStore` existed
        here too)."""
        for source_id, target_id, rel_type, weight in relationships:
            self.add_relationship(source_id, target_id, rel_type, weight)

    @abstractmethod
    def traverse(self, entity_id: str, depth: int = 1) -> list[dict[str, Any]]: ...

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Return stored attributes for a single entity, or None. Optional
        — override where cheap to support."""
        raise NotImplementedError
