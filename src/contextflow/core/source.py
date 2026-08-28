"""Describes a connected data source (an installed + configured connector
instance), independent of any single ContextObject fetched from it."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Source(BaseModel):
    name: str
    """Unique source identifier, e.g. 'github:yourorg/yourrepo'."""
    connector_type: str
    """Which Connector implementation this is, e.g. 'github'."""
    config: dict[str, Any] = Field(default_factory=dict)
    last_synced_at: datetime | None = None
    status: str = "not_configured"
    """One of: not_configured | connected | syncing | error."""
