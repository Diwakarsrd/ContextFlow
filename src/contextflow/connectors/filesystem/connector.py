"""Filesystem connector: syncs text files from a local directory.

This connector is fully local (no auth needed), which makes it the
easiest way to try ContextFlow end-to-end — it's what `contextflow ingest
./docs` uses under the hood.

Config:
    path: directory to scan
    extensions: list of file extensions to include (default: common text types)
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from contextflow.connectors.base import Connector
from contextflow.core.context import ContextObject

DEFAULT_EXTENSIONS = {".md", ".txt", ".rst", ".py", ".ts", ".js", ".json", ".yaml", ".yml"}


class FilesystemConnector(Connector):
    name = "filesystem"

    def authenticate(self) -> None:
        path = Path(self.config.get("path", "."))
        if not path.exists():
            raise RuntimeError(f"FilesystemConnector path does not exist: {path}")
        self._root = path

    def discover(self) -> Iterable[str]:
        extensions = set(self.config.get("extensions", DEFAULT_EXTENSIONS))
        for dirpath, _dirnames, filenames in os.walk(self._root):
            for filename in filenames:
                if Path(filename).suffix in extensions:
                    yield str(Path(dirpath) / filename)

    def fetch(self, resource_id: str) -> Iterable[dict[str, Any]]:
        path = Path(resource_id)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return
        yield {"path": str(path), "content": text, "size": path.stat().st_size}

    def normalize(self, raw_record: dict[str, Any]) -> ContextObject:
        return ContextObject(
            type="document",
            content=raw_record["content"],
            source=self.name,
            metadata={"path": raw_record["path"], "size": raw_record["size"]},
        )
