#!/usr/bin/env python3
"""
Unit tests for Memory Router and MemOS Deprecation.

Updated for Memory System Consolidation (Task 049).
This file now primarily tests the memory_router unified API, with a small subset
of MemOS tests to verify deprecation warnings work correctly.

Tests cover:
- Memory Router API (add_memory, search_memory, get_context)
- ADHD helpers (whats_hot, whats_cold, pin/unpin)
- Backend selection and fallback behavior
- MemOS deprecation warnings
- Convenience aliases (remember, recall)
"""

from pathlib import Path
import sys
from unittest.mock import AsyncMock, Mock, patch
import warnings

import pytest


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ========================================================================
# Test Memory Router API
# ========================================================================


class TestMemoryRouter:
    """Test unified memory router API."""

    def test_import_memory_router(self):
        """Test memory_router can be imported."""
        from Tools.memory_router import add_memory, search_memory, get_context

        assert add_memory is not None
        assert search_memory is not None
        assert get_context is not None

    @patch("Tools.memory_router._get_v2_service")
    def test_add_memory_routes_to_v2(self, mock_get_v2):
        """Test add_memory routes to Memory V2 by default."""
        from Tools.memory_router import add_memory

        # Mock Memory V2 service
        mock_service = Mock()
        mock_service.add = Mock(return_value={"id": "mem_123", "success": True})
        mock_get_v2.return_value = mock_service

        result = add_memory("Test memory", metadata={"source": "test"})

        assert result["id"] == "mem_123"
        assert result["success"] is True
        mock_service.add.assert_called_once_with("Test memory", {"source": "test"})

    @patch("Tools.memory_router._get_v2_service")
    def test_search_memory_routes_to_v2(self, mock_get_v2):
        """Test search_memory routes to Memory V2 by default."""
        from Tools.memory_router import search_memory

        # Mock Memory V2 service
        mock_service = Mock()
        mock_service.search = Mock(return_value=[
            {"id": "mem_123", "content": "Test result", "effective_score": 0.95}
        ])
        mock_get_v2.return_value = mock_service

        results = search_memory("test query", limit=10)

        assert len(results) == 1
        assert results[0]["id"] == "mem_123"
        mock_service.search.assert_called_once_with("test query", 10, None)

    @patch("Tools.memory_router._get_v2_service")
    def test_search_with_filters(self, mock_get_v2):
        """Test search_memory with client/domain filters."""
        from Tools.memory_router import search_memory

        # Mock Memory V2 service
        mock_service = Mock()
        mock_service.search = Mock(return_value=[
            {"id": "mem_123", "content": "Orlando project", "client": "Orlando"}
        ])
        mock_get_v2.return_value = mock_service

        results = search_memory(
            "project update",
            limit=10,
            filters={"client": "Orlando", "domain": "work"}
        )

        assert len(results) == 1
        assert results[0]["client"] == "Orlando"
        mock_service.search.assert_called_once()

    @patch("Tools.memory_router._get_v2_service")
    def test_get_context(self, mock_get_v2):
        """Test get_context for Claude prompts."""
        from Tools.memory_router import get_context

        # Mock Memory V2 service
        mock_service = Mock()
        mock_service.get_context_for_query = Mock(
            return_value="Context: Test memory (heat: 0.85)"
        )
        mock_get_v2.return_value = mock_service

        context = get_context("test query", limit=5)

        assert "Context: Test memory" in context
        assert "heat: 0.85" in context
        mock_service.get_context_for_query.assert_called_once_with("test query", 5)

    @patch("Tools.memory_router._get_v2_service")
    def test_get_stats(self, mock_get_v2):
        """Test get_stats returns Memory V2 statistics."""
        from Tools.memory_router import get_stats

        # Mock Memory V2 service
        mock_service = Mock()
        mock_service.stats = Mock(return_value={
            "total": 1000,
            "hot_count": 50,
            "cold_count": 100
        })
        mock_get_v2.return_value = mock_service

        stats = get_stats()

        assert stats["total"] == 1000
        assert stats["hot_count"] == 50
        mock_service.stats.assert_called_once()


# ========================================================================
# Test ADHD Helpers
# ========================================================================


class TestADHDHelpers:
    """Test ADHD helper functions."""

    @patch("Tools.memory_router._get_v2_service")
    def test_whats_hot(self, mock_get_v2):
        """Test whats_hot ADHD helper function."""
        from Tools.memory_router import whats_hot

        # Mock Memory V2 service
        mock_service = Mock()
        mock_service.whats_hot = Mock(return_value=[
            {"id": "mem_456", "content": "Hot memory", "heat": 0.95}
        ])
        mock_get_v2.return_value = mock_service

        results = whats_hot(limit=10)

        assert len(results) == 1
        assert results[0]["heat"] == 0.95
        mock_service.whats_hot.assert_called_once_with(10)

    @patch("Tools.memory_router._get_v2_service")
    def test_whats_cold(self, mock_get_v2):
        """Test whats_cold ADHD helper function."""
        from Tools.memory_router import whats_cold

        # Mock Memory V2 service
        mock_service = Mock()
        mock_service.whats_cold = Mock(return_value=[
            {"id": "mem_789", "content": "Cold memory", "heat": 0.1}
        ])
        mock_get_v2.return_value = mock_service

        results = whats_cold(threshold=0.2, limit=10)

        assert len(results) == 1
        assert results[0]["heat"] == 0.1
        mock_service.whats_cold.assert_called_once_with(0.2, 10)

    @patch("Tools.memory_router._get_v2_service")
    def test_pin_memory(self, mock_get_v2):
        """Test pin_memory prevents decay."""
        from Tools.memory_router import pin_memory

        # Mock Memory V2 service
        mock_service = Mock()
        mock_service.pin = Mock(return_value=True)
        mock_get_v2.return_value = mock_service

        result = pin_memory("mem_123")

        assert result is True
        mock_service.pin.assert_called_once_with("mem_123")

    @patch("Tools.memory_router._get_v2_service")
    def test_unpin_memory(self, mock_get_v2):
        """Test unpin_memory allows normal decay."""
        from Tools.memory_router import unpin_memory

        # Mock Memory V2 service
        mock_service = Mock()
        mock_service.unpin = Mock(return_value=True)
        mock_get_v2.return_value = mock_service

        result = unpin_memory("mem_123")

        assert result is True
        mock_service.unpin.assert_called_once_with("mem_123")


