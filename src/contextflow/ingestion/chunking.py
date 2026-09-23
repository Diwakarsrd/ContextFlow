"""Splits long content into retrieval-sized chunks.

Packs whole sentences into chunks of up to `chunk_size` characters, so a
chunk never ends mid-word or mid-sentence (a fact split across two
chunks can't be retrieved whole by either). Consecutive chunks share up
to `overlap` characters of trailing sentences for continuity. A single
sentence longer than `chunk_size` is split at whitespace. Structural
chunking (by heading, function, etc.) is a good v0.2 contribution.
"""

from __future__ import annotations

import re

# End of a sentence: terminal punctuation (optionally followed by a
# closing quote/bracket) then whitespace, or a paragraph break.
_SENTENCE_END = re.compile(r"(?<=[.!?])[\"'”’)\]]*\s+|\n\s*\n")


def _sentences(text: str) -> list[str]:
    return [s for s in (p.strip() for p in _SENTENCE_END.split(text)) if s]


def _split_long(sentence: str, chunk_size: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for word in sentence.split():
        if current and len(current) + 1 + len(word) > chunk_size:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        pieces.append(current)
    return pieces


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    if len(text) <= chunk_size:
        return [text] if text else []

    units: list[str] = []
    for sentence in _sentences(text):
        units.extend(_split_long(sentence, chunk_size) if len(sentence) > chunk_size else [sentence])

    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for unit in units:
        if current and length + 1 + len(unit) > chunk_size:
            chunks.append(" ".join(current))
            # Carry trailing sentences (up to `overlap` chars) forward.
            carried: list[str] = []
            carried_len = 0
            for prev in reversed(current):
                if carried_len + len(prev) + 1 > overlap:
                    break
                carried.insert(0, prev)
                carried_len += len(prev) + 1
            current, length = carried, max(carried_len - 1, 0)
        current.append(unit)
        length += len(unit) + (1 if length else 0)
    if current:
        chunks.append(" ".join(current))
    return chunks
