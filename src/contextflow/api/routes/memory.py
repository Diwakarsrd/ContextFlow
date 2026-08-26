from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from contextflow.api.schemas.requests import MemoryRecallRequest, MemoryRememberRequest
from contextflow.auth.fastapi_deps import require_principal

router = APIRouter()


@router.post("/memory/remember")
def memory_remember(
    request: Request, body: MemoryRememberRequest, principal: str = Depends(require_principal)
) -> dict:
    store = request.app.state.memory_store
    entry_id = store.remember(body.scope, body.scope_id, body.fact, body.metadata)
    request.app.state.audit_log.record(
        principal, "memory_remember", {"scope": body.scope, "scope_id": body.scope_id}
    )
    return {"id": entry_id}


@router.post("/memory/recall")
def memory_recall(
    request: Request, body: MemoryRecallRequest, principal: str = Depends(require_principal)
) -> list[dict]:
    store = request.app.state.memory_store
    entries = store.recall(body.scope, body.scope_id, body.query, body.limit)
    request.app.state.audit_log.record(
        principal, "memory_recall", {"scope": body.scope, "scope_id": body.scope_id}
    )
    return [
        {"id": e.id, "content": e.content, "metadata": e.metadata, "created_at": e.created_at}
        for e in entries
    ]
