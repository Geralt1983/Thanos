#!/usr/bin/env python3
"""
Unit tests for HistorySearchHandler.

Tests cover:
- Search query processing and validation
- Filter parsing (agent, date, session, after, before)
- Query term highlighting with intelligent preview window
- Result formatting with session context
- ChromaAdapter integration and error handling
- Edge cases (empty results, missing ChromaAdapter, etc.)
"""

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
import sys

import pytest

# Add project root to path
THANOS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(THANOS_DIR))

from Tools.command_handlers.history_search_handler import HistorySearchHandler
from Tools.command_handlers.base import CommandResult


@dataclass
class MockChromaResult:
    """Mock result from ChromaAdapter."""

    success: bool
    data: dict = None
    error: str = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


@pytest.mark.unit
class TestHistorySearchHandler:
    """Test suite for HistorySearchHandler."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for HistorySearchHandler."""
        orchestrator = Mock()
        session_manager = Mock()
        context_manager = Mock()
        state_reader = Mock()
        thanos_dir = Path("/mock/thanos")
        current_agent_getter = Mock(return_value="architect")

        return {
            "orchestrator": orchestrator,
            "session_manager": session_manager,
            "context_manager": context_manager,
            "state_reader": state_reader,
            "thanos_dir": thanos_dir,
            "current_agent_getter": current_agent_getter,
        }

    @pytest.fixture
    def handler(self, mock_dependencies):
        """Create HistorySearchHandler with mocked dependencies."""
        return HistorySearchHandler(**mock_dependencies)

    @pytest.fixture
    def mock_session_with_chroma(self, mock_dependencies):
        """Create handler with ChromaAdapter configured."""
        handler = HistorySearchHandler(**mock_dependencies)
        handler.session._chroma = Mock()
        handler.session._chroma.call_tool = AsyncMock()
        return handler

    # Test filter parsing

    def test_parse_filters_no_filters(self, handler):
        """Test parsing query without filters."""
        query, filters = handler._parse_filters("authentication implementation")

        assert query == "authentication implementation"
        assert filters is None

    def test_parse_filters_agent_filter(self, handler):
        """Test parsing agent filter."""
        query, filters = handler._parse_filters("API design agent:architect")

        assert query == "API design"
        assert filters == {"agent": "architect"}

    def test_parse_filters_date_filter(self, handler):
        """Test parsing date filter."""
        query, filters = handler._parse_filters("database changes date:2026-01-11")

        assert query == "database changes"
        assert filters == {"date": "2026-01-11"}

    def test_parse_filters_session_filter(self, handler):
        """Test parsing session filter."""
        query, filters = handler._parse_filters("error handling session:abc123")

        assert query == "error handling"
        assert filters == {"session_id": "abc123"}

    def test_parse_filters_after_filter(self, handler):
        """Test parsing after date filter."""
        query, filters = handler._parse_filters("API work after:2026-01-01")

        assert query == "API work"
        assert filters == {"date": {"$gte": "2026-01-01"}}

    def test_parse_filters_before_filter(self, handler):
        """Test parsing before date filter."""
        query, filters = handler._parse_filters("database work before:2026-01-31")

        assert query == "database work"
        assert filters == {"date": {"$lte": "2026-01-31"}}

    def test_parse_filters_date_range(self, handler):
        """Test parsing date range with after and before."""
        query, filters = handler._parse_filters("API changes after:2026-01-01 before:2026-01-31")

        assert query == "API changes"
        assert filters == {
            "date": {
                "$gte": "2026-01-01",
                "$lte": "2026-01-31"
            }
        }

    def test_parse_filters_multiple_filters(self, handler):
        """Test parsing multiple filters combined."""
        query, filters = handler._parse_filters("testing agent:architect date:2026-01-11")

        assert query == "testing"
        assert filters == {
            "agent": "architect",
            "date": "2026-01-11"
        }

    def test_parse_filters_only_filters_no_query(self, handler):
        """Test parsing with only filters and no search query."""
        query, filters = handler._parse_filters("agent:architect date:2026-01-11")

        assert query == ""
        assert filters == {
            "agent": "architect",
            "date": "2026-01-11"
        }

    # Test query term highlighting

    def test_highlight_query_terms_single_word(self, handler):
        """Test highlighting single query term."""
        content = "We discussed authentication using JWT tokens for API access."
        query = "authentication"

        result = handler._highlight_query_terms(content, query)

        assert "\x1b[1mauthentication\x1b[0m" in result
        assert "JWT" in result

    def test_highlight_query_terms_multiple_words(self, handler):
        """Test highlighting multiple query terms."""
        content = "The API implementation uses REST patterns for authentication."
        query = "API authentication"

        result = handler._highlight_query_terms(content, query)

        assert "\x1b[1mAPI\x1b[0m" in result
        assert "\x1b[1mauthentication\x1b[0m" in result

    def test_highlight_query_terms_case_insensitive(self, handler):
        """Test case-insensitive query highlighting."""
        content = "Authentication is handled by the API gateway using JWT."
        query = "authentication api"

        result = handler._highlight_query_terms(content, query)

        # Should highlight both uppercase and lowercase matches
        assert "\x1b[1mAuthentication\x1b[0m" in result or "\x1b[1mauthentication\x1b[0m" in result.lower()
        assert "\x1b[1mAPI\x1b[0m" in result or "\x1b[1mapi\x1b[0m" in result.lower()

    def test_highlight_query_terms_preview_window(self, handler):
        """Test intelligent preview window centering."""
        # Create long content with match in middle
        prefix = "Lorem ipsum dolor sit amet " * 10
        match_text = "authentication implementation details"
        suffix = " consectetur adipiscing elit" * 10
        content = prefix + match_text + suffix

        result = handler._highlight_query_terms(content, "authentication", max_length=100)

        # Should contain the match
        assert "authentication" in result.lower()
        # Should be truncated (indicated by ellipsis)
        assert "..." in result
        # Should not contain entire prefix
        assert len(result) < len(content)

    def test_highlight_query_terms_no_match(self, handler):
        """Test highlighting when query not found in content."""
        content = "Database migration strategy for production deployment."
        query = "authentication"

        result = handler._highlight_query_terms(content, query)

        # Should show beginning of content
        assert "Database" in result
        # No highlighting since no match
        assert "\x1b[1m" not in result or result.count("\x1b[1m") == 0

    def test_highlight_query_terms_empty_content(self, handler):
        """Test highlighting with empty content."""
        result = handler._highlight_query_terms("", "query")
        assert result == ""

    def test_highlight_query_terms_short_content(self, handler):
        """Test highlighting with short content."""
        content = "Short text"
        query = "text"

        result = handler._highlight_query_terms(content, query, max_length=100)

        # Should not truncate short content
        assert "..." not in result
        assert content.replace("text", "\x1b[1mtext\x1b[0m") == result

    # Test command handling

    def test_handle_history_search_empty_args(self, handler):
        """Test handling empty search query."""
        with patch("builtins.print") as mock_print:
            result = handler.handle_history_search("")

            # Should show usage message
            assert mock_print.call_count > 0
            # Should find "Usage:" in one of the print calls
            usage_found = any("Usage:" in str(call) for call in mock_print.call_args_list)
            assert usage_found

    def test_handle_history_search_no_chroma_adapter(self, handler):
        """Test handling search when ChromaAdapter not configured."""
        handler.session._chroma = None

        with patch("builtins.print") as mock_print:
            result = handler.handle_history_search("test query")

            assert result.success is False
            # Should mention ChromaAdapter not configured
            chroma_mentioned = any(
                "ChromaAdapter" in str(call) for call in mock_print.call_args_list
            )
            assert chroma_mentioned

    def test_handle_history_search_only_filters_no_query(self, mock_session_with_chroma):
        """Test handling when only filters provided without search query."""
        with patch("builtins.print") as mock_print:
            result = mock_session_with_chroma.handle_history_search("agent:architect date:2026-01-11")

            assert result.success is False
            # Should show error about missing query
            error_found = any("No search query" in str(call) for call in mock_print.call_args_list)
            assert error_found

    @pytest.mark.asyncio
    async def test_handle_history_search_successful_results(self, mock_session_with_chroma):
        """Test successful search with results."""
        # Mock ChromaAdapter response
        mock_results = [
            {
                "content": "We implemented authentication using JWT tokens.",
                "metadata": {
                    "session_id": "abc12345",
                    "date": "2026-01-11",
                    "timestamp": "2026-01-11T14:23:45",
                    "role": "user",
                    "agent": "architect"
                },
                "similarity": 0.85
            },
            {
                "content": "The authentication middleware validates tokens on each request.",
                "metadata": {
                    "session_id": "def67890",
                    "date": "2026-01-10",
                    "timestamp": "2026-01-10T10:15:30",
                    "role": "assistant",
                    "agent": "ops"
                },
                "similarity": 0.78
            }
        ]

        mock_chroma_result = MockChromaResult(
            success=True,
            data={"results": mock_results}
        )

        mock_session_with_chroma.session._chroma.call_tool.return_value = mock_chroma_result

        with patch("builtins.print") as mock_print:
            result = mock_session_with_chroma.handle_history_search("authentication")

            # Should succeed
            assert result.success is not False

            # Should display results
            output = "\n".join(str(call) for call in mock_print.call_args_list)
            assert "Search Results" in output
            assert "2 semantically similar" in output or "Found 2" in output

            # Should show session context
            assert "abc12345" in output
            assert "architect" in output

            # Should show similarity scores
            assert "85" in output or "0.85" in output

    @pytest.mark.asyncio
    async def test_handle_history_search_no_results(self, mock_session_with_chroma):
        """Test search with no results."""
        mock_chroma_result = MockChromaResult(
            success=True,
            data={"results": []}
        )

        mock_session_with_chroma.session._chroma.call_tool.return_value = mock_chroma_result

        with patch("builtins.print") as mock_print:
            result = mock_session_with_chroma.handle_history_search("nonexistent query")

            # Should complete without error
            assert result.success is not False

            # Should show "no matches" message
            no_matches_found = any(
                "No matches" in str(call) for call in mock_print.call_args_list
            )
            assert no_matches_found

    @pytest.mark.asyncio
    async def test_handle_history_search_with_filters(self, mock_session_with_chroma):
        """Test search with filters applied."""
        mock_results = [
            {
                "content": "Database optimization completed.",
                "metadata": {
                    "session_id": "xyz12345",
                    "date": "2026-01-11",
                    "timestamp": "2026-01-11T16:30:00",
                    "role": "assistant",
                    "agent": "architect"
                },
                "similarity": 0.92
            }
        ]

        mock_chroma_result = MockChromaResult(
            success=True,
            data={"results": mock_results}
        )

        mock_session_with_chroma.session._chroma.call_tool.return_value = mock_chroma_result

        with patch("builtins.print") as mock_print:
            result = mock_session_with_chroma.handle_history_search(
                "database agent:architect date:2026-01-11"
            )

            # Should succeed
            assert result.success is not False

            # Should show active filters
            output = "\n".join(str(call) for call in mock_print.call_args_list)
            assert "Active filters" in output
            assert "agent=architect" in output
            assert "date=2026-01-11" in output

    @pytest.mark.asyncio
    async def test_handle_history_search_with_date_range(self, mock_session_with_chroma):
        """Test search with date range filters."""
        mock_chroma_result = MockChromaResult(
            success=True,
            data={"results": []}
        )

        mock_session_with_chroma.session._chroma.call_tool.return_value = mock_chroma_result

        with patch("builtins.print") as mock_print:
            result = mock_session_with_chroma.handle_history_search(
                "API work after:2026-01-01 before:2026-01-31"
            )

            # Should succeed
            assert result.success is not False

            # Should show date range in filters
            output = "\n".join(str(call) for call in mock_print.call_args_list)
            if "Active filters" in output:
                # Date range should be displayed
                assert "2026-01-01" in output and "2026-01-31" in output

    @pytest.mark.asyncio
    async def test_handle_history_search_chroma_error(self, mock_session_with_chroma):
        """Test handling ChromaAdapter errors."""
        mock_chroma_result = MockChromaResult(
            success=False,
            error="ChromaDB connection failed"
        )

        mock_session_with_chroma.session._chroma.call_tool.return_value = mock_chroma_result

        with patch("builtins.print") as mock_print:
            result = mock_session_with_chroma.handle_history_search("test query")

            assert result.success is False

            # Should show error message
            error_found = any(
                "failed" in str(call).lower() for call in mock_print.call_args_list
            )
            assert error_found

    @pytest.mark.asyncio
    async def test_handle_history_search_exception_handling(self, mock_session_with_chroma):
        """Test exception handling during search."""
        # Make call_tool raise an exception
        mock_session_with_chroma.session._chroma.call_tool.side_effect = Exception(
            "Unexpected error"
        )

        with patch("builtins.print") as mock_print:
            result = mock_session_with_chroma.handle_history_search("test query")

            assert result.success is False

            # Should show error message - check for either "Error" or "Unexpected error" in output
            output = "\n".join(str(call) for call in mock_print.call_args_list)
            error_found = "Error" in output or "Unexpected error" in output or "error" in output.lower()
            assert error_found

    def test_handle_history_search_calls_semantic_search_correctly(self, mock_session_with_chroma):
        """Test that semantic_search is called with correct parameters."""
        mock_chroma_result = MockChromaResult(
            success=True,
            data={"results": []}
        )

        mock_session_with_chroma.session._chroma.call_tool.return_value = mock_chroma_result

        with patch("builtins.print"):
            mock_session_with_chroma.handle_history_search("test query agent:architect")

            # Verify call_tool was called
            assert mock_session_with_chroma.session._chroma.call_tool.called

            # Get the call arguments
            call_args = mock_session_with_chroma.session._chroma.call_tool.call_args

            # Should call semantic_search tool
            assert call_args[0][0] == "semantic_search"

            # Should include query and where clause
            params = call_args[0][1]
            assert params["query"] == "test query"
            assert params["collection"] == "conversations"
            assert params["limit"] == 10
            assert "where" in params
            assert params["where"]["agent"] == "architect"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
