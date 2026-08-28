"""Local, fully-offline semantic embedding provider using spaCy's
pretrained GloVe-style word vectors — no API key, no running server
(unlike OpenAI/Cohere/Ollama), just a one-time model download.

    python -m spacy download en_core_web_md
    # or en_core_web_lg for higher quality / larger download

    from contextflow.embeddings.spacy_local import SpacyEmbeddingProvider
    engine = ContextEngine(embedding_provider=SpacyEmbeddingProvider())

This is a genuine semantic embedding — averaged word vectors captured
from real distributional training data, unlike
LocalHashEmbeddingProvider's hashing trick, which has no notion of word
meaning at all. It is NOT as strong as a modern sentence-transformer or
API-based embedding: naive average-pooling of word vectors is a known-
weak sentence representation (see the docstring note on measured
LoCoMo results below). It exists as a middle ground: meaningfully more
semantic than hashing, with zero external API dependency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from contextflow.embeddings.base import EmbeddingProvider

if TYPE_CHECKING:
    from spacy.language import Language

# spacy is an optional dependency (the `spacy` extra) imported lazily in
# __init__ below, so this module can be imported even without spacy
# installed — only instantiating SpacyEmbeddingProvider requires it.
_MODEL_CACHE: dict[str, Language] = {}


class SpacyEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str = "en_core_web_md") -> None:
        try:
            import spacy
        except ImportError as exc:
            raise ImportError(
                "SpacyEmbeddingProvider requires spacy: pip install spacy && "
                f"python -m spacy download {model}"
            ) from exc

        if model not in _MODEL_CACHE:
            try:
                # We only need vocab.vectors for averaging, not any
                # pipeline component — exclude them all for speed and to
                # avoid an irrelevant "no POS annotation" warning from
                # the lemmatizer, which we never invoke.
                _MODEL_CACHE[model] = spacy.load(
                    model, exclude=["parser", "ner", "tagger", "attribute_ruler", "lemmatizer"]
                )
            except OSError as exc:
                raise RuntimeError(
                    f"spaCy model {model!r} not installed. Run: python -m spacy download {model}"
                ) from exc
        self._nlp: Language = _MODEL_CACHE[model]
        self.dimensions = self._nlp.vocab.vectors.shape[1]

        if not self._nlp.vocab.vectors.shape[0]:
            raise RuntimeError(
                f"spaCy model {model!r} has no word vectors (e.g. en_core_web_sm doesn't). "
                "Use en_core_web_md or en_core_web_lg."
            )

    def embed(self, text: str) -> list[float]:
        return self._nlp(text).vector.tolist()
