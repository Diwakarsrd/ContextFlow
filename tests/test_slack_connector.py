import httpx
import pytest

from contextflow.connectors.slack.connector import SlackAPIError, SlackConnector


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        params = dict(request.url.params)

        if path == "/api/conversations.list":
            cursor = params.get("cursor", "")
            if not cursor:
                return httpx.Response(
                    200,
                    json={
                        "ok": True,
                        "channels": [{"id": "C_GENERAL", "name": "general"}],
                        "response_metadata": {"next_cursor": "page2"},
                    },
                )
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "channels": [{"id": "C_PAYMENTS", "name": "eng-payments"}],
                    "response_metadata": {"next_cursor": ""},
                },
            )

        if path == "/api/conversations.history":
            channel = params.get("channel")
            if channel == "C_PAYMENTS":
                return httpx.Response(
                    200,
                    json={
                        "ok": True,
                        "messages": [
                            {
                                "user": "U1",
                                "text": "Stripe integration is done",
                                "ts": "100.001",
                                "reply_count": 1,
                            },
                            {"user": "U2", "text": "Nice work", "ts": "100.002"},
                        ],
                        "response_metadata": {"next_cursor": ""},
                    },
                )
            return httpx.Response(200, json={"ok": True, "messages": [], "response_metadata": {}})

        if path == "/api/conversations.replies":
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "messages": [
                        {"user": "U1", "text": "Stripe integration is done", "ts": "100.001"},
                        {"user": "U3", "text": "Does it handle refunds?", "ts": "100.003"},
                    ],
                },
            )

        if path == "/api/broken.method":
            return httpx.Response(200, json={"ok": False, "error": "invalid_auth"})

        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _connector(**config) -> SlackConnector:
    connector = SlackConnector(config={"token": "xoxb-fake", **config})
    connector.authenticate()
    connector._client = httpx.Client(base_url="https://slack.com/api", transport=_mock_transport())
    return connector


def test_discover_resolves_channel_names_with_pagination():
    connector = _connector(channel_names=["general", "eng-payments"])
    channels = list(connector.discover())
    assert set(channels) == {"C_GENERAL", "C_PAYMENTS"}


def test_discover_requires_channels_or_names():
    connector = _connector()
    with pytest.raises(RuntimeError):
        list(connector.discover())


def test_fetch_includes_thread_replies_but_not_duplicate_parent():
    connector = _connector(channels=["C_PAYMENTS"])
    records = list(connector.fetch("C_PAYMENTS"))

    texts = [r["text"] for r in records]
    assert "Stripe integration is done" in texts
    assert texts.count("Stripe integration is done") == 1  # parent not duplicated via thread fetch
    assert "Does it handle refunds?" in texts
    assert "Nice work" in texts

    reply = next(r for r in records if r["text"] == "Does it handle refunds?")
    assert reply["is_thread_reply"] is True
    assert reply["thread_ts"] == "100.001"


def test_fetch_respects_max_messages_per_channel():
    connector = _connector(
        channels=["C_PAYMENTS"], max_messages_per_channel=1, include_threads=False
    )
    records = list(connector.fetch("C_PAYMENTS"))
    assert len(records) == 1


def test_normalize_builds_message_context_object():
    connector = _connector(channels=["C_PAYMENTS"])
    obj = connector.normalize(
        {"channel": "C_PAYMENTS", "user": "U1", "text": "hello", "ts": "1", "thread_ts": None}
    )
    assert obj.type == "message"
    assert obj.content == "hello"
    assert obj.metadata["channel"] == "C_PAYMENTS"


def test_slack_api_error_raised_on_not_ok_response():
    connector = _connector()
    with pytest.raises(SlackAPIError):
        connector._call("broken.method")


def test_full_engine_sync_and_retrieve_end_to_end():
    """Exercises the real Connector.sync() -> ContextEngine.ingest() path,
    not just fetch()/normalize() in isolation — sync() calls
    authenticate() itself, so the mock has to be installed there."""
    from contextflow.engine import ContextEngine

    connector = SlackConnector(config={"token": "xoxb-fake", "channels": ["C_PAYMENTS"]})
    connector.authenticate = lambda: setattr(
        connector,
        "_client",
        httpx.Client(base_url="https://slack.com/api", transport=_mock_transport()),
    )

    engine = ContextEngine()
    count = engine.sync(connector)
    assert count > 0

    results = engine.retrieve("stripe")
    assert any("stripe" in r.content.lower() for r in results)
