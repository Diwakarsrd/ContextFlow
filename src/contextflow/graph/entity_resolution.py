"""Entity resolution: merges references to the same real-world entity
across sources (e.g. "@jsmith" on Slack and "John Smith" in Jira).
Planned for v0.2 — see ROADMAP.md and CONTRIBUTING.md."""

from __future__ import annotations

from contextflow.core.entity import Entity


def resolve(candidates: list[Entity]) -> list[Entity]:
    # TODO: cluster candidates by name/alias similarity + co-occurrence.
    return candidates
