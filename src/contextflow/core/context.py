"""The ContextObject: the atomic unit every connector, retriever, and
compiler in ContextFlow speaks.

Every connector normalizes whatever it fetches (a Slack message, a GitHub
issue, a Postgres row) into one or more ContextObjects. Everything
downstream — retrieval, ranking, graph building, compilation — operates
on this shared schema.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

ContextType = Literal[
    "document",
    "message",
    "ticket",
    "record",
    "code",
    "commit",
    "email",
    "conversation",
    "custom",
]


class ContextObject(BaseModel):
    """A single, normalized piece of context from any source."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: ContextType = "document"
    content: str
    source: str
    """Name of the connector/source this came from, e.g. 'github'."""

    entities: list[str] = Field(default_factory=list)
    """IDs of entities (people, projects, orgs) mentioned in this object."""

    relationships: list[str] = Field(default_factory=list)
    """IDs of relationships this object participates in or evidences."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    """Principals (usernames) allowed to see this object."""

    allowed_roles: list[str] = Field(default_factory=list)
    """Roles allowed to see this object, checked against the caller's
    roles at retrieval time (see governance/policies.py). Empty means no
    role-based grant — visibility then depends only on `permissions` and
    the "no restrictions = public" default."""

    tenant_id: str | None = None
    """Optional tenant/organization scope. When set, only retrieval
    calls for the same tenant_id return this object — see
    `governance/permissions.py: filter_by_tenant`."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None

    # --- Quality signals, used by ranking and the compiler ---
    freshness: float = 1.0
    confidence: float = 1.0
    trust: float = 1.0

    def is_visible_to(self, principal: str, roles: list[str] | None = None) -> bool:
        """No permissions or allowed_roles recorded means "public within
        the tenant". Otherwise visible if the principal is explicitly
        allow-listed, or holds any of the allowed roles."""
        if not self.permissions and not self.allowed_roles:
            return True
        if principal in self.permissions:
            return True
        return bool(roles and self.allowed_roles and set(roles) & set(self.allowed_roles))
