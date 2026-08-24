# Embedding Providers

`ContextEngine` takes an `embedding_provider` (preferred) or a raw
`embed_fn`. Three real providers ship in v0.1:

```python
from contextflow import ContextEngine
from contextflow.embeddings.openai import OpenAIEmbeddingProvider

engine = ContextEngine(embedding_provider=OpenAIEmbeddingProvider())
```

- `contextflow.embeddings.openai.OpenAIEmbeddingProvider` — hosted, needs `$OPENAI_API_KEY`
- `contextflow.embeddings.cohere.CohereEmbeddingProvider` — hosted, needs `$COHERE_API_KEY`
- `contextflow.embeddings.ollama.OllamaEmbeddingProvider` — fully local, needs a running Ollama server
- `contextflow.embeddings.spacy_local.SpacyEmbeddingProvider` — fully local,
  **no API key and no running server** — just `pip install spacy &&
  python -m spacy download en_core_web_md`. Uses averaged GloVe-style
  word vectors. Weaker than a modern sentence-transformer or API
  embedding (naive mean-pooling is a known-weak sentence
  representation), but measurably better than the hash placeholder —
  see `benchmarks/external/locomo/RESULTS.md` for a real, measured
  comparison: roughly doubled Recall@5 on a real external benchmark
  versus the hash default, while still using zero external services.

The CLI picks a provider from `$CONTEXTOS_EMBEDDING_PROVIDER`
(`openai`/`ollama`/`cohere`/`spacy`) — see `.env.example`. `spacy` is the
easiest real upgrade from the default: no API key, no server, just a
one-time `pip install spacy && python -m spacy download en_core_web_md`.

## The default: `LocalHashEmbeddingProvider`

If no provider is configured, `ContextEngine()` falls back to
`contextflow.embeddings.base.LocalHashEmbeddingProvider` — a deterministic
hashing trick with **no real semantic understanding**. It exists purely
so the local quickstart works with zero API keys. Do not use it for
anything where retrieval quality matters.

## Adding a provider

Implement `EmbeddingProvider` (`embed(text) -> list[float]`, optionally
`embed_batch` for a real batch endpoint) — see any of the three built-in
providers for the pattern. Hugging Face / sentence-transformers and
Voyage AI are open, wanted contributions (see `CONTRIBUTING.md`).

## One gotcha

Vectors from different providers/models aren't compatible — mixing them
in one workspace silently degrades search. If you switch
`CONTEXTOS_EMBEDDING_PROVIDER`, re-ingest into a fresh `.contextflow/`
workspace rather than reusing one that was populated with a different
provider.
