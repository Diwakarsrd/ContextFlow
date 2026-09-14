"""OpenAI embedding provider.

Config: pass `api_key` explicitly or set `$OPENAI_API_KEY`.

    from contextflow.embeddings.openai import OpenAIEmbeddingProvider

    provider = OpenAIEmbeddingProvider(model="text-embedding-3-small")
    engine = ContextEngine(embed_fn=provider.embed)
"""

from __future__ import annotations

import os

import httpx

from contextflow.embeddings.base import EmbeddingProvider

_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ) -> None:
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OpenAIEmbeddingProvider requires api_key or $OPENAI_API_KEY")
        self.model = model
        self.dimensions = _DIMENSIONS.get(model, 1536)
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=timeout,
        )

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.post("/embeddings", json={"model": self.model, "input": texts})
        resp.raise_for_status()
        data = resp.json()["data"]
        # The API doesn't guarantee response order matches input order in
        # all client libraries' docs examples, but per OpenAI's spec the
        # `index` field on each item does — sort defensively by it.
        data.sort(key=lambda item: item["index"])
        return [item["embedding"] for item in data]
