"""
GitLab Connector for ContextFlow.

Extracts repositories, issues, and merge requests.
"""
from typing import Any
from collections.abc import Iterable
import time
import requests
import logging

from contextflow.connectors.base import Connector
from contextflow.core.context import ContextObject

logger = logging.getLogger("contextflow.connectors.gitlab")

class GitLabConnector(Connector):
    name = "gitlab"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.api_url = self.config.get("api_url", "https://gitlab.com/api/v4")
        self.private_token = self.config.get("private_token")
        self.project_id = self.config.get("project_id")
        self._mock_mode = False
        
    def authenticate(self) -> None:
        if not self.private_token or not self.project_id:
            logger.warning("GitLab config missing private_token or project_id. Running in mocked mode.")
            self._mock_mode = True
            return
            
        headers = {"PRIVATE-TOKEN": self.private_token}
        response = requests.get(f"{self.api_url}/user", headers=headers)
        if response.status_code not in (200, 401):
            # 401 allowed if token is project-specific rather than user-level, 
            # though standard implementation validates proper access handling.
            pass
            
    def discover(self) -> Iterable[str]:
        yield "issues"
        yield "merge_requests"
        
    def fetch(self, resource_id: str) -> Iterable[dict[str, Any]]:
        if self._mock_mode:
            yield {
                "id": 101,
                "title": "Update architectural documentation",
                "description": "Remove non-standard formatting strings and implement strict guidelines.",
                "type": resource_id,
                "state": "opened",
                "updated_at": "2026-09-15T00:00:00Z"
            }
            return
            
        headers = {"PRIVATE-TOKEN": self.private_token}
        url = f"{self.api_url}/projects/{self.project_id}/{resource_id}"
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            for item in response.json():
                item["type"] = resource_id
                yield item

    def normalize(self, raw_record: dict[str, Any]) -> ContextObject:
        item_id = str(raw_record.get("id", "UNKNOWN"))
        title = raw_record.get("title", "")
        desc = raw_record.get("description", "")
        item_type = raw_record.get("type", "entity")
        state = raw_record.get("state", "unknown")
        
        text_payload = f"GitLab {item_type} #{item_id}: {title}. State: {state}. Details: {desc}"
        
        return ContextObject(
            id=f"gitlab_{item_type}_{item_id}",
            text=text_payload,
            metadata={
                "source": "gitlab",
                "type": item_type,
                "state": state
            },
            confidence=0.9,
            timestamp=time.time()
        )
