# Notion Connector

Syncs pages (block content flattened to plain text) and database rows
via the Notion API. Real implementation — see
`src/contextflow/connectors/notion/connector.py`.

```python
from contextflow.connectors.notion.connector import NotionConnector

connector = NotionConnector(config={
    "token": "secret_...",                # or $NOTION_API_KEY
    "page_ids": ["..."],                  # optional: specific pages
    "database_ids": ["..."],              # optional: specific databases
    "discover_via_search": True,           # default True: if neither of
                                            # the above is set, discover
                                            # everything shared with the
                                            # integration via /v1/search
    "max_blocks_per_page": 500,            # default 500
    "max_rows_per_database": 500,          # default 500
})

engine.sync(connector)
```

The integration must be **explicitly shared** with each page/database in
the Notion UI — Notion doesn't expose anything to an integration by
default, even with a valid token.

## What gets extracted

- **Pages** → one `ContextObject` per page: title + block text
  (paragraphs, headings, list items, quotes, etc. — anything with a
  `rich_text` array). Blocks without `rich_text` (dividers, embeds,
  files) are skipped, not guessed at.
- **Database rows** → one `ContextObject` per row, built from
  title/rich_text/select/multi_select/number/checkbox/url/email/phone/date
  properties. Relations, rollups, formulas, and files aren't extracted —
  a real gap, not an oversight; contributions welcome.

## Testing status

Tested against a **mocked** Notion API
(`tests/test_notion_connector.py`), including search-based discovery,
block pagination, database row pagination, and a full
`engine.sync()` → `engine.retrieve()` round trip.

**Not tested against a real Notion workspace.** `api.notion.com` isn't
reachable from this project's development environment. Real-world edge
cases (nested blocks/toggles, synced blocks, unusual property types,
actual rate limits) haven't been verified. If you run this against a
real workspace, consider contributing back what you find — see
CONTRIBUTING.md.
