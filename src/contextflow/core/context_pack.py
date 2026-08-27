"""ContextPack: the compiled, agent-ready output of a retrieval +
compilation pass.

Where `ContextObject` is the atomic unit stored internally, `ContextPack`
is what gets handed to an agent or LLM — organized by category, budgeted
to a token limit, with conflicts surfaced rather than silently resolved.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from contextflow.core.context import ContextObject


class ConflictingClaim(BaseModel):
    claim_a: str
    claim_b: str
    source_a: str
    source_b: str
    resolution: str | None = None
    """Human-readable explanation of which claim is more likely correct
    and why (e.g. "newer", "higher authority source")."""


class ContextPack(BaseModel):
    """Agent-facing bundle of context for a task, optionally scoped to an
    entity (e.g. a customer, a project, a person)."""

    task: str
    entity: str | None = None

    facts: list[dict[str, Any]] = Field(default_factory=list)
    people: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    conversations: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)

    sources: list[str] = Field(default_factory=list)
    conflicts: list[ConflictingClaim] = Field(default_factory=list)

    token_budget: int | None = None
    tokens_used: int | None = None
    confidence: float = 0.0

    @classmethod
    def empty(cls, task: str, entity: str | None = None) -> ContextPack:
        return cls(task=task, entity=entity)

    def add_object(self, obj: ContextObject, bucket: str) -> None:
        """Route a retrieved/compiled ContextObject into the right bucket
        (facts, documents, conversations, ...) on this pack."""
        target = getattr(self, bucket, None)
        if target is None or not isinstance(target, list):
            raise ValueError(f"Unknown ContextPack bucket: {bucket!r}")
        target.append(
            {
                "id": obj.id,
                "content": obj.content,
                "source": obj.source,
                "confidence": obj.confidence,
                "freshness": obj.freshness,
            }
        )
        if obj.source not in self.sources:
            self.sources.append(obj.source)
