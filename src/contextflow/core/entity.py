"""Entities are the nodes of the Context Graph: people, projects,
organizations, tickets, or anything else the engine tracks identity for."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

EntityType = Literal["person", "organization", "project", "document", "ticket", "custom"]


class Entity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EntityType
    name: str
    aliases: list[str] = Field(default_factory=list)
    """Alternate names/handles used for entity resolution across sources."""
    attributes: dict[str, Any] = Field(default_factory=dict)
    source_ids: list[str] = Field(default_factory=list)
    """ContextObject IDs that mention or evidence this entity."""
