"""
Unit tests for the ResponseCache class.
Tests TTL-based response caching functionality.
"""
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.litellm import ResponseCache


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


# ============================================================================
# ResponseCache Tests
# ============================================================================

class TestResponseCache:
    """Tests for the ResponseCache class."""

    def test_set_and_get(self, temp_dir):
        """Cache should store and retrieve responses."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=3600)

        cache.set("test prompt", "anthropic/claude-opus-4-5", {}, "cached response")
        result = cache.get("test prompt", "anthropic/claude-opus-4-5", {})

        assert result == "cached response"

    def test_cache_miss(self, temp_dir):
        """Cache should return None for missing entries."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=3600)

        result = cache.get("nonexistent", "model", {})

        assert result is None

    def test_cache_expiration(self, temp_dir):
        """Expired cache entries should return None."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=1)

        cache.set("test", "model", {}, "response")

        # Manually expire the cache
        import time
        time.sleep(1.1)

        result = cache.get("test", "model", {})
        assert result is None

    def test_different_models_different_cache(self, temp_dir):
        """Same prompt with different models should have different cache entries."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=3600)

        cache.set("test prompt", "model-a", {}, "response from A")
        cache.set("test prompt", "model-b", {}, "response from B")

        assert cache.get("test prompt", "model-a", {}) == "response from A"
        assert cache.get("test prompt", "model-b", {}) == "response from B"

    def test_clear_expired(self, temp_dir):
        """clear_expired should remove old cache entries."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=1)
        cache_dir = Path(temp_dir / "cache")

        cache.set("test1", "model", {}, "response1")
        cache.set("test2", "model", {}, "response2")

        import time
        time.sleep(1.1)

        cache.clear_expired()

        # All cache files should be removed
        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) == 0
