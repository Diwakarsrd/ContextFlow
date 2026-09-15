from __future__ import annotations

from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    # NOTE: no `principal` field. Identity comes from the authenticated
    # API key (see auth/fastapi_deps.py) — a client-supplied principal in
    # the body would let any caller claim to be anyone.


class ContextPackRequest(BaseModel):
    task: str
    entity: str | None = None
    max_tokens: int = 3000


class TraceRequest(BaseModel):
    query: str
    limit: int = 10


class MemoryRememberRequest(BaseModel):
    scope: str
    scope_id: str
    fact: str
    metadata: dict | None = None


class MemoryRecallRequest(BaseModel):
    scope: str
    scope_id: str
    query: str | None = None
    limit: int = 10


class AssignRoleRequest(BaseModel):
    principal: str
    role: str


class RevokeRoleRequest(BaseModel):
    principal: str
    role: str
