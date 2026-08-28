"""EmbeddingProvider interface: the seam between ContextFlow and whatever
turns text into vectors.

This is the single biggest gap between the v0.1 scaffold and something
usable for real retrieval — the previous default (`_default_hash_embed`
in this module) is a dependency-free hashing trick with no actual
semantic understanding, kept only as an offline fallback so the local
demo works with zero API keys. Real semantic search requires a real
provider: OpenAI, Ollama (local), or Cohere below, or a
community-contributed one (Hugging Face / sentence-transformers,
Voyage, etc. — see CONTRIBUTING.md).
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Implementations must be deterministic for a given text/model and
    return vectors of consistent dimensionality for a given instance."""

    dimensions: int

    @abstractmethod
    def embed(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Default: embed one at a time. Override for providers with a
        real batch endpoint (OpenAI, Cohere) — it's meaningfully faster
        and cheaper than N single calls."""
        return [self.embed(text) for text in texts]


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Dependency-free, deterministic placeholder — a hashing trick, not
    a real embedding model. It has no semantic understanding: it can
    match exact/overlapping vocabulary but won't know that "car" and
    "automobile" are related.

    This exists purely so `ContextEngine()` works out of the box with no
    API key for smoke-testing and the CLI quickstart. Do not use this for
    anything where retrieval quality matters — configure a real provider
    (`OpenAIEmbeddingProvider`, `OllamaEmbeddingProvider`,
    `CohereEmbeddingProvider`) instead.
    """

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = digest[0] % self.dimensions
            vector[idx] += 1.0
        return vector
