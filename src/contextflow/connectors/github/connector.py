"""GitHub connector: syncs issues, pull requests, and README content
from configured repositories via the GitHub REST API.

Config:
    token: GitHub personal access token (defaults to $GITHUB_TOKEN).
           Optional for public repos, but unauthenticated requests are
           rate-limited to 60/hour — set a token for anything beyond a
           quick demo.
    repos: list of "owner/repo" strings to sync
    include_readme: whether to also sync each repo's README (default True)
    max_items_per_repo: cap on issues+PRs fetched per repo (default 100)
"""

from __future__ import annotations

import base64
import os
from collections.abc import Iterable
from typing import Any

import httpx

from contextflow.connectors.base import Connector
from contextflow.core.context import ContextObject

_API_BASE = "https://api.github.com"


class GitHubConnector(Connector):
    name = "github"

    def authenticate(self) -> None:
        token = self.config.get("token") or os.environ.get("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(base_url=_API_BASE, headers=headers, timeout=30.0)

    def discover(self) -> Iterable[str]:
        repos = self.config.get("repos", [])
        if not repos:
            raise RuntimeError("GitHubConnector requires config['repos'] (list of owner/repo)")
        return repos

    def fetch(self, resource_id: str) -> Iterable[dict[str, Any]]:
        owner, repo = resource_id.split("/", 1)
        max_items = self.config.get("max_items_per_repo", 100)
        fetched = 0
        page = 1

        while fetched < max_items:
            resp = self._client.get(
                f"/repos/{owner}/{repo}/issues",
                params={"state": "all", "per_page": min(50, max_items - fetched), "page": page},
            )
            resp.raise_for_status()
            items = resp.json()
            if not items:
                break
            for item in items:
                yield {
                    "kind": "pull_request" if "pull_request" in item else "issue",
                    "repo": resource_id,
                    "number": item["number"],
                    "title": item.get("title", ""),
                    "body": item.get("body") or "",
                    "url": item.get("html_url"),
                    "author": (item.get("user") or {}).get("login"),
                    "state": item.get("state"),
                    "updated_at": item.get("updated_at"),
                }
                fetched += 1
                if fetched >= max_items:
                    break
            page += 1

        if self.config.get("include_readme", True):
            readme = self._fetch_readme(owner, repo)
            if readme is not None:
                yield readme

    def _fetch_readme(self, owner: str, repo: str) -> dict[str, Any] | None:
        resp = self._client.get(f"/repos/{owner}/{repo}/readme")
        if resp.status_code != 200:
            return None
        data = resp.json()
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
        return {
            "kind": "readme",
            "repo": f"{owner}/{repo}",
            "number": None,
            "title": "README",
            "body": content,
            "url": data.get("html_url"),
            "author": None,
            "state": None,
            "updated_at": None,
        }

    def normalize(self, raw_record: dict[str, Any]) -> ContextObject:
        kind = raw_record.get("kind")
        content = f"{raw_record.get('title', '')}\n\n{raw_record.get('body', '')}".strip()
        return ContextObject(
            type="ticket" if kind in ("issue", "pull_request") else "document",
            content=content,
            source=self.name,
            metadata={
                "repo": raw_record.get("repo"),
                "number": raw_record.get("number"),
                "url": raw_record.get("url"),
                "author": raw_record.get("author"),
                "state": raw_record.get("state"),
                "kind": kind,
            },
        )
