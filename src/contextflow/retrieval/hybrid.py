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
        semantic_weight: float = 1.0,
        keyword_weight: float = 1.0,
    ) -> None:
        self.semantic = semantic
        self.keyword = keyword
        self.rrf_k = rrf_k
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        self.last_scores: dict[str, float] = {}
        """`_retrieval_score` of each result of the most recent query, for
        explanations (see mcp/server.py: explain_context)."""

    def retrieve(self, query: str, limit: int = 10) -> list[ContextObject]:
        semantic_results = self.semantic.retrieve(query, limit=limit * 2)
        keyword_results = self.keyword.retrieve(query, limit=limit * 2)

        scores: dict[str, float] = {}
        objects: dict[str, ContextObject] = {}

        for results, weight in (
            (semantic_results, self.semantic_weight),
            (keyword_results, self.keyword_weight),
        ):
            for rank, obj in enumerate(results):
                scores[obj.id] = scores.get(obj.id, 0.0) + weight / (self.rrf_k + rank + 1)
                if obj.id in objects:
                    # Found by both retrievers: keep both raw scores.
                    obj.metadata = {**objects[obj.id].metadata, **obj.metadata}
                objects[obj.id] = obj

        # Normalize the fused score to [0, 1] (1 = ranked first by both
        # retrievers) so it sits on one scale for the reranker, instead of
        # the reranker comparing raw cosine similarities against raw BM25
        # scores, which are on unrelated scales.
        max_score = (self.semantic_weight + self.keyword_weight) / (self.rrf_k + 1)
        ranked_ids = sorted(scores, key=lambda oid: scores[oid], reverse=True)[:limit]
        self.last_scores = {oid: scores[oid] / max_score for oid in ranked_ids}
        for oid in ranked_ids:
            objects[oid].metadata["_retrieval_score"] = self.last_scores[oid]
        return [objects[oid] for oid in ranked_ids]
