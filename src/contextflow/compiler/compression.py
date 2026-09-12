# ruff: noqa
import time

class ContextCompressor:
    """Phase 4 and 5 Core: Intelligent compression and Memory Time-Decay."""
    @staticmethod
    def apply_decay(confidence: float, timestamp: float, half_life_days: int = 30) -> float:
        age_days = (time.time() - timestamp) / (60 * 60 * 24)
        if age_days < 0: return confidence
        return confidence * (0.5 ** (age_days / half_life_days))

    @staticmethod
    def compress(text: str, max_tokens: int) -> str:
        words = text.split()
        if len(words) <= max_tokens: return text
        truncated = " ".join(words[:max_tokens])
        if "." in truncated: truncated = truncated.rsplit(".", 1)[0] + "."
        return truncated + " [Compressed for length...]"
