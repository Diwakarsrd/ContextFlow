"""
Jira Connector for ContextFlow.

Extracts Epics, Tasks, and Bugs from Jira workspaces to provide agent metadata.
"""
from typing import Any
from collections.abc import Iterable
import time
import requests
import logging

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
        
    def authenticate(self) -> None:
        if not self.domain or not self.email or not self.api_token:
            logger.warning("Jira config missing domain, email, or api_token. Running in mocked demo mode.")
            self._mock_mode = True
            return
            
        self._mock_mode = False
        url = f"https://{self.domain}/rest/api/3/myself"
        response = requests.get(url, auth=(self.email, self.api_token))
        if response.status_code != 200:
            raise ValueError(f"Failed to authenticate with Jira: {response.text}")
            
    def discover(self) -> Iterable[str]:
        # In this connector, a "resource" is a JQL query execution block
        yield self.jql_filter
        
    def fetch(self, resource_id: str) -> Iterable[dict[str, Any]]:
        if self._mock_mode:
            yield {
                "key": "ENG-101",
                "fields": {
                    "summary": "Fix memory leak in ContextEngine",
                    "description": "Agent memory is expanding infinitely due to lack of time decay.",
                    "assignee": {"displayName": "John Doe"},
                    "updated": "2026-09-15T00:00:00.000+0000"
                }
            }
            return
            
        url = f"https://{self.domain}/rest/api/3/search"
        params = {"jql": resource_id, "maxResults": 50}
        response = requests.get(url, auth=(self.email, self.api_token), params=params)
        response.raise_for_status()
        
        data = response.json()
        yield from data.get("issues", [])

    def normalize(self, raw_record: dict[str, Any]) -> ContextObject:
        key = raw_record.get("key", "UNKNOWN")
        fields = raw_record.get("fields", {})
        summary = fields.get("summary", "")
        desc = fields.get("description", "")
        assignee = fields.get("assignee", {}).get("displayName", "Unassigned")
        updated = fields.get("updated", "")
        
        # Combine into a dense string for vector embedding
        text_payload = f"Jira Ticket {key}: {summary}. Assigned to {assignee}. Description: {desc}"
        
        # Assign contextual significance (trust/confidence)
        confidence = 0.9 if assignee != "Unassigned" else 0.5
        
        return ContextObject(
            id=f"jira_{key}",
            text=text_payload,
            metadata={
                "source": "jira",
                "assignee": assignee,
                "project": key.split("-")[0] if "-" in key else "global",
                "last_updated": updated
            },
            confidence=confidence,
            timestamp=time.time()
        )
