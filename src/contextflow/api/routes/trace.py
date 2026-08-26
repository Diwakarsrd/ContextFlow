from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from contextflow.api.schemas.requests import TraceRequest
from contextflow.auth.fastapi_deps import require_principal

router = APIRouter()


@router.post("/trace")
def trace(
    request: Request, body: TraceRequest, principal: str = Depends(require_principal)
) -> dict:
    engine = request.app.state.engine
    _, trace_obj = engine.retrieve_with_trace(body.query, limit=body.limit, principal=principal)
    request.app.state.audit_log.record(principal, "trace", {"query": body.query})
    return trace_obj.to_dict()
