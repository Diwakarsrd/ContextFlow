"""Deduplicates near-identical ContextObjects (e.g. the same doc synced
from two connectors). v0.1 ships exact-hash dedup; near-duplicate
detection via minhash/simhash is a good v0.2 contribution."""

from __future__ import annotations

import hashlib

from contextflow.core.context import ContextObject


def deduplicate(objects: list[ContextObject]) -> list[ContextObject]:
    seen: set[str] = set()
    result = []
    for obj in objects:
        digest = hashlib.sha256(obj.content.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        result.append(obj)
    return result
