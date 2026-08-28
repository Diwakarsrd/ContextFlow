"""Relevance judging helpers for building/validating benchmark datasets."""

from __future__ import annotations


def is_relevant(query: str, content: str) -> bool:
    raise NotImplementedError(
        "is_relevant needs a judging implementation (heuristic or LLM) — see CONTRIBUTING.md"
    )
