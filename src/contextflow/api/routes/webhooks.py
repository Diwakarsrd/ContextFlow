from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException

from contextflow.api.schemas.requests import WebhookPayloadRequest
from contextflow.auth.fastapi_deps import require_principal
from contextflow.core.context import ContextObject

router = APIRouter()

@router.post("/ingest")
def handle_webhook_ingest(
    request: Request, body: WebhookPayloadRequest, principal: str = Depends(require_principal)
) -> dict:
    """ Phase 8 Real-Time Event Bus endpoint.
    Accepts raw payloads from external CDCs or systems (Slack/Jira webhooks),
    converts to a ContextObject natively, and immediately pipelines into the engine.
    """
    engine = request.app.state.engine
    
    # Map the incoming webhook event to the internal ContextObject graph schema
    obj = ContextObject(
        content=body.content,
        source=body.source,
        metadata=body.metadata or {},
        tenant_id=body.tenant_id
    )
    
    # Process the object (runs through PII redaction, LLM extraction, and Vector graph indexing)
    try:
        processed_count = engine.ingest([obj])
        request.app.state.audit_log.record(
            principal, "webhook_ingest", {"source": body.source, "tenant_id": body.tenant_id}
        )
        return {"status": "success", "indexed_chunks": processed_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Engine indexing failure: {str(e)}")
