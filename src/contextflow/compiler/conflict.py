"""Conflict detection: flags when two sources disagree on a claim so the
agent (or a human) can decide rather than silently picking one.

v0.1 ships a minimal placeholder. Real conflict detection needs claim
extraction and semantic comparison — see ROADMAP.md v0.2 and
CONTRIBUTING.md if you'd like to help build it.
"""

from __future__ import annotations

from contextflow.core.context import ContextObject
from contextflow.core.context_pack import ConflictingClaim


def detect_conflicts(objects: list[ContextObject]) -> list[ConflictingClaim]:
    # TODO: extract atomic claims per object and compare pairwise for
    # disagreement (e.g. via an LLM call or a lightweight NLI model).
    # Returning an empty list keeps the compiler correct-by-default until
    # this lands.
    return []
