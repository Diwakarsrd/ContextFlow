"""RBAC policy engine: maps principals to roles and evaluates access.

This is deliberately simple — role membership, no ABAC condition
language, no scoped permissions per action. It's real (persisted,
tested, wired into retrieval), not a mock — but full ABAC/condition-based
policies remain a v0.3+ target, see ROADMAP.md.
"""

from __future__ import annotations

import json
from pathlib import Path


class RoleStore:
    """Persists principal -> roles assignments. File-backed by default
    (`.contextflow/roles.json`), matching the rest of the local-first
    workspace — see `storage/local_persistent.py` for the same pattern.
    """

    def __init__(self, path: str = ".contextflow/roles.json") -> None:
        self.path = Path(path)
        self._roles: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            self._roles = json.loads(self.path.read_text() or "{}")

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._roles, indent=2))

    def assign(self, principal: str, role: str) -> None:
        roles = self._roles.setdefault(principal, [])
        if role not in roles:
            roles.append(role)
        self._save()

    def revoke(self, principal: str, role: str) -> None:
        if principal in self._roles and role in self._roles[principal]:
            self._roles[principal].remove(role)
            self._save()

    def roles_for(self, principal: str) -> list[str]:
        return list(self._roles.get(principal, []))


class PolicyEngine:
    """Evaluates whether a principal can perform an action, given their
    roles. v0.1 supports a single action ("read") and role membership
    only — see docstring above for what's deliberately out of scope."""

    def __init__(self, role_store: RoleStore | None = None) -> None:
        self.role_store = role_store or RoleStore()

    def roles_for(self, principal: str) -> list[str]:
        return self.role_store.roles_for(principal)

    def can_read(self, principal: str, allowed_roles: list[str], permissions: list[str]) -> bool:
        if not allowed_roles and not permissions:
            return True  # unrestricted object
        if principal in permissions:
            return True
        principal_roles = set(self.roles_for(principal))
        return bool(principal_roles & set(allowed_roles))
