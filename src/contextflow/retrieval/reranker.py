"""Reranking interface. Ship a simple heuristic reranker by default;
contributors can add cross-encoder / LLM-based rerankers behind the same
interface (see CONTRIBUTING.md: "Improve retrieval")."""

from __future__ import annotations

from abc import ABC, abstractmethod

from contextflow.core.context import ContextObject


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, candidates: list[ContextObject]) -> list[ContextObject]: ...


class QualityWeightedReranker(Reranker):
    """Reorders candidates by a blend of retrieval score, freshness,
    confidence, and trust. No model call required — good default."""

    def __init__(
        self,
        freshness_weight: float = 0.15,
        confidence_weight: float = 0.15,
        trust_weight: float = 0.1,
    ) -> None:
        self.freshness_weight = freshness_weight
        self.confidence_weight = confidence_weight
        self.trust_weight = trust_weight

    def rerank(self, query: str, candidates: list[ContextObject]) -> list[ContextObject]:
        def score(obj: ContextObject) -> float:
            base = obj.metadata.get("_semantic_score") or obj.metadata.get("_keyword_score") or 0.0
            return (
                base
                + self.freshness_weight * obj.freshness
                + self.confidence_weight * obj.confidence
                + self.trust_weight * obj.trust
            )

        return sorted(candidates, key=score, reverse=True)
