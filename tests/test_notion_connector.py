import httpx
import pytest

from contextflow.connectors.notion.connector import (
    NotionAPIError,
    NotionConnector,
    _extract_plain_text,
    _extract_property_text,
)


def _rich_text(text: str) -> list[dict]:
    return [{"plain_text": text}]


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method

        if path == "/v1/search" and method == "POST":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {"object": "page", "id": "PAGE1"},
                        {"object": "database", "id": "DB1"},
                    ],
                    "has_more": False,
                    "next_cursor": None,
                },
            )

        if path == "/v1/pages/PAGE1" and method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": "PAGE1",
                    "url": "https://notion.so/PAGE1",
                    "properties": {
                        "Name": {"type": "title", "title": _rich_text("Payments Architecture")}
                    },
                },
            )

        if path == "/v1/blocks/PAGE1/children" and method == "GET":
            cursor = request.url.params.get("start_cursor")
            if not cursor:
                return httpx.Response(
                    200,
                    json={
                        "results": [
                            {
                                "type": "paragraph",
                                "paragraph": {"rich_text": _rich_text("Stripe was selected.")},
                            },
                            {
                                "type": "heading_1",
                                "heading_1": {"rich_text": _rich_text("Timeline")},
                            },
                        ],
                        "has_more": True,
                        "next_cursor": "page2",
                    },
                )
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {"rich_text": _rich_text("Migration in Q4")},
                        },
                        {"type": "divider", "divider": {}},  # no rich_text -> should be skipped
                    ],
                    "has_more": False,
                    "next_cursor": None,
                },
            )

        if path == "/v1/databases/DB1/query" and method == "POST":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "ROW1",
                            "url": "https://notion.so/ROW1",
                            "properties": {
                                "Name": {"type": "title", "title": _rich_text("Acme Corp")},
                                "Plan": {"type": "select", "select": {"name": "Enterprise"}},
                                "Tags": {
                                    "type": "multi_select",
                                    "multi_select": [{"name": "priority"}, {"name": "renewal"}],
                                },
                            },
                        }
                    ],
                    "has_more": False,
                    "next_cursor": None,
                },
            )

        if path == "/v1/broken":
            return httpx.Response(404, text="not found")

        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _connector(**config) -> NotionConnector:
    connector = NotionConnector(config={"token": "secret_fake", **config})
    connector.authenticate()
    connector._client = httpx.Client(
        base_url="https://api.notion.com/v1",
        transport=_mock_transport(),
        headers=connector._client.headers,
    )
    return connector


def test_extract_plain_text_handles_various_block_types():
    assert (
        _extract_plain_text({"type": "paragraph", "paragraph": {"rich_text": _rich_text("hi")}})
        == "hi"
    )
    assert _extract_plain_text({"type": "divider", "divider": {}}) == ""
    assert _extract_plain_text({}) == ""


def test_extract_property_text_handles_common_types():
    assert (
        _extract_property_text({"type": "select", "select": {"name": "Enterprise"}}) == "Enterprise"
    )
    assert _extract_property_text({"type": "select", "select": None}) == ""
    assert (
        _extract_property_text(
            {"type": "multi_select", "multi_select": [{"name": "a"}, {"name": "b"}]}
        )
        == "a, b"
    )
    assert (
        _extract_property_text({"type": "relation"}) == ""
    )  # unrecognized type -> skipped, not guessed


def test_discover_via_search_finds_pages_and_databases():
    connector = _connector()
    resources = list(connector.discover())
    assert set(resources) == {"page:PAGE1", "database:DB1"}


def test_discover_uses_explicit_ids_without_calling_search():
    connector = _connector(page_ids=["EXPLICIT_PAGE"], discover_via_search=True)
    resources = list(connector.discover())
    assert resources == ["page:EXPLICIT_PAGE"]


def test_fetch_page_paginates_blocks_and_skips_textless_blocks():
    connector = _connector()
    records = list(connector.fetch("page:PAGE1"))
    assert len(records) == 1
    record = records[0]
    assert record["title"] == "Payments Architecture"
    assert "Stripe was selected." in record["text"]
    assert "Timeline" in record["text"]
    assert "Migration in Q4" in record["text"]


def test_fetch_database_extracts_row_properties():
    connector = _connector()
    records = list(connector.fetch("database:DB1"))
    assert len(records) == 1
    fields = records[0]["fields"]
    assert fields["Name"] == "Acme Corp"
    assert fields["Plan"] == "Enterprise"
    assert fields["Tags"] == "priority, renewal"


def test_normalize_page_and_database_row():
    connector = _connector()
    page_obj = connector.normalize(
        {"kind": "page", "id": "P1", "title": "Title", "text": "body text", "url": "u"}
    )
    assert page_obj.type == "document"
    assert "Title" in page_obj.content and "body text" in page_obj.content

    row_obj = connector.normalize(
        {
            "kind": "database_row",
            "id": "R1",
            "database_id": "DB1",
            "fields": {"Name": "Acme"},
            "url": "u",
        }
    )
    assert row_obj.type == "record"
    assert "Acme" in row_obj.content
    assert row_obj.metadata["field:Name"] == "Acme"


def test_notion_api_error_on_bad_status():
    connector = _connector()
    with pytest.raises(NotionAPIError):
        connector._get("/broken")


def test_full_engine_sync_and_retrieve_end_to_end():
    from contextflow.engine import ContextEngine

    connector = NotionConnector(config={"token": "secret_fake"})
    headers = {
        "Authorization": "Bearer secret_fake",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    connector.authenticate = lambda: setattr(
        connector,
        "_client",
        httpx.Client(
            base_url="https://api.notion.com/v1", headers=headers, transport=_mock_transport()
        ),
    )

    engine = ContextEngine()
    count = engine.sync(connector)
    assert count > 0

    results = engine.retrieve("stripe")
    assert any("stripe" in r.content.lower() for r in results)
