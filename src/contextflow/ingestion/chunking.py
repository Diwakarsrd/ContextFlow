"""Splits long content into retrieval-sized chunks. v0.1 ships a simple
fixed-size splitter with overlap; semantic/structural chunking (by
heading, function, etc.) is a good v0.2 contribution."""

from __future__ import annotations


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks
