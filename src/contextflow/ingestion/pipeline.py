"""Ties parsing -> normalization -> chunking -> dedup together for a
connector's raw output, producing ContextObjects ready for indexing."""

from __future__ import annotations

from contextflow.core.context import ContextObject
from contextflow.governance.pii import redact_pii
from contextflow.ingestion.chunking import chunk_text
from contextflow.ingestion.deduplication import deduplicate
from contextflow.ingestion.extractor import ObservationExtractor
from contextflow.ingestion.normalization import normalize_text


def process(objects: list[ContextObject], chunk_size: int = 1000, extract_observations: bool = False) -> list[ContextObject]:
    extractor = ObservationExtractor() if extract_observations else None
    processed = []
    for obj in objects:
        clean = normalize_text(redact_pii(obj.content))
        if extractor is not None:
            # Phase 9: Splice LLM observations into context blocks
            observations = extractor.extract(clean)
            for obs in observations:
                processed.append(obj.model_copy(update={"content": obs}))
        else:
            for piece in chunk_text(clean, chunk_size=chunk_size):
                processed.append(obj.model_copy(update={"content": piece}))
    return deduplicate(processed)
