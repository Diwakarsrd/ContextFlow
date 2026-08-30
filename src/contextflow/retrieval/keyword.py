"""Keyword retrieval via BM25 (rank_bm25). Good complement to semantic
search for exact terms, IDs, and jargon embeddings tend to blur."""

from __future__ import annotations

from contextflow.core.context import ContextObject


class KeywordRetriever:
    def __init__(self) -> None:
        self._objects: list[ContextObject] = []
        self._bm25 = None
        self._dirty = True

    def index(self, obj: ContextObject) -> None:
        self._objects.append(obj)
        self._dirty = True

    def _ensure_index(self) -> None:
        if not self._dirty:
            return
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "KeywordRetriever requires `rank-bm25` (pip install rank-bm25)"
            ) from exc

        tokenized = [obj.content.lower().split() for obj in self._objects]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None
        self._dirty = False

    def retrieve(self, query: str, limit: int = 10) -> list[ContextObject]:
        self._ensure_index()
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(query.lower().split())
        ranked = sorted(zip(self._objects, scores), key=lambda pair: pair[1], reverse=True)
        results = []
        for obj, score in ranked[:limit]:
            obj.metadata["_keyword_score"] = float(score)
            results.append(obj)
        return results
