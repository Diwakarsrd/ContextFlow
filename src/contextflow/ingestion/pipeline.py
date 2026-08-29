"""Ties parsing -> normalization -> chunking -> dedup together for a
connector's raw output, producing ContextObjects ready for indexing."""

from __future__ import annotations

from contextflow.core.context import ContextObject
from contextflow.ingestion.chunking import chunk_text
from contextflow.ingestion.deduplication import deduplicate
from contextflow.ingestion.normalization import normalize_text


def process(objects: list[ContextObject], chunk_size: int = 1000) -> list[ContextObject]:
    processed = []
    for obj in objects:
        clean = normalize_text(obj.content)
        for piece in chunk_text(clean, chunk_size=chunk_size):
            processed.append(obj.model_copy(update={"content": piece}))
    return deduplicate(processed)
