"""Ties parsing -> normalization -> chunking -> dedup together for a
connector's raw output, producing ContextObjects ready for indexing."""

from __future__ import annotations

from contextflow.core.context import ContextObject
from contextflow.governance.pii import redact_pii
from contextflow.ingestion.chunking import chunk_text
from contextflow.ingestion.deduplication import deduplicate
from contextflow.ingestion.extractor import ObservationExtractor
from contextflow.ingestion.normalization import normalize_text


def _split(obj: ContextObject, pieces: list[str]) -> list[ContextObject]:
    """One ContextObject per piece. A single piece keeps the source's id;
    multiple pieces each get a distinct `<id>#chunk-<n>` id, since the
    stores are keyed by id and identical ids would overwrite each other
    (leaving only the last chunk of every long document retrievable)."""
    if len(pieces) == 1:
        return [obj.model_copy(update={"content": pieces[0]})]
    return [
        obj.model_copy(
            update={
                "id": f"{obj.id}#chunk-{i}",
                "content": piece,
                "metadata": {**obj.metadata, "parent_id": obj.id, "chunk_index": i},
            }
        )
        for i, piece in enumerate(pieces)
    ]


def process(
    objects: list[ContextObject], chunk_size: int = 1000, extract_observations: bool = False
) -> list[ContextObject]:
    extractor = ObservationExtractor() if extract_observations else None
    processed = []
    for obj in objects:
        clean = normalize_text(redact_pii(obj.content))
        if extractor is not None:
            # Phase 9: Splice LLM observations into context blocks
            processed.extend(_split(obj, extractor.extract(clean)))
        else:
            processed.extend(_split(obj, chunk_text(clean, chunk_size=chunk_size)))
    return deduplicate(processed)
