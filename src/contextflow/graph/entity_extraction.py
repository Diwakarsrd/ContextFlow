"""Naive entity extraction: pulls out capitalized-word sequences as
candidate entity names.

This is a heuristic, not real NER — it will over- and under-extract
(sentence-initial words, acronyms, etc.). It exists so the Knowledge
Graph has *something* real to build on for v0.1's "5-minute demo"
without requiring a model download or API key. Replacing this with a
proper NER model (spaCy, an LLM call, or a hybrid) behind the same
`extract_entities(text) -> list[str]` signature is one of the
highest-leverage v0.2 contributions — see CONTRIBUTING.md and
ROADMAP.md ("Entity resolution").
"""

from __future__ import annotations

import re

_PROPER_NOUN_RUN = re.compile(r"\b([A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*){0,3})\b")

_STOPWORDS = {
    "The",
    "This",
    "That",
    "These",
    "Those",
    "A",
    "An",
    "It",
    "We",
    "I",
    "You",
    "They",
    "He",
    "She",
    "In",
    "On",
    "At",
    "For",
    "With",
    "As",
}


def extract_entities(text: str, max_entities: int = 10) -> list[str]:
    candidates = _PROPER_NOUN_RUN.findall(text)
    seen: list[str] = []
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate or candidate in _STOPWORDS:
            continue
        if candidate not in seen:
            seen.append(candidate)
        if len(seen) >= max_entities:
            break
    return seen
