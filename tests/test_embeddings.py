import httpx
import pytest

from contextflow.embeddings.base import LocalHashEmbeddingProvider
from contextflow.embeddings.cohere import CohereEmbeddingProvider
from contextflow.embeddings.ollama import OllamaEmbeddingProvider
from contextflow.embeddings.openai import OpenAIEmbeddingProvider


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
