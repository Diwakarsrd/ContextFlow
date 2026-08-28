"""Cohere embedding provider.

Config: pass `api_key` explicitly or set `$COHERE_API_KEY`.

    from contextflow.embeddings.cohere import CohereEmbeddingProvider

    provider = CohereEmbeddingProvider()
    engine = ContextEngine(embed_fn=provider.embed)
"""

from __future__ import annotations

import os

import httpx

from contextflow.embeddings.base import EmbeddingProvider

_DIMENSIONS = {
    "embed-english-v3.0": 1024,
    "embed-multilingual-v3.0": 1024,
    "embed-english-light-v3.0": 384,
}


class CohereEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model: str = "embed-english-v3.0",
        api_key: str | None = None,
        input_type: str = "search_document",
        base_url: str = "https://api.cohere.com/v1",
        timeout: float = 30.0,
    ) -> None:
        key = api_key or os.environ.get("COHERE_API_KEY")
        if not key:
            raise RuntimeError("CohereEmbeddingProvider requires api_key or $COHERE_API_KEY")
        self.model = model
        self.input_type = input_type
        self.dimensions = _DIMENSIONS.get(model, 1024)
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=timeout,
        )

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.post(
            "/embed",
            json={"model": self.model, "texts": texts, "input_type": self.input_type},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]
