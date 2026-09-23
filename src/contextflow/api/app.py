"""FastAPI application factory for the ContextFlow REST API.

Run with:

    contextflow serve

or directly:

    uvicorn contextflow.api.app:app --reload

Authentication: every /v1 route requires `Authorization: Bearer <key>`
once keys are configured (see `contextflow auth create-key` or
$CONTEXTOS_API_KEYS). With no keys configured, the API runs in open mode
for local development only — see `auth/fastapi_deps.py`. Every request
is recorded in the audit log (`governance/audit.py`).
"""

from __future__ import annotations

from fastapi import FastAPI

from contextflow.api.routes import context as context_routes
from contextflow.api.routes import governance as governance_routes
from contextflow.api.routes import memory as memory_routes
from contextflow.api.routes import trace as trace_routes
from contextflow.api.routes import webhooks as webhook_routes
from contextflow.auth.api_keys import APIKeyStore
from contextflow.auth.rate_limit import RateLimiter
from contextflow.engine import ContextEngine
from contextflow.governance.audit import AuditLog
from contextflow.governance.policies import PolicyEngine
from contextflow.memory.store import MemoryStore


def create_app(
    engine: ContextEngine | None = None,
    api_key_store: APIKeyStore | None = None,
    audit_log: AuditLog | None = None,
    rate_limiter: RateLimiter | None = None,
    memory_store: MemoryStore | None = None,
) -> FastAPI:
    app = FastAPI(
        title="ContextFlow API",
        description="REST API for the ContextFlow context engine.",
        version="0.1.0",
    )
    app.state.engine = engine or ContextEngine()
    app.state.api_key_store = api_key_store or APIKeyStore.from_env_and_file()
    app.state.audit_log = audit_log or AuditLog()
    app.state.rate_limiter = rate_limiter or RateLimiter()
    app.state.memory_store = memory_store or MemoryStore()
    if app.state.engine.policy_engine is None:
        app.state.engine.policy_engine = PolicyEngine()
    app.include_router(context_routes.router, prefix="/v1", tags=["context"])
    app.include_router(trace_routes.router, prefix="/v1", tags=["trace"])
    app.include_router(memory_routes.router, prefix="/v1", tags=["memory"])
    app.include_router(governance_routes.router, prefix="/v1/governance", tags=["governance"])
    app.include_router(webhook_routes.router, prefix="/v1/webhooks", tags=["webhooks"])

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
