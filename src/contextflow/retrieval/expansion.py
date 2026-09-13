"""
Query expansion subsystem for ContextFlow.

This module provides the foundational interfaces for query expansion.
While the default implementation uses a static ruleset for zero-dependency execution,
production environments should inject an LLM-backed or Knowledge-Graph-backed expander
that conforms to the QueryExpander protocol.
"""
from typing import Protocol, runtime_checkable
import logging

logger = logging.getLogger("contextflow.retrieval.expansion")

@runtime_checkable
class QueryExpander(Protocol):
    """
    Protocol defining the contract for query expansion.
    """
    def expand(self, query: str) -> list[str]:
        ...

class StaticQueryExpander:
    """
    A deterministic query expander using a predefined alias map.
    
    Trade-off: This sacrifices broad semantic understanding (like an LLM would provide)
    in favor of sub-millisecond execution times and deterministic behavior, which is 
    often preferable in strict enterprise RBAC environments where query unpredictability 
    is a compliance risk.
    """
    def __init__(self, synonym_map: dict[str, list[str]] | None = None) -> None:
        self._synonyms = synonym_map or {}
        if not self._synonyms:
            logger.debug("StaticQueryExpander initialized with empty synonym map.")
        
    def expand(self, query: str) -> list[str]:
        if not query or not query.strip():
            logger.warning("Received empty query for expansion. Returning as-is.")
            return [query]

        variations: list[str] = [query.strip()]
        words = query.lower().split()
        
        syn_variation = [self._synonyms.get(w, [w])[0] for w in words]
        syn_query = " ".join(syn_variation)
        
        if syn_query != query.lower():
            variations.append(syn_query)
            logger.debug(f"Expanded query '{query}' to include: {syn_query}")
            
        return variations
