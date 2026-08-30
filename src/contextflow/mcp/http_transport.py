"""Runs the MCP server over streamable HTTP with real Bearer-token auth,
using the mcp package's own `BearerAuthBackend` / `RequireAuthMiddleware`
(no OAuth authorization server required — just the same static API keys
the REST API uses).

Only relevant for `contextflow mcp --transport http`. The default stdio
transport needs no additional auth — see `auth/mcp_token_verifier.py`
for why.
"""

from __future__ import annotations

import logging

from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend, RequireAuthMiddleware
from mcp.server.mcpserver import MCPServer
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.types import ASGIApp

from contextflow.auth.api_keys import APIKeyStore
from contextflow.auth.mcp_token_verifier import StaticAPIKeyVerifier

logger = logging.getLogger("contextflow.mcp.http")


def build_http_app(server: MCPServer, api_key_store: APIKeyStore) -> ASGIApp:
    inner: ASGIApp = server.streamable_http_app()

    if not api_key_store.is_configured():
        logger.warning(
            "CONTEXTOS_API_KEYS is not set — the MCP HTTP server is running with NO "
            "authentication. This is only appropriate for local development. Run "
            "`contextflow auth create-key` before exposing this beyond localhost."
        )
        return inner

    verifier = StaticAPIKeyVerifier(api_key_store)
    authenticated: ASGIApp = AuthenticationMiddleware(inner, backend=BearerAuthBackend(verifier))
    return RequireAuthMiddleware(authenticated, required_scopes=["contextflow"])


def run_http(server: MCPServer, api_key_store: APIKeyStore, host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn

    app = build_http_app(server, api_key_store)
    uvicorn.run(app, host=host, port=port)
