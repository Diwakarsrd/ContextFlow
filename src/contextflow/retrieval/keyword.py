"""Keyword retrieval via BM25 (rank_bm25). Good complement to semantic
search for exact terms, IDs, and jargon embeddings tend to blur."""

from __future__ import annotations

import re

from contextflow.core.context import ContextObject

_TOKEN = re.compile(r"\w+(?:'\w+)?")
# Question words and auxiliaries dominate short queries ("what did X
# do ...") and match nearly every document, drowning out content terms.
_STOPWORDS = frozenset(
    "a an and are as at be been but by can could did do does for from had has have how "  # noqa: SIM905
    "i if in into is it its me my of on or our she he so than that the their them then "
    "there these they this to was we were what when where which who whom why will with "
    "would you your".split()
)


def _normalize(token: str) -> str:
    """Minimal suffix folding so "Acme's" matches "Acme" and "payments"
    matches "payment". Deliberately conservative (no full stemmer):
    only possessives and plain plural -s, leaving "-ss"/"-us"/"-is"
    words ("access", "status", "analysis") alone."""
    token = token.removesuffix("'s")
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        token = token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    """Lowercase, suffix-folded word tokens without punctuation or
    stopwords, so "yesterday." matches "yesterday" and "what did"
    matches nothing."""
    return [
        _normalize(t) for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS
    ]


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

        tokenized = [tokenize(obj.content) for obj in self._objects]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None
        self._dirty = False

    def retrieve(self, query: str, limit: int = 10) -> list[ContextObject]:
        self._ensure_index()
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(zip(self._objects, scores), key=lambda pair: pair[1], reverse=True)
        results = []
        for obj, score in ranked[:limit]:
            if score <= 0:
                # No query term matched; don't hand fusion a fake rank.
                break
            # Per-query copy, for the same reason as SemanticRetriever.
            metadata = {**obj.metadata, "_keyword_score": float(score)}
            results.append(obj.model_copy(update={"metadata": metadata}))
        return results
