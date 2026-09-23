from itertools import pairwise

import pytest

from contextflow.core.context import ContextObject
from contextflow.engine import ContextEngine
from contextflow.ingestion.chunking import chunk_text


def test_short_text_is_a_single_chunk():
    assert chunk_text("One sentence.", chunk_size=100, overlap=10) == ["One sentence."]
    assert chunk_text("", chunk_size=100, overlap=10) == []


def test_chunks_break_on_sentence_boundaries_within_size():
    sentences = [f"Sentence number {i} talks about topic {i}." for i in range(40)]
    chunks = chunk_text(" ".join(sentences), chunk_size=200, overlap=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 200
        assert chunk.endswith(".")  # never cut mid-sentence
    # every sentence survives intact in some chunk
    for s in sentences:
        assert any(s in c for c in chunks)


def test_consecutive_chunks_overlap():
    text = " ".join(f"Fact {i} is here." for i in range(50))
    chunks = chunk_text(text, chunk_size=120, overlap=40)
    for a, b in pairwise(chunks):
        assert a.split(". ")[-1].rstrip(".") in b


def test_overlong_sentence_is_split_on_whitespace():
    chunks = chunk_text("word " * 100, chunk_size=50, overlap=10)
    assert all(len(c) <= 50 for c in chunks)
    assert all(not c.startswith(" ") and "wor d" not in c for c in chunks)


def test_rejects_overlap_not_smaller_than_size():
    with pytest.raises(ValueError):
        chunk_text("x", chunk_size=10, overlap=10)


def test_every_chunk_of_a_long_document_is_stored_and_retrievable():
    # Regression: chunks used to share the parent's id, so each one
    # overwrote the last and only the final chunk was retrievable.
    body = "Alpha section about apples. " * 60 + "Omega section about zebras. " * 60
    engine = ContextEngine()
    n = engine.ingest([ContextObject(id="doc1", content=body, source="t")])
    assert n > 1
    stored = engine.metadata_store.all()
    assert len(stored) == n
    assert {o.metadata["parent_id"] for o in stored} == {"doc1"}
    assert sorted(o.metadata["chunk_index"] for o in stored) == list(range(n))
    top = engine.retrieve("apples", limit=1)[0]
    assert "apples" in top.content
    assert top.id.startswith("doc1#chunk-")


def test_short_document_keeps_its_id():
    engine = ContextEngine()
    engine.ingest([ContextObject(id="short", content="Tiny note.", source="t")])
    assert [o.id for o in engine.metadata_store.all()] == ["short"]
