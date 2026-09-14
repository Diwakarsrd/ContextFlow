import httpx

from contextflow.connectors.github.connector import GitHubConnector


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/acme/widgets/issues":
            page = request.url.params.get("page", "1")
            if page == "1":
                return httpx.Response(
                    200,
                    json=[
                        {
                            "number": 1,
                            "title": "Bug: login fails",
                            "body": "Steps to reproduce...",
                            "html_url": "https://github.com/acme/widgets/issues/1",
                            "user": {"login": "alice"},
                            "state": "open",
                            "updated_at": "2026-01-01T00:00:00Z",
                        }
                    ],
                )
            return httpx.Response(200, json=[])
        if request.url.path == "/repos/acme/widgets/readme":
            return httpx.Response(
                200,
                json={
                    "content": "IyBXaWRnZXRzXG5BIGdyZWF0IHByb2plY3Qu",  # base64 "# Widgets\nA great project."
                    "html_url": "https://github.com/acme/widgets#readme",
                },
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_github_connector_fetch_and_normalize():
    connector = GitHubConnector(config={"token": "fake", "repos": ["acme/widgets"]})
    connector.authenticate()
    connector._client = httpx.Client(base_url="https://api.github.com", transport=_mock_transport())

    raw_records = list(connector.fetch("acme/widgets"))
    kinds = {r["kind"] for r in raw_records}
    assert kinds == {"issue", "readme"}

    objects = [connector.normalize(r) for r in raw_records]
    issue_obj = next(o for o in objects if o.metadata["kind"] == "issue")
    assert issue_obj.type == "ticket"
    assert "login fails" in issue_obj.content
    assert issue_obj.metadata["author"] == "alice"

    readme_obj = next(o for o in objects if o.metadata["kind"] == "readme")
    assert readme_obj.type == "document"
    assert "great project" in readme_obj.content


def test_full_engine_sync_and_retrieve_end_to_end():
    """Exercises the real Connector.sync() -> ContextEngine.ingest() path.
    sync() calls authenticate() itself, so the mock transport has to be
    installed there rather than only overriding _client after a manual
    authenticate() call — a gap the Slack connector's tests caught."""
    from contextflow.engine import ContextEngine

    connector = GitHubConnector(config={"token": "fake", "repos": ["acme/widgets"]})
    connector.authenticate = lambda: setattr(
        connector,
        "_client",
        httpx.Client(base_url="https://api.github.com", transport=_mock_transport()),
    )

    engine = ContextEngine()
    count = engine.sync(connector)
    assert count > 0

    results = engine.retrieve("login")
    assert any("login" in r.content.lower() for r in results)
