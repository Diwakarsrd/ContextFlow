"""Zero-dependency local backends, used by `contextflow init`.

These make `pip install contextflow && python -c "..."` work with no
Postgres, Qdrant, or Neo4j required. Swap in `storage/postgres.py`,
`storage/qdrant.py` (community-contributed, see CONTRIBUTING.md) for
production use.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

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


class CosineIndex:
    """Brute-force cosine top-k over an `{id: vector}` dict, vectorized
    with numpy: the vectors are normalized into one matrix (rebuilt
    lazily after `invalidate()`), so a search is a single matrix-vector
    product instead of a Python loop over every vector (measured at 7,259
    768-d vectors: 3.3 s -> 3.5 ms per search). Falls back to the pure-Python loop if vectors
    have mixed dimensions."""

    def __init__(self) -> None:
        self._ids: list[str] = []
        self._matrix: np.ndarray | None = None
        self._dirty = True

    def invalidate(self) -> None:
        self._dirty = True

    def search(
        self, vectors: dict[str, list[float]], query: list[float], limit: int
    ) -> list[tuple[str, float]]:
        if not vectors or limit <= 0:
            return []
        if self._dirty:
            self._ids = list(vectors)
            try:
                matrix = np.asarray([vectors[i] for i in self._ids], dtype=np.float32)
            except ValueError:  # ragged: vectors of different dimensions
                matrix = None
            if matrix is not None and matrix.ndim == 2:
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                self._matrix = np.divide(
                    matrix, norms, out=np.zeros_like(matrix), where=norms > 0
                )
            else:
                self._matrix = None
            self._dirty = False

        q = np.asarray(query, dtype=np.float32)
        q_norm = float(np.linalg.norm(q)) if q.ndim == 1 else 0.0
        if self._matrix is None or q.shape != (self._matrix.shape[1],) or q_norm == 0:
            scored = [(id, cosine_similarity(query, vec)) for id, vec in vectors.items()]
            scored.sort(key=lambda pair: pair[1], reverse=True)
            return scored[:limit]

        sims = self._matrix @ (q / q_norm)
        k = min(limit, len(self._ids))
        top = np.argpartition(-sims, k - 1)[:k]
        top = top[np.argsort(-sims[top], kind="stable")]
        return [(self._ids[i], float(sims[i])) for i in top]


class InMemoryVectorStore(VectorStore):
    """Brute-force cosine similarity (numpy-vectorized, see CosineIndex).
    Fine up to tens of thousands of vectors — swap in Qdrant or pgvector
    beyond that."""

    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}
        self._payloads: dict[str, dict[str, Any]] = {}
        self._index = CosineIndex()

    def upsert(self, id: str, embedding: list[float], payload: dict[str, Any]) -> None:
        self._vectors[id] = embedding
        self._payloads[id] = payload
        self._index.invalidate()

    def search(self, query_embedding: list[float], limit: int = 10) -> list[tuple[str, float]]:
        return self._index.search(self._vectors, query_embedding, limit)


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
