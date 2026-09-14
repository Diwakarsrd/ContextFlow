"""Slack connector: syncs channel messages (and optionally thread
replies) via the Slack Web API.

Config:
    token: Slack bot token (defaults to $SLACK_BOT_TOKEN). Needs the
           `channels:history` and `channels:read` scopes at minimum
           (add `groups:history`/`groups:read` for private channels).
    channels: list of channel IDs to sync, e.g. ["C0123456789"]
    channel_names: list of channel names to resolve to IDs at sync time,
           e.g. ["general", "eng-payments"] — resolved via
           `conversations.list` and merged with `channels`
    include_threads: whether to also fetch replies in threads started in
           the synced channels (default True)
    max_messages_per_channel: cap per channel (default 200)

Not live-tested against a real Slack workspace — slack.com isn't
reachable from this project's development sandbox. Tested against a
mocked Slack Web API instead (`tests/test_slack_connector.py`), which
proves the request/pagination/normalization logic but not real-world
behavior (actual rate limits, real message formatting/mrkdwn edge
cases, real thread structures). Treat this the way you'd treat any
new integration you haven't run against production: verify against a
real workspace before depending on it — see CONTRIBUTING.md if you do
and want to report back or improve it.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

import httpx

from contextflow.connectors.base import Connector
from contextflow.core.context import ContextObject

_API_BASE = "https://slack.com/api"


class SlackAPIError(RuntimeError):
    pass


class SlackConnector(Connector):
    name = "slack"

    def authenticate(self) -> None:
        token = self.config.get("token") or os.environ.get("SLACK_BOT_TOKEN")
        if not token:
            raise RuntimeError("SlackConnector requires config['token'] or $SLACK_BOT_TOKEN")
        self._client = httpx.Client(
            base_url=_API_BASE,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    def _call(self, method: str, **params: Any) -> dict[str, Any]:
        resp = self._client.get(f"/{method}", params=params)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise SlackAPIError(f"Slack API error calling {method}: {data.get('error')}")
        return data

    def _resolve_channel_names(self, names: list[str]) -> list[str]:
        wanted = set(names)
        resolved: list[str] = []
        cursor = None
        while wanted:
            data = self._call(
                "conversations.list",
                limit=200,
                cursor=cursor,
                types="public_channel,private_channel",
            )
            for channel in data.get("channels", []):
                if channel.get("name") in wanted:
                    resolved.append(channel["id"])
                    wanted.discard(channel["name"])
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor or not wanted:
                break
        if wanted:
            raise RuntimeError(f"Could not resolve Slack channel name(s): {sorted(wanted)}")
        return resolved

    def discover(self) -> Iterable[str]:
        channels = list(self.config.get("channels", []))
        channel_names = self.config.get("channel_names", [])
        if channel_names:
            channels.extend(self._resolve_channel_names(channel_names))
        if not channels:
            raise RuntimeError(
                "SlackConnector requires config['channels'] and/or config['channel_names']"
            )
        return channels

    def fetch(self, resource_id: str) -> Iterable[dict[str, Any]]:
        max_messages = self.config.get("max_messages_per_channel", 200)
        include_threads = self.config.get("include_threads", True)
        fetched = 0
        cursor = None

        while fetched < max_messages:
            data = self._call(
                "conversations.history",
                channel=resource_id,
                limit=min(200, max_messages - fetched),
                cursor=cursor,
            )
            messages = data.get("messages", [])
            if not messages:
                break

            for message in messages:
                yield {
                    "channel": resource_id,
                    "user": message.get("user"),
                    "text": message.get("text", ""),
                    "ts": message.get("ts"),
                    "thread_ts": message.get("thread_ts"),
                    "is_thread_reply": False,
                }
                fetched += 1

                if include_threads and message.get("reply_count", 0) > 0:
                    yield from self._fetch_thread(resource_id, message["ts"])

                if fetched >= max_messages:
                    break

            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

    def _fetch_thread(self, channel: str, thread_ts: str) -> Iterable[dict[str, Any]]:
        data = self._call("conversations.replies", channel=channel, ts=thread_ts, limit=200)
        for message in data.get("messages", []):
            if message.get("ts") == thread_ts:
                continue  # the parent message, already yielded by fetch()
            yield {
                "channel": channel,
                "user": message.get("user"),
                "text": message.get("text", ""),
                "ts": message.get("ts"),
                "thread_ts": thread_ts,
                "is_thread_reply": True,
            }

    def normalize(self, raw_record: dict[str, Any]) -> ContextObject:
        return ContextObject(
            type="message",
            content=raw_record.get("text", ""),
            source=self.name,
            metadata={
                "channel": raw_record.get("channel"),
                "user": raw_record.get("user"),
                "ts": raw_record.get("ts"),
                "thread_ts": raw_record.get("thread_ts"),
                "is_thread_reply": raw_record.get("is_thread_reply", False),
            },
        )
