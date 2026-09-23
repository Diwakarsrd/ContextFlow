"""Reranking interface. Ship a simple heuristic reranker by default;
contributors can add cross-encoder / LLM-based rerankers behind the same
interface (see CONTRIBUTING.md: "Improve retrieval")."""

from __future__ import annotations

from abc import ABC, abstractmethod

from contextflow.core.context import ContextObject


def retrieval_score(obj: ContextObject) -> float:
    """The fused hybrid score when present; otherwise whichever single
    retriever score the object carries (e.g. a retriever used directly)."""
    for key in ("_retrieval_score", "_semantic_score", "_keyword_score"):
        if key in obj.metadata:
            return float(obj.metadata[key])
    return 0.0


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
            base = retrieval_score(obj)
            return (
                base
                + self.freshness_weight * obj.freshness
                + self.confidence_weight * obj.confidence
                + self.trust_weight * obj.trust
            )

        return sorted(candidates, key=score, reverse=True)
