"""Notion connector: syncs pages (as documents, with block content
flattened to plain text) and database rows (as records).

Config:
    token: Notion integration secret (defaults to $NOTION_API_KEY). The
           integration must be explicitly shared with each page/database
           you want to sync — Notion doesn't expose anything to an
           integration by default.
    page_ids: list of specific page IDs to sync
    database_ids: list of specific database IDs to sync (each row
           becomes one ContextObject)
    discover_via_search: if True and neither of the above is given, use
           Notion's `/v1/search` endpoint to discover everything shared
           with the integration (default True)
    max_blocks_per_page: cap on child blocks fetched per page (default 500)
    max_rows_per_database: cap on rows fetched per database (default 500)

Not live-tested against a real Notion workspace — api.notion.com isn't
reachable from this project's development sandbox. Tested against a
mocked Notion API instead (`tests/test_notion_connector.py`), which
proves the request/pagination/normalization logic but not real-world
behavior (real block-type coverage, real rate limits, real workspace
structure). Treat this the way you'd treat any integration you haven't
personally run against production — see CONTRIBUTING.md if you do and
want to report back or improve it.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

import httpx

from contextflow.connectors.base import Connector
from contextflow.core.context import ContextObject

_API_BASE = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


class NotionAPIError(RuntimeError):
    pass


def _extract_plain_text(block: dict[str, Any]) -> str:
    """Notion blocks store text under a type-specific key (paragraph,
    heading_1, bulleted_list_item, to_do, quote, code, ...), each holding
    a `rich_text` array of spans with a `plain_text` field. This pulls
    text out regardless of block type rather than special-casing each
    one — it will miss anything Notion adds a new block type for without
    a `rich_text` array (e.g. embeds, files), which is an acceptable
    v0.1 gap."""
    block_type = block.get("type")
    if not block_type:
        return ""
    type_data = block.get(block_type, {})
    rich_text = type_data.get("rich_text", [])
    return "".join(span.get("plain_text", "") for span in rich_text)


def _extract_property_text(prop: dict[str, Any]) -> str:
    """Best-effort plain-text extraction for a database row's property
    value, covering the common property types. Property types this
    doesn't recognize (relations, rollups, formulas, files) are skipped
    rather than guessed at."""
    prop_type = prop.get("type")
    if prop_type in ("title", "rich_text"):
        return "".join(span.get("plain_text", "") for span in prop.get(prop_type, []))
    if prop_type == "select":
        value = prop.get("select")
        return value.get("name", "") if value else ""
    if prop_type == "multi_select":
        return ", ".join(v.get("name", "") for v in prop.get("multi_select", []))
    if prop_type in ("number", "checkbox", "url", "email", "phone_number"):
        return str(prop.get(prop_type, ""))
    if prop_type == "date":
        date = prop.get("date")
        return date.get("start", "") if date else ""
    return ""


class NotionConnector(Connector):
    name = "notion"

    def authenticate(self) -> None:
        token = self.config.get("token") or os.environ.get("NOTION_API_KEY")
        if not token:
            raise RuntimeError("NotionConnector requires config['token'] or $NOTION_API_KEY")
        self._client = httpx.Client(
            base_url=_API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": _NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def _post(self, path: str, **json: Any) -> dict[str, Any]:
        resp = self._client.post(path, json=json)
        if resp.status_code >= 400:
            raise NotionAPIError(f"Notion API error calling {path}: {resp.status_code} {resp.text}")
        return resp.json()

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        resp = self._client.get(path, params=params)
        if resp.status_code >= 400:
            raise NotionAPIError(f"Notion API error calling {path}: {resp.status_code} {resp.text}")
        return resp.json()

    def _discover_via_search(self) -> tuple[list[str], list[str]]:
        page_ids, database_ids = [], []
        cursor = None
        while True:
            body: dict[str, Any] = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            data = self._post("/search", **body)
            for result in data.get("results", []):
                if result["object"] == "page":
                    page_ids.append(result["id"])
                elif result["object"] == "database":
                    database_ids.append(result["id"])
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        return page_ids, database_ids

    def discover(self) -> Iterable[str]:
        page_ids = list(self.config.get("page_ids", []))
        database_ids = list(self.config.get("database_ids", []))

        if not page_ids and not database_ids and self.config.get("discover_via_search", True):
            page_ids, database_ids = self._discover_via_search()

        if not page_ids and not database_ids:
            raise RuntimeError(
                "NotionConnector found nothing to sync — check page_ids/database_ids, "
                "or that the integration has been shared with pages in the workspace"
            )

        return [f"page:{pid}" for pid in page_ids] + [f"database:{did}" for did in database_ids]

    def fetch(self, resource_id: str) -> Iterable[dict[str, Any]]:
        kind, _, resource = resource_id.partition(":")
        if kind == "page":
            yield from self._fetch_page(resource)
        elif kind == "database":
            yield from self._fetch_database(resource)
        else:
            raise ValueError(f"Unknown Notion resource kind: {kind!r}")

    def _fetch_page(self, page_id: str) -> Iterable[dict[str, Any]]:
        page = self._get(f"/pages/{page_id}")
        title = ""
        for prop in page.get("properties", {}).values():
            if prop.get("type") == "title":
                title = "".join(span.get("plain_text", "") for span in prop.get("title", []))
                break

        max_blocks = self.config.get("max_blocks_per_page", 500)
        texts: list[str] = []
        cursor = None
        fetched = 0
        while fetched < max_blocks:
            params: dict[str, Any] = {"page_size": min(100, max_blocks - fetched)}
            if cursor:
                params["start_cursor"] = cursor
            data = self._get(f"/blocks/{page_id}/children", **params)
            blocks = data.get("results", [])
            for block in blocks:
                text = _extract_plain_text(block)
                if text:
                    texts.append(text)
            fetched += len(blocks)
            if not data.get("has_more") or not blocks:
                break
            cursor = data.get("next_cursor")

        yield {
            "kind": "page",
            "id": page_id,
            "title": title,
            "text": "\n".join(texts),
            "url": page.get("url"),
        }

    def _fetch_database(self, database_id: str) -> Iterable[dict[str, Any]]:
        max_rows = self.config.get("max_rows_per_database", 500)
        cursor = None
        fetched = 0
        while fetched < max_rows:
            body: dict[str, Any] = {"page_size": min(100, max_rows - fetched)}
            if cursor:
                body["start_cursor"] = cursor
            data = self._post(f"/databases/{database_id}/query", **body)
            rows = data.get("results", [])
            for row in rows:
                field_text = {
                    name: _extract_property_text(prop)
                    for name, prop in row.get("properties", {}).items()
                }
                yield {
                    "kind": "database_row",
                    "id": row["id"],
                    "database_id": database_id,
                    "fields": field_text,
                    "url": row.get("url"),
                }
            fetched += len(rows)
            if not data.get("has_more") or not rows:
                break
            cursor = data.get("next_cursor")

    def normalize(self, raw_record: dict[str, Any]) -> ContextObject:
        if raw_record["kind"] == "page":
            content = f"{raw_record['title']}\n\n{raw_record['text']}".strip()
            return ContextObject(
                type="document",
                content=content,
                source=self.name,
                metadata={"notion_id": raw_record["id"], "url": raw_record.get("url"), "kind": "page"},
            )

        fields = raw_record["fields"]
        content = " ".join(v for v in fields.values() if v) or str(fields)
        return ContextObject(
            type="record",
            content=content,
            source=self.name,
            metadata={
                "notion_id": raw_record["id"],
                "database_id": raw_record["database_id"],
                "url": raw_record.get("url"),
                "kind": "database_row",
                **{f"field:{k}": v for k, v in fields.items()},
            },
        )
