"""Query router: picks which retrieval strategy (or combination) to use.

v0.1 ships a single default (hybrid retrieval for everything). Adaptive,
intent-based routing (e.g. graph traversal for "who owns X" queries) is
planned for v0.3 — see ROADMAP.md.
"""

from __future__ import annotations

from contextflow.core.context import ContextObject
from contextflow.retrieval.hybrid import HybridRetriever


class RetrievalRouter:
    def __init__(self, hybrid: HybridRetriever) -> None:
        self.hybrid = hybrid

    def route(self, query: str, limit: int = 10) -> list[ContextObject]:
        # TODO(v0.3): detect intent (lookup vs. relational vs. temporal)
        # and route to graph/temporal retrievers when appropriate.
        return self.hybrid.retrieve(query, limit=limit)
