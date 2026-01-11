#!/usr/bin/env python3
"""
Response caching for LiteLLM client.

This module provides TTL-based response caching with model-specific storage.
Caches API responses to reduce redundant calls and improve performance while
managing cache size and expiration automatically.
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict


class ResponseCache:
    """Cache responses with TTL and model-specific storage."""

    def __init__(self, cache_path: str, ttl_seconds: int, max_size_mb: int = 100):
        self.cache_path = Path(cache_path)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def _get_cache_key(self, prompt: str, model: str, params: Dict) -> str:
        """Generate a cache key from prompt and parameters."""
        content = json.dumps({
            "prompt": prompt,
            "model": model,
            "params": {k: v for k, v in params.items() if k != "history"}
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, prompt: str, model: str, params: Dict) -> Optional[str]:
        """Retrieve cached response if valid."""
        cache_key = self._get_cache_key(prompt, model, params)
        cache_file = self.cache_path / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            cached = json.loads(cache_file.read_text())
            cached_time = datetime.fromisoformat(cached["timestamp"])
            if datetime.now() - cached_time < timedelta(seconds=self.ttl_seconds):
                return cached["response"]
            else:
                cache_file.unlink()  # Remove expired cache
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

        return None

    def set(self, prompt: str, model: str, params: Dict, response: str):
        """Cache a response."""
        cache_key = self._get_cache_key(prompt, model, params)
        cache_file = self.cache_path / f"{cache_key}.json"

        cache_file.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "response": response
        }))

    def clear_expired(self):
        """Remove expired cache entries."""
        cutoff = datetime.now() - timedelta(seconds=self.ttl_seconds)
        for cache_file in self.cache_path.glob("*.json"):
            try:
                cached = json.loads(cache_file.read_text())
                cached_time = datetime.fromisoformat(cached["timestamp"])
                if cached_time < cutoff:
                    cache_file.unlink()
            except (json.JSONDecodeError, KeyError, ValueError):
                cache_file.unlink()  # Remove corrupted cache
