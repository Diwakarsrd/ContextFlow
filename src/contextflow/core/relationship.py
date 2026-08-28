"""Relationships are the edges of the Context Graph."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class Relationship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_entity_id: str
    target_entity_id: str
    type: str
    """e.g. 'works_on', 'reports_to', 'mentions', 'blocks'."""
    weight: float = 1.0
    """Relationship strength, used by graph retrieval/traversal."""
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    """ContextObject IDs that support this relationship existing."""
