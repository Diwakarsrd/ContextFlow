"""Tests for SpacyEmbeddingProvider. Skipped (not failed) if spacy or
the en_core_web_md model isn't installed, so contributors without the
~33MB model download aren't blocked — same pattern as the live
PostgreSQL tests.
"""

from __future__ import annotations

import pytest

spacy = pytest.importorskip("spacy", reason="spacy not installed (pip install spacy)")

try:
    spacy.load("en_core_web_md", exclude=["parser", "ner", "tagger"])
    _MODEL_AVAILABLE = True
except OSError:
    _MODEL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _MODEL_AVAILABLE,
    reason="en_core_web_md not installed (python -m spacy download en_core_web_md)",
)


def test_spacy_provider_produces_vectors():
    from contextflow.embeddings.spacy_local import SpacyEmbeddingProvider

    provider = SpacyEmbeddingProvider()
    vec = provider.embed("The dentist appointment was yesterday")
    assert len(vec) == provider.dimensions
    assert provider.dimensions == 300


def test_spacy_provider_semantic_similarity_beats_hash_baseline():
    """The real point of this provider: two paraphrased sentences with
    almost no shared vocabulary should score more similar to each other
    than to an unrelated sentence — something the hashing placeholder
    cannot do at all, since it only matches exact tokens."""
    from contextflow.embeddings.base import LocalHashEmbeddingProvider
    from contextflow.embeddings.spacy_local import SpacyEmbeddingProvider
    from contextflow.storage.local import cosine_similarity

    spacy_provider = SpacyEmbeddingProvider()

    a = spacy_provider.embed("I went to the dentist yesterday")
    b = spacy_provider.embed("When did she visit the dentist?")
    c = spacy_provider.embed("The stock market fell sharply today")

    sim_related = cosine_similarity(a, b)
    sim_unrelated = cosine_similarity(a, c)
    assert sim_related > sim_unrelated

    hash_provider = LocalHashEmbeddingProvider()
    hash_a = hash_provider.embed("I went to the dentist yesterday")
    hash_b = hash_provider.embed("When did she visit the dentist?")
    hash_sim = cosine_similarity(hash_a, hash_b)
    # The hash provider shares almost no exact tokens between these two
    # paraphrased sentences, so its similarity should be near zero —
    # spaCy's should be meaningfully higher, demonstrating the actual
    # capability gap this provider closes.
    assert sim_related > hash_sim


def test_engine_with_spacy_provider_retrieves_paraphrased_query():
    from contextflow.core.context import ContextObject
    from contextflow.embeddings.spacy_local import SpacyEmbeddingProvider
    from contextflow.engine import ContextEngine

    engine = ContextEngine(embedding_provider=SpacyEmbeddingProvider())
    engine.ingest(
        [ContextObject(content="I went to the dentist yesterday for a cleaning", source="t")]
    )
    # Paraphrased query sharing almost no exact vocabulary with the
    # ingested content — this is exactly the case LocalHashEmbeddingProvider
    # cannot handle, since it only matches exact tokens.
    results = engine.retrieve("When did she visit the dental office?", limit=5)
    assert len(results) > 0
