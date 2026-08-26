"""Compiles retrieved ContextObjects into a token-budgeted ContextPack.

This is where ContextFlow differentiates from "retrieve chunks, paste into
prompt" RAG: dedup, categorize, detect conflicts, and respect a token
budget instead of dumping everything at the model.
"""

from __future__ import annotations

from contextflow.compiler.conflict import detect_conflicts
from contextflow.core.context import ContextObject
from contextflow.core.context_pack import ContextPack

# Rough chars-per-token estimate used until a real tokenizer is wired in.
_CHARS_PER_TOKEN = 4

_TYPE_TO_BUCKET = {
    "document": "documents",
    "message": "conversations",
    "conversation": "conversations",
    "ticket": "risks",
    "record": "facts",
    "code": "documents",
    "commit": "documents",
    "email": "conversations",
    "custom": "facts",
}


def compile_context_pack(
    task: str,
    objects: list[ContextObject],
    entity: str | None = None,
    max_tokens: int = 3000,
) -> ContextPack:
    """Compile a ranked list of ContextObjects (highest-value first) into
    a ContextPack, stopping once the token budget is spent."""
    pack = ContextPack.empty(task=task, entity=entity)
    pack.token_budget = max_tokens

    tokens_used = 0
    seen_content: set[str] = set()

    for obj in objects:
        if obj.content in seen_content:
            continue
        estimated_tokens = max(1, len(obj.content) // _CHARS_PER_TOKEN)
        if tokens_used + estimated_tokens > max_tokens:
            continue
        bucket = _TYPE_TO_BUCKET.get(obj.type, "facts")
        pack.add_object(obj, bucket)
        seen_content.add(obj.content)
        tokens_used += estimated_tokens

    pack.tokens_used = tokens_used
    pack.conflicts = detect_conflicts(objects)
    pack.confidence = _aggregate_confidence(objects)
    return pack


def _aggregate_confidence(objects: list[ContextObject]) -> float:
    if not objects:
        return 0.0
    return sum(obj.confidence for obj in objects) / len(objects)
