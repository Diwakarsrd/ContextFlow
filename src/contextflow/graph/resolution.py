"""
Entity Resolution Module for Knowledge Graph Mapping.

Handles the canonicalization of distinct string representations of an entity
(e.g., '@acmecorp', 'Acme', 'Acme Corporation') into a single underlying node ID.
"""
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("contextflow.graph.resolution")

class BaseEntityResolver(ABC):
    """
    Base class for entity resolution. Custom resolvers (e.g., Cosine-similarity 
    based or LLM-based) should inherit from this.
    """
    @abstractmethod
    def resolve(self, entity_str: str) -> str:
        pass

class RuleBasedEntityResolver(BaseEntityResolver):
    """
    Resolves entities using a strict dictionary mapping.
    
    Why use rule-based? In financial or legal AI contexts, LLM-based entity resolution 
    can hallucinate mappings (e.g. mapping 'Apple' the fruit to 'Apple Inc.'). A strict 
    rule-based resolver enforces safety at the cost of manual curation.
    """
    def __init__(self, canonical_map: dict[str, str] | None = None) -> None:
        self._canonical_map = canonical_map or {}
        
    def resolve(self, entity_str: str) -> str:
        if not entity_str:
            raise ValueError("entity_str cannot be empty or None")
            
        lower_ent = entity_str.lower().strip()
        resolved = self._canonical_map.get(lower_ent, entity_str)
        
        if resolved != entity_str:
            logger.debug(f"Resolved alias '{entity_str}' -> '{resolved}'")
            
        return resolved
