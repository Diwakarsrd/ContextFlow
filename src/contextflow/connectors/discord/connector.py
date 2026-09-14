"""
Discord Connector for ContextFlow.

Extracts server messages and threads to provide conversational context.
"""

import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

import requests

from contextflow.connectors.base import Connector
from contextflow.core.context import ContextObject

logger = logging.getLogger("contextflow.connectors.discord")


class DiscordConnector(Connector):
    name = "discord"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.bot_token = self.config.get("bot_token")
        self.target_channels = self.config.get("channels", [])
        self._mock_mode = False

    def authenticate(self) -> None:
        if not self.bot_token:
            logger.warning("Discord config missing bot_token. Running in mocked demo mode.")
            self._mock_mode = True
            return

        headers = {"Authorization": f"Bot {self.bot_token}"}
        response = requests.get("https://discord.com/api/v10/users/@me", headers=headers)
        if response.status_code != 200:
            raise ValueError(f"Failed to authenticate with Discord API: {response.status_code}")

    def discover(self) -> Iterable[str]:
        if self._mock_mode:
            yield "mock_channel"
        else:
            yield from self.target_channels

    def fetch(self, resource_id: str) -> Iterable[dict[str, Any]]:
        if self._mock_mode:
            yield {
                "id": "msg_9999",
                "content": "Discussing the new context pipeline architecture in the general channel.",
                "author": {"username": "DeveloperOne"},
                "timestamp": "2026-09-15T00:00:00.000000+00:00",
            }
            return

        url = f"https://discord.com/api/v10/channels/{resource_id}/messages?limit=50"
        headers = {"Authorization": f"Bot {self.bot_token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        yield from response.json()

    def normalize(self, raw_record: dict[str, Any]) -> ContextObject:
        msg_id = str(raw_record.get("id", "UNKNOWN"))
        content = raw_record.get("content", "")
        author = raw_record.get("author", {}).get("username", "UnknownUser")
        timestamp_str = str(raw_record.get("timestamp", ""))

        text_payload = f"Discord Message from {author}: {content}"

        try:
            dt_created = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            dt_created = datetime.now(timezone.utc)

        return ContextObject(
            id=f"discord_{msg_id}",
            content=text_payload,
            source="discord",
            metadata={"source": "discord", "author": author, "recorded_at": timestamp_str},
            confidence=0.8,
            created_at=dt_created,
        )
