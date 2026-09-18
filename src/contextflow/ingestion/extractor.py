from __future__ import annotations

import json
import os
import httpx
from typing import List

class ObservationExtractor:
    """ Phase 9: Zero-Shot Observation Extraction Pipeline.
    Instead of vectorizing raw noise, this extracts crisp, highly semantic
    business facts and observations using an LLM.
    """
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url
        self.model = model
    
    def extract(self, text: str) -> List[str]:
        if not self.api_key:
            return [text]  # Fallback to raw text if no LLM key is configured
            
        system_prompt = (
            "You are a strict data-extraction engine. Read the following raw text and extract "
            "concrete business facts, observations, and temporal events. Ignore all conversational noise. "
            'Return ONLY a valid JSON object matching this schema: {{"observations": ["string"]}}'
        )
        
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text}
                        ]
                    }
                )
                res.raise_for_status()
                data = res.json()
                content = json.loads(data["choices"][0]["message"]["content"])
                return content.get("observations", [text])
        except Exception:
            return [text]  # Fail gracefully to allow ingestion to continue synchronously
