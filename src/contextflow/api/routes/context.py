from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from contextflow.api.schemas.requests import ContextPackRequest, SearchRequest
from contextflow.auth.fastapi_deps import require_principal

router = APIRouter()


@router.post("/search")
def search(
    request: Request, body: SearchRequest, principal: str = Depends(require_principal)
) -> list[dict]:
    engine = request.app.state.engine
    results = engine.retrieve(body.query, limit=body.limit, principal=principal)
    request.app.state.audit_log.record(
        principal, "search", {"query": body.query, "result_count": len(results)}
    )
    return [obj.model_dump(mode="json") for obj in results]


@router.post("/context-pack")
def context_pack(
    request: Request, body: ContextPackRequest, principal: str = Depends(require_principal)
) -> dict:
    engine = request.app.state.engine
    pack = engine.context_pack(
        task=body.task,
        entity=body.entity,
        max_tokens=body.max_tokens,
        principal=principal,
    )
    request.app.state.audit_log.record(
        principal, "context_pack", {"task": body.task, "entity": body.entity}
    )
    return pack.model_dump(mode="json")
