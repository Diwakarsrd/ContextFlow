"""Graph traversal helpers built on top of GraphStore.traverse()."""

from __future__ import annotations

from typing import Any

from contextflow.core.metadata import GraphStore


def neighbors(graph_store: GraphStore, entity_id: str, depth: int = 1) -> list[dict[str, Any]]:
    return graph_store.traverse(entity_id, depth=depth)
