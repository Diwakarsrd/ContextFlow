"""The Connector interface. Every source integration — built-in or
community-contributed — implements this. See CONTRIBUTING.md for the
connector contribution guide.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from contextflow.core.context import ContextObject


class Connector(ABC):
    """Base class for all ContextFlow connectors.

    Lifecycle: authenticate() once, then discover() -> fetch() -> normalize()
    -> emit() for each sync. `sync()` is a default implementation of that
    pipeline; override it only if your source needs a different flow.
    """

    name: str = "base"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    @abstractmethod
    def authenticate(self) -> None:
        """Validate credentials / establish a client. Raise on failure."""

    @abstractmethod
    def discover(self) -> Iterable[str]:
        """Return an iterable of resource identifiers available to sync
        (repo names, channel IDs, table names, file paths, ...)."""

    @abstractmethod
    def fetch(self, resource_id: str) -> Iterable[dict[str, Any]]:
        """Fetch raw records for a single discovered resource."""

    @abstractmethod
    def normalize(self, raw_record: dict[str, Any]) -> ContextObject:
        """Convert one raw record into a ContextObject."""

    def emit(self, objects: Iterable[ContextObject]) -> Iterable[ContextObject]:
        """Hook for last-mile transforms (dedup, filtering) before objects
        reach the ingestion pipeline. Default: pass through unchanged."""
        yield from objects

    def sync(self) -> Iterable[ContextObject]:
        """Default end-to-end sync pipeline: authenticate -> discover ->
        fetch -> normalize -> emit."""
        self.authenticate()
        for resource_id in self.discover():
            objects = (self.normalize(raw) for raw in self.fetch(resource_id))
            yield from self.emit(objects)
