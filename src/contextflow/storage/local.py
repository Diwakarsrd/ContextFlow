"""Zero-dependency local backends, used by `contextflow init`.

These make `pip install contextflow && python -c "..."` work with no
Postgres, Qdrant, or Neo4j required. Swap in `storage/postgres.py`,
`storage/qdrant.py` (community-contributed, see CONTRIBUTING.md) for
production use.
"""

from __future__ import annotations

import math
from typing import Any

from contextflow.core.context import ContextObject
from contextflow.core.metadata import GraphStore, MetadataStore, VectorStore


class InMemoryMetadataStore(MetadataStore):
    def __init__(self) -> None:
        self._objects: dict[str, ContextObject] = {}

    def get(self, id: str) -> ContextObject | None:
        return self._objects.get(id)

    def put(self, obj: ContextObject) -> None:
        self._objects[obj.id] = obj

    def delete(self, id: str) -> None:
        self._objects.pop(id, None)

    def filter(self, **criteria: Any) -> list[ContextObject]:
        results = list(self._objects.values())
        for key, value in criteria.items():
            results = [o for o in results if getattr(o, key, None) == value]
        return results

    def all(self) -> list[ContextObject]:
        return list(self._objects.values())


class InMemoryVectorStore(VectorStore):
    """Brute-force cosine similarity. Fine up to a few thousand vectors —
    swap in Qdrant or pgvector well before that point."""

    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}
        self._payloads: dict[str, dict[str, Any]] = {}

    def upsert(self, id: str, embedding: list[float], payload: dict[str, Any]) -> None:
        self._vectors[id] = embedding
        self._payloads[id] = payload

    def search(self, query_embedding: list[float], limit: int = 10) -> list[tuple[str, float]]:
        scored = [
            (id, cosine_similarity(query_embedding, vec)) for id, vec in self._vectors.items()
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:limit]


class InMemoryGraphStore(GraphStore):
    def __init__(self) -> None:
        self._entities: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []

    def add_entity(self, entity_id: str, attributes: dict[str, Any]) -> None:
        existing = self._entities.get(entity_id, {})
        existing.update(attributes)
        self._entities[entity_id] = existing

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        return self._entities.get(entity_id)

    def add_relationship(
        self, source_id: str, target_id: str, rel_type: str, weight: float = 1.0
    ) -> None:
        self._edges.append(
            {"source": source_id, "target": target_id, "type": rel_type, "weight": weight}
        )

    def traverse(self, entity_id: str, depth: int = 1) -> list[dict[str, Any]]:
        frontier = {entity_id}
        visited: list[dict[str, Any]] = []
        for _ in range(depth):
            next_frontier: set[str] = set()
            for edge in self._edges:
                if edge["source"] in frontier:
                    visited.append(edge)
                    next_frontier.add(edge["target"])
            frontier = next_frontier
        return visited


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
