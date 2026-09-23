"""
Jira Connector for ContextFlow.

Extracts Epics, Tasks, and Bugs from Jira workspaces to provide agent metadata.
"""

import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

import httpx

from contextflow.connectors.base import Connector
from contextflow.core.context import ContextObject

logger = logging.getLogger("contextflow.connectors.jira")


class JiraConnector(Connector):
    name = "jira"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.domain = self.config.get("domain")
        self.email = self.config.get("email")
        self.api_token = self.config.get("api_token")
        self.jql_filter = self.config.get("jql_filter", "ORDER BY updated DESC")
        self._mock_mode = False

    def authenticate(self) -> None:
        if not self.domain or not self.email or not self.api_token:
            logger.warning(
                "Jira config missing domain, email, or api_token. Running in mocked demo mode."
            )
            self._mock_mode = True
            return

        self._mock_mode = False
        url = f"https://{self.domain}/rest/api/3/myself"
        response = httpx.get(url, auth=(str(self.email), str(self.api_token)))
        if response.status_code != 200:
            raise ValueError(f"Failed to authenticate with Jira: {response.text}")

    def discover(self) -> Iterable[str]:
        yield str(self.jql_filter)

    def fetch(self, resource_id: str) -> Iterable[dict[str, Any]]:
        if self._mock_mode:
            yield {
                "key": "ENG-101",
                "fields": {
                    "summary": "Fix memory leak in ContextEngine",
                    "description": "Agent memory is expanding infinitely due to lack of time decay.",
                    "assignee": {"displayName": "John Doe"},
                    "updated": "2026-09-15T00:00:00.000+0000",
                },
            }
            return

        url = f"https://{self.domain}/rest/api/3/search"
        params: dict[str, str | int] = {"jql": resource_id, "maxResults": 50}
        response = httpx.get(url, auth=(str(self.email), str(self.api_token)), params=params)
        response.raise_for_status()

        data = response.json()
        yield from data.get("issues", [])

    def normalize(self, raw_record: dict[str, Any]) -> ContextObject:
        key = str(raw_record.get("key", "UNKNOWN"))
        fields = raw_record.get("fields", {})
        summary = fields.get("summary", "")
        desc = fields.get("description", "")
        assignee = fields.get("assignee", {}).get("displayName", "Unassigned")
        updated = str(fields.get("updated", ""))

        text_payload = f"Jira Ticket {key}: {summary}. Assigned to {assignee}. Description: {desc}"

        confidence = 0.9 if assignee != "Unassigned" else 0.5

        try:
            dt_created = datetime.fromisoformat(
                updated.replace("Z", "+00:00").replace("+0000", "+00:00")
            )
        except (ValueError, TypeError):
            dt_created = datetime.now(timezone.utc)

        return ContextObject(
            id=f"jira_{key}",
            content=text_payload,
            source="jira",
            metadata={
                "source": "jira",
                "assignee": assignee,
                "project": key.split("-")[0] if "-" in key else "global",
                "last_updated": updated,
            },
            confidence=confidence,
            created_at=dt_created,
        )
