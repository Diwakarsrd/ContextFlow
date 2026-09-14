"""TokenVerifier for running the MCP server over HTTP, backed by the
same APIKeyStore as the REST API — one set of keys, one set of
principals, for both surfaces.

Only relevant for `contextflow mcp --transport http`. Over stdio (the
default transport, `contextflow mcp`), the MCP server is a local
subprocess talking over a pipe to whatever spawned it — the trust
boundary is "who can run this process," the same as any local CLI tool,
so no additional token check applies there.
"""

from __future__ import annotations

from mcp.server.auth.provider import AccessToken, TokenVerifier

from contextflow.auth.api_keys import APIKeyStore


class StaticAPIKeyVerifier(TokenVerifier):
    def __init__(self, store: APIKeyStore) -> None:
        self.store = store

    async def verify_token(self, token: str) -> AccessToken | None:
        principal = self.store.verify(token)
        if principal is None:
            return None
        return AccessToken(
            token=token, client_id=principal, scopes=["contextflow"], subject=principal
        )
