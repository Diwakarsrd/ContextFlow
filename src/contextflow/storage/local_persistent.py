"""JSON-file-backed VectorStore and GraphStore.

Together with `storage.sqlite.SQLiteMetadataStore`, these back the CLI's
persistent local-first workspace (`.contextflow/`) — `contextflow ingest`
and `contextflow search` now share state across separate process
invocations.

Brute-force cosine similarity and an edge-list graph are fine up to a
few thousand objects. Swap in Qdrant/pgvector and Neo4j (contributor
territory — see CONTRIBUTING.md) well before that point.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contextflow.core.metadata import GraphStore, VectorStore
from contextflow.storage.local import cosine_similarity


class FileVectorStore(VectorStore):
    def __init__(self, path: str = ".contextflow/vectors.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._vectors: dict[str, list[float]] = {}
        self._payloads: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text() or "{}")
            self._vectors = data.get("vectors", {})
            self._payloads = data.get("payloads", {})

    def _save(self) -> None:
        self.path.write_text(
            json.dumps({"vectors": self._vectors, "payloads": self._payloads})
        )

    def upsert(self, id: str, embedding: list[float], payload: dict[str, Any]) -> None:
        self._vectors[id] = embedding
        self._payloads[id] = payload
        self._save()

    def upsert_batch(self, items: list[tuple[str, list[float], dict[str, Any]]]) -> None:
        """Overrides the default loop-over-upsert: writes to disk once
        after updating all items in memory, not once per item. Without
        this, ingesting N objects did N full-file JSON rewrites of an
        ever-growing file — O(n) per write, O(n^2) total — found via a
        real performance benchmark (benchmarks/performance/results.md)
        showing ingestion throughput *dropping* as corpus size grew."""
        for id, embedding, payload in items:
            self._vectors[id] = embedding
            self._payloads[id] = payload
        self._save()

    def search(self, query_embedding: list[float], limit: int = 10) -> list[tuple[str, float]]:
        scored = [
            (id, cosine_similarity(query_embedding, vec)) for id, vec in self._vectors.items()
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:limit]

    def count(self) -> int:
        return len(self._vectors)


class FileGraphStore(GraphStore):
    def __init__(self, path: str = ".contextflow/graph.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entities: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text() or "{}")
            self._entities = data.get("entities", {})
            self._edges = data.get("edges", [])

    def _save(self) -> None:
        self.path.write_text(
            json.dumps({"entities": self._entities, "edges": self._edges})
        )

    def add_entity(self, entity_id: str, attributes: dict[str, Any]) -> None:
        self._add_entity_no_save(entity_id, attributes)
        self._save()

    def _add_entity_no_save(self, entity_id: str, attributes: dict[str, Any]) -> None:
        existing = self._entities.get(entity_id, {})
        existing.update(attributes)
        self._entities[entity_id] = existing

    def add_entities_batch(self, entities: list[tuple[str, dict[str, Any]]]) -> None:
        """See `FileVectorStore.upsert_batch` — same O(n^2)
        full-file-rewrite-per-call bug, same fix: update in memory, save
        once."""
        for entity_id, attributes in entities:
            self._add_entity_no_save(entity_id, attributes)
        self._save()

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        return self._entities.get(entity_id)

    def add_relationship(
        self, source_id: str, target_id: str, rel_type: str, weight: float = 1.0
    ) -> None:
        self._add_relationship_no_save(source_id, target_id, rel_type, weight)
        self._save()

    def _add_relationship_no_save(
        self, source_id: str, target_id: str, rel_type: str, weight: float
    ) -> None:
        for edge in self._edges:
            if (
                edge["source"] == source_id
                and edge["target"] == target_id
                and edge["type"] == rel_type
            ):
                edge["weight"] = edge.get("weight", 0.0) + weight
                return
        self._edges.append(
            {"source": source_id, "target": target_id, "type": rel_type, "weight": weight}
        )

    def add_relationships_batch(
        self, relationships: list[tuple[str, str, str, float]]
    ) -> None:
        for source_id, target_id, rel_type, weight in relationships:
            self._add_relationship_no_save(source_id, target_id, rel_type, weight)
        self._save()

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

    def entities(self) -> dict[str, dict[str, Any]]:
        return dict(self._entities)
