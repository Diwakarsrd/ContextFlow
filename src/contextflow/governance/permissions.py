"""Permission- and tenant-aware retrieval filtering: applied BEFORE
ranking/compilation, not after. See ARCHITECTURE.md's "Design
principles".
"""

from __future__ import annotations

from contextflow.core.context import ContextObject
from contextflow.governance.policies import PolicyEngine


def filter_visible(
    objects: list[ContextObject],
    principal: str,
    policy_engine: PolicyEngine | None = None,
) -> list[ContextObject]:
    if policy_engine is None:
        # No RBAC configured — fall back to permissions-only visibility
        # (ContextObject.is_visible_to with no roles).
        return [obj for obj in objects if obj.is_visible_to(principal)]

    roles = policy_engine.roles_for(principal)
    return [
        obj
        for obj in objects
        if policy_engine.can_read(principal, obj.allowed_roles, obj.permissions)
        or obj.is_visible_to(principal, roles)
    ]


def filter_by_tenant(objects: list[ContextObject], tenant_id: str | None) -> list[ContextObject]:
    """Multi-tenant isolation: an object with no tenant_id is visible to
    every tenant (shared/global content); an object with a tenant_id is
    only visible to retrieval calls scoped to that same tenant."""
    if tenant_id is None:
        return [obj for obj in objects if obj.tenant_id is None]
    return [obj for obj in objects if obj.tenant_id in (None, tenant_id)]
