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


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model: str = "nomic-embed-text",
        host: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.dimensions = _KNOWN_DIMENSIONS.get(model, 0)
        host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self._client = httpx.Client(base_url=host, timeout=timeout)

    def embed(self, text: str) -> list[float]:
        resp = self._client.post("/api/embeddings", json={"model": self.model, "prompt": text})
        resp.raise_for_status()
        embedding = resp.json()["embedding"]
        if not self.dimensions:
            self.dimensions = len(embedding)
        return embedding
