"""Builds the entity/relationship graph from ContextObjects.

v0.1 ships a co-mention graph over naively-extracted entities (see
`entity_extraction.py`): entities mentioned in the same object get a
`co_mentioned` edge, and each entity gets a `mentioned_in` edge to its
source so `traverse()` can answer "what talks about X". Real entity
resolution (merging "Acme" / "Acme Corp" / "@acme") is a v0.2 target —
see ROADMAP.md.
"""

from __future__ import annotations

from contextflow.core.context import ContextObject
from contextflow.core.metadata import GraphStore


def build_from_objects(objects: list[ContextObject], graph_store: GraphStore) -> None:
    entities: list[tuple[str, dict]] = []
    relationships: list[tuple[str, str, str, float]] = []

    for obj in objects:
        for entity_id in obj.entities:
            entities.append((entity_id, {"name": entity_id}))
            relationships.append((entity_id, obj.id, "mentioned_in", 1.0))
        for i, a in enumerate(obj.entities):
            for b in obj.entities[i + 1 :]:
                relationships.append((a, b, "co_mentioned", 1.0))
                relationships.append((b, a, "co_mentioned", 1.0))

    # Batched (see core/metadata.py: GraphStore.add_entities_batch) so
    # file-backed graph stores write to disk once, not once per
    # entity/relationship — the same class of O(n^2) bug fixed in
    # FileVectorStore, found via a real performance benchmark.
    graph_store.add_entities_batch(entities)
    graph_store.add_relationships_batch(relationships)
