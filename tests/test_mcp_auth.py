from starlette.middleware.authentication import AuthenticationMiddleware

from contextflow.auth.api_keys import APIKeyStore
from contextflow.mcp.http_transport import build_http_app
from contextflow.mcp.server import build_server


def test_http_app_unwrapped_in_open_mode():
    server = build_server()
    app = build_http_app(server, APIKeyStore())
    # In open mode, no auth middleware wraps the app.
    assert not isinstance(app, AuthenticationMiddleware)


def test_http_app_wrapped_with_auth_when_keys_configured():
    server = build_server()
    store = APIKeyStore({"sk_test": "alice"})
    app = build_http_app(server, store)
    # RequireAuthMiddleware wraps AuthenticationMiddleware wraps the real app.
    assert hasattr(app, "app")
    assert isinstance(app.app, AuthenticationMiddleware)


def test_token_verifier_resolves_principal():
    import anyio

    from contextflow.auth.mcp_token_verifier import StaticAPIKeyVerifier

    store = APIKeyStore({"sk_test": "alice"})
    verifier = StaticAPIKeyVerifier(store)

    token = anyio.run(verifier.verify_token, "sk_test")
    assert token is not None
    assert token.subject == "alice"

    assert anyio.run(verifier.verify_token, "sk_wrong") is None
