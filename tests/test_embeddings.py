import json

import httpx
import pytest

from contextflow.core.context import ContextObject
from contextflow.embeddings.base import EmbeddingProvider, LocalHashEmbeddingProvider
from contextflow.embeddings.cohere import CohereEmbeddingProvider
from contextflow.embeddings.ollama import OllamaEmbeddingProvider
from contextflow.embeddings.openai import OpenAIEmbeddingProvider
from contextflow.engine import ContextEngine


def test_local_hash_embedding_is_deterministic():
    provider = LocalHashEmbeddingProvider(dimensions=32)
    a = provider.embed("hello world")
    b = provider.embed("hello world")
    assert a == b
    assert len(a) == 32


def test_openai_embedding_provider_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        OpenAIEmbeddingProvider()


def test_openai_embedding_provider_parses_response_in_index_order():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer sk-test"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.2, 0.2]},
                    {"index": 0, "embedding": [0.1, 0.1]},
                ]
            },
        )

    provider = OpenAIEmbeddingProvider(api_key="sk-test")
    provider._client = httpx.Client(
        base_url="https://api.openai.com/v1",
        headers={"Authorization": "Bearer sk-test"},
        transport=httpx.MockTransport(handler),
    )
    result = provider.embed_batch(["first", "second"])
    assert result == [[0.1, 0.1], [0.2, 0.2]]


def test_cohere_embedding_provider_requires_key(monkeypatch):
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        CohereEmbeddingProvider()


def test_cohere_embedding_provider_calls_embed_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embed"
        return httpx.Response(200, json={"embeddings": [[0.5, 0.5]]})

    provider = CohereEmbeddingProvider(api_key="co-test")
    provider._client = httpx.Client(
        base_url="https://api.cohere.com/v1", transport=httpx.MockTransport(handler)
    )
    assert provider.embed("hello") == [0.5, 0.5]


def test_ollama_embedding_provider_infers_dimensions():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embeddings"
        return httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3]})

    provider = OllamaEmbeddingProvider(model="some-custom-model")
    provider._client = httpx.Client(
        base_url="http://localhost:11434", transport=httpx.MockTransport(handler)
    )
    assert provider.dimensions == 0
    result = provider.embed("hello")
    assert result == [0.1, 0.2, 0.3]
    assert provider.dimensions == 3


def test_ollama_embed_batch_uses_batch_endpoint_in_chunks():
    calls: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        inputs = json.loads(request.content)["input"]
        calls.append(inputs)
        return httpx.Response(200, json={"embeddings": [[float(len(t)), 1.0] for t in inputs]})

    provider = OllamaEmbeddingProvider(model="some-custom-model")
    provider._client = httpx.Client(
        base_url="http://localhost:11434", transport=httpx.MockTransport(handler)
    )
    texts = ["a", "bb", "ccc", "dddd", "eeeee"]
    result = provider.embed_batch(texts, batch_size=2)
    assert [len(c) for c in calls] == [2, 2, 1]
    assert result == [[float(len(t)), 1.0] for t in texts]
    assert provider.dimensions == 2


def test_engine_ingest_embeds_through_provider_batch_api():
    class CountingProvider(EmbeddingProvider):
        dimensions = 2

        def __init__(self) -> None:
            self.single_calls = 0
            self.batch_calls = 0

        def embed(self, text: str) -> list[float]:
            self.single_calls += 1
            return [float(len(text)), 1.0]

        def embed_batch(self, texts: list[str]) -> list[list[float]]:
            self.batch_calls += 1
            return [[float(len(t)), 1.0] for t in texts]

    provider = CountingProvider()
    engine = ContextEngine(embedding_provider=provider)
    engine.ingest(
        [ContextObject(id=f"doc{i}", content=f"document {i}", source="test") for i in range(5)]
    )
    assert provider.batch_calls == 1
    assert provider.single_calls == 0
    assert {obj.id for obj in engine.retrieve("document", limit=5)} == {
        f"doc{i}" for i in range(5)
    }
