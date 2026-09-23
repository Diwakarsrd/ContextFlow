"""Ollama embedding provider — runs fully locally against a running
Ollama server, no API key or internet access required beyond pulling the
model once.

    ollama pull nomic-embed-text
    ollama serve   # usually already running as a background service

    from contextflow.embeddings.ollama import OllamaEmbeddingProvider

    provider = OllamaEmbeddingProvider(model="nomic-embed-text")
    engine = ContextEngine(embed_fn=provider.embed)
"""

from __future__ import annotations

import os

import httpx

from contextflow.embeddings.base import EmbeddingProvider

# Known dimensions for common Ollama embedding models. Unknown models
# fall back to inferring dimensions from the first real response.
_KNOWN_DIMENSIONS = {
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    "all-minilm": 384,
}

# (query prefix, document prefix) that these models were trained with;
# per their model cards, retrieval quality drops without them.
_KNOWN_PREFIXES = {
    "nomic-embed-text": ("search_query: ", "search_document: "),
    "mxbai-embed-large": ("Represent this sentence for searching relevant passages: ", ""),
}


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model: str = "nomic-embed-text",
        host: str | None = None,
        timeout: float = 60.0,
        query_prefix: str | None = None,
        document_prefix: str | None = None,
    ) -> None:
        self.model = model
        self.dimensions = _KNOWN_DIMENSIONS.get(model, 0)
        default_query_prefix, default_document_prefix = _KNOWN_PREFIXES.get(
            model.split(":")[0], ("", "")
        )
        self.query_prefix = default_query_prefix if query_prefix is None else query_prefix
        self.document_prefix = (
            default_document_prefix if document_prefix is None else document_prefix
        )
        host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self._client = httpx.Client(base_url=host, timeout=timeout)

    def embed(self, text: str) -> list[float]:
        return self._embed_one(self.document_prefix + text)

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(self.query_prefix + text)

    def _embed_one(self, text: str) -> list[float]:
        # `/api/embed` (Ollama >= 0.3), not the deprecated `/api/embeddings`:
        # measured ~150ms vs ~1s per call on a CPU-only machine, and it
        # returns the same normalized vectors as `embed_batch`.
        resp = self._client.post("/api/embed", json={"model": self.model, "input": [text]})
        resp.raise_for_status()
        embedding = resp.json()["embeddings"][0]
        if not self.dimensions:
            self.dimensions = len(embedding)
        return embedding

    def embed_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Uses Ollama's batch `/api/embed` endpoint (Ollama >= 0.3) — one
        request per `batch_size` texts instead of one per text, roughly
        10x faster on CPU."""
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            chunk = [self.document_prefix + t for t in texts[start : start + batch_size]]
            resp = self._client.post("/api/embed", json={"model": self.model, "input": chunk})
            resp.raise_for_status()
            embeddings.extend(resp.json()["embeddings"])
        if embeddings and not self.dimensions:
            self.dimensions = len(embeddings[0])
        return embeddings