# ========================================================================
# Test Convenience Aliases
# ========================================================================


class TestConvenienceAliases:
    """Test memory router convenience aliases."""

    def test_remember_is_alias_for_add_memory(self):
        """Test remember() is an alias for add_memory()."""
        from Tools.memory_router import remember, add_memory

        assert remember is add_memory

    def test_recall_is_alias_for_search_memory(self):
        """Test recall() is an alias for search_memory()."""
        from Tools.memory_router import recall, search_memory

        assert recall is search_memory

    def test_get_memory_is_alias_for_get_context(self):
        """Test get_memory() is an alias for get_context()."""
        from Tools.memory_router import get_memory, get_context

        assert get_memory is get_context


# ========================================================================
# Test Backend Selection
# ========================================================================


class TestBackendSelection:
    """Test memory router backend selection logic."""

    @patch("Tools.memory_router._get_memos_service")
    def test_can_explicitly_use_memos_backend(self, mock_get_memos):
        """Test explicit MemOS backend selection (for migration)."""
        from Tools.memory_router import add_memory, MemoryBackend

        # Mock MemOS service
        mock_service = Mock()
        mock_service.add = Mock(return_value={"id": "memos_123", "success": True})
        mock_get_memos.return_value = mock_service

        result = add_memory(
            "Test memory",
            metadata={"source": "test"},
            backend=MemoryBackend.MEMOS
        )

        assert result["id"] == "memos_123"
        mock_service.add.assert_called_once()

    @patch("Tools.memory_router._get_v2_service")
    def test_default_backend_is_v2(self, mock_get_v2):
        """Test Memory V2 is the default backend."""
        from Tools.memory_router import add_memory

        # Mock Memory V2 service
        mock_service = Mock()
        mock_service.add = Mock(return_value={"id": "v2_123", "success": True})
        mock_get_v2.return_value = mock_service

        # Call without explicit backend - should use V2
        result = add_memory("Test memory")

        assert result["id"] == "v2_123"
        mock_service.add.assert_called_once()


# ========================================================================
# Test MemOS Deprecation Warnings (Legacy Support)
# ========================================================================


class TestMemOSDeprecation:
    """Test MemOS deprecation warnings."""

    def test_memos_import_shows_deprecation_warning(self):
        """Test that using get_memos() triggers deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            from Tools.memos import get_memos

            # Call get_memos to trigger the deprecation warning
            _ = get_memos()

            # Check that at least one warning was raised
            assert len(w) > 0

            # Check that at least one is a DeprecationWarning
            deprecation_warnings = [
                warning for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) > 0

            # Check message content
            assert any(
                "deprecated" in str(warning.message).lower()
                for warning in deprecation_warnings
            )

    @patch("Tools.memos.NEO4J_AVAILABLE", False)
    @patch("Tools.memos.CHROMA_AVAILABLE", False)
    @patch("Tools.memos.OPENAI_AVAILABLE", False)
    def test_memos_initialization_still_works(self):
        """Test MemOS can still be initialized (for migration purposes)."""
        from Tools.memos import MemOS

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            memos = MemOS()

            assert memos is not None
            assert memos.graph_available is False
            assert memos.vector_available is False


# ========================================================================
# Test MemoryResult Dataclass (Minimal Legacy Support)
# ========================================================================


class TestMemoryResult:
    """Test MemoryResult dataclass (legacy MemOS component)."""

    def test_import_memory_result(self):
        """Test MemoryResult can be imported."""
        from Tools.memos import MemoryResult

        assert MemoryResult is not None

    def test_memory_result_ok(self):
        """Test MemoryResult.ok() creates successful result."""
        from Tools.memos import MemoryResult

        result = MemoryResult.ok(
            graph_results=[{"id": "test1"}],
            vector_results=[{"content": "test"}],
            query="test query",
        )

        assert result.success is True
        assert result.error is None
        assert len(result.graph_results) == 1
        assert len(result.vector_results) == 1
        assert result.metadata.get("query") == "test query"

    def test_memory_result_fail(self):
        """Test MemoryResult.fail() creates failed result."""
        from Tools.memos import MemoryResult

        result = MemoryResult.fail("Test error", context="testing")

        assert result.success is False
        assert result.error == "Test error"
        assert result.metadata.get("context") == "testing"
        assert result.graph_results == []
        assert result.vector_results == []



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
