"""
Context Compiler utilities for memory decay and token compression.

Unlike naive RAG systems that truncate text arbitrarily, the ContextCompressor 
attempts to preserve semantic boundaries (sentences) and applies mathematical 
decay properties to historical memories.
"""
import logging
import time
from typing import Final

logger = logging.getLogger("contextflow.compiler.compression")

# Magic numbers extracted to constants for readability and configuration
DEFAULT_HALF_LIFE_DAYS: Final[int] = 30
SECONDS_IN_DAY: Final[int] = 86400

class ContextCompressor:
    """
    Provides stateless utility methods for context manipulation.
    """
    
    @staticmethod
    def apply_decay(confidence: float, timestamp: float, half_life_days: int = DEFAULT_HALF_LIFE_DAYS) -> float:
        """
        Applies a radioactive-style exponential decay to a memory's confidence score.
        
        This ensures that a fact retrieved from 2 years ago is mathematically down-ranked 
        compared to a fact retrieved from today, solving the 'stale context' hallucination 
        problem common in un-decayed vector stores.
        """
        if confidence < 0.0 or confidence > 1.0:
            logger.warning(f"Confidence score {confidence} is out of bounds [0, 1]. Clamping.")
            confidence = max(0.0, min(1.0, confidence))
            
        age_days = (time.time() - timestamp) / SECONDS_IN_DAY
        
        # Guard against future timestamps (e.g. clock drift or bad data)
        if age_days < 0:
            logger.debug(f"Timestamp {timestamp} is in the future. Bypassing decay.")
            return confidence
            
        decay_factor = 0.5 ** (age_days / half_life_days)
        return confidence * decay_factor

    @staticmethod
    def compress(text: str, max_tokens: int) -> str:
        """
        Intelligently compresses text to fit within token boundaries.
        
        Rather than a hard slice on characters which can break words or semantic 
        meaning, this truncates at the nearest trailing period.
        """
        if not text:
            return ""
            
        if max_tokens <= 0:
            raise ValueError("max_tokens must be strictly positive")
            
        words = text.split()
        if len(words) <= max_tokens:
            return text
            
        truncated = " ".join(words[:max_tokens])
        
        # Attempt to find the last valid sentence boundary to avoid hanging thoughts
        last_period_idx = truncated.rfind(".")
        if last_period_idx != -1:
            truncated = truncated[:last_period_idx + 1]
            
        return truncated + " [Compressed for context length]"
