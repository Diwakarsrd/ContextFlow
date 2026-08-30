"""Hybrid retrieval: fuses semantic + keyword (+ graph, when available)
results via reciprocal rank fusion.

Contributors: this is a good place to add a new fusion strategy or plug
in a learned reranker — see CONTRIBUTING.md.
"""

from __future__ import annotations

from contextflow.core.context import ContextObject
from contextflow.retrieval.keyword import KeywordRetriever
from contextflow.retrieval.semantic import SemanticRetriever


class HybridRetriever:
    def __init__(
        self,
        semantic: SemanticRetriever,
        keyword: KeywordRetriever,
        rrf_k: int = 60,
    ) -> None:
        self.semantic = semantic
        self.keyword = keyword
        self.rrf_k = rrf_k

    def retrieve(self, query: str, limit: int = 10) -> list[ContextObject]:
        semantic_results = self.semantic.retrieve(query, limit=limit * 2)
        keyword_results = self.keyword.retrieve(query, limit=limit * 2)

        scores: dict[str, float] = {}
        objects: dict[str, ContextObject] = {}

        for rank, obj in enumerate(semantic_results):
            scores[obj.id] = scores.get(obj.id, 0.0) + 1.0 / (self.rrf_k + rank + 1)
            objects[obj.id] = obj

        for rank, obj in enumerate(keyword_results):
            scores[obj.id] = scores.get(obj.id, 0.0) + 1.0 / (self.rrf_k + rank + 1)
            objects[obj.id] = obj

        ranked_ids = sorted(scores, key=lambda oid: scores[oid], reverse=True)
        return [objects[oid] for oid in ranked_ids[:limit]]
