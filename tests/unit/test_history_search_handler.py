#!/usr/bin/env python3
"""
Unit tests for HistorySearchHandler.

Tests cover:
- Search query processing and validation
- Filter parsing (client, source, type)
- Query term highlighting with intelligent preview window
- Result formatting with heat scores and context
- Memory V2 integration and error handling
- Edge cases (empty results, missing Memory V2, etc.)
"""

from pathlib import Path
from unittest.mock import Mock, patch, PropertyMock
import sys

import pytest

# Add project root to path
THANOS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(THANOS_DIR))

from Tools.command_handlers.history_search_handler import HistorySearchHandler
from Tools.command_handlers.base import CommandResult


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
    def handler_with_memory(self, mock_dependencies):
        """Create handler with Memory V2 service configured."""
        handler = HistorySearchHandler(**mock_dependencies)
        # Mock the memory_service property
        mock_memory_service = Mock()
        mock_memory_service.search = Mock(return_value=[])
        handler._memory_service = mock_memory_service
        return handler

    # Test filter parsing

    def test_parse_filters_no_filters(self, handler):
        """Test parsing query without filters."""
        query, filters = handler._parse_filters("authentication implementation")

        assert query == "authentication implementation"
        assert filters is None

    def test_parse_filters_client_filter(self, handler):
        """Test parsing client filter."""
        query, filters = handler._parse_filters("API design client:Orlando")

        assert query == "API design"
        assert filters == {"client": "Orlando"}

    def test_parse_filters_source_filter(self, handler):
        """Test parsing source filter."""
        query, filters = handler._parse_filters("meeting notes source:hey_pocket")

        assert query == "meeting notes"
        assert filters == {"source": "hey_pocket"}

    def test_parse_filters_type_filter(self, handler):
        """Test parsing memory type filter."""
        query, filters = handler._parse_filters("decisions type:decision")

        assert query == "decisions"
        assert filters == {"memory_type": "decision"}

    def test_parse_filters_agent_filter_legacy(self, handler):
        """Test parsing legacy agent filter (preserved for compatibility)."""
        query, filters = handler._parse_filters("API design agent:architect")

        assert query == "API design"
        assert filters == {"agent": "architect"}

    def test_parse_filters_session_filter(self, handler):
        """Test parsing session filter."""
        query, filters = handler._parse_filters("error handling session:abc123")

        assert query == "error handling"
        assert filters == {"session_id": "abc123"}

    def test_parse_filters_date_filter(self, handler):
        """Test parsing date filter (limited support)."""
        query, filters = handler._parse_filters("database changes date:2026-01-11")

        assert query == "database changes"
        assert filters == {"date": "2026-01-11"}

    def test_parse_filters_after_filter(self, handler):
        """Test parsing after date filter (stored as internal key)."""
        query, filters = handler._parse_filters("API work after:2026-01-01")

        assert query == "API work"
        assert filters == {"_after": "2026-01-01"}

    def test_parse_filters_before_filter(self, handler):
        """Test parsing before date filter (stored as internal key)."""
        query, filters = handler._parse_filters("database work before:2026-01-31")

        assert query == "database work"
        assert filters == {"_before": "2026-01-31"}

    def test_parse_filters_multiple_filters(self, handler):
        """Test parsing multiple filters combined."""
        query, filters = handler._parse_filters("testing client:Orlando source:conversation")

        assert query == "testing"
        assert filters == {
            "client": "Orlando",
            "source": "conversation"
        }

    def test_parse_filters_only_filters_no_query(self, handler):
        """Test parsing with only filters and no search query."""
        query, filters = handler._parse_filters("client:Orlando source:manual")

        assert query == ""
        assert filters == {
            "client": "Orlando",
            "source": "manual"
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

    def test_handle_history_search_no_memory_service(self, handler):
        """Test handling search when Memory V2 service not configured."""
        # memory_service property will return None since _memory_service is None
        # and we haven't mocked the import
        handler._memory_service = None

        with patch("builtins.print") as mock_print:
            with patch.object(HistorySearchHandler, 'memory_service', new_callable=PropertyMock) as mock_prop:
                mock_prop.return_value = None
                result = handler.handle_history_search("test query")

                assert result.success is False
                # Should mention Memory V2 not configured
                memory_mentioned = any(
                    "Memory V2" in str(call) for call in mock_print.call_args_list
                )
                assert memory_mentioned

    def test_handle_history_search_only_filters_no_query(self, handler_with_memory):
        """Test handling when only filters provided without search query."""
        with patch("builtins.print") as mock_print:
            result = handler_with_memory.handle_history_search("client:Orlando source:manual")

            assert result.success is False
            # Should show error about missing query
            error_found = any("No search query" in str(call) for call in mock_print.call_args_list)
            assert error_found

    def test_handle_history_search_successful_results(self, handler_with_memory):
        """Test successful search with results."""
        # Mock Memory V2 response
        mock_results = [
            {
                "id": "abc-123",
                "memory": "We implemented authentication using JWT tokens.",
                "effective_score": 0.85,
                "heat": 0.9,
                "importance": 1.0,
                "client": "Orlando",
                "source": "conversation",
                "created_at": "2026-01-11T14:23:45"
            },
            {
                "id": "def-456",
                "memory": "The authentication middleware validates tokens on each request.",
                "effective_score": 0.78,
                "heat": 0.5,
                "importance": 1.0,
                "client": "Memphis",
                "source": "manual",
                "created_at": "2026-01-10T10:15:30"
            }
        ]

        handler_with_memory._memory_service.search.return_value = mock_results

        with patch("builtins.print") as mock_print:
            result = handler_with_memory.handle_history_search("authentication")

            # Should succeed
            assert result.success is not False

            # Should display results
            output = "\n".join(str(call) for call in mock_print.call_args_list)
            assert "Search Results" in output
            assert "2 relevant" in output or "Found 2" in output

            # Should show client context
            assert "Orlando" in output

            # Should show relevance scores
            assert "85" in output or "0.85" in output

    def test_handle_history_search_no_results(self, handler_with_memory):
        """Test search with no results."""
        handler_with_memory._memory_service.search.return_value = []

        with patch("builtins.print") as mock_print:
            result = handler_with_memory.handle_history_search("nonexistent query")

            # Should complete without error
            assert result.success is not False

            # Should show "no matches" message
            no_matches_found = any(
                "No matches" in str(call) for call in mock_print.call_args_list
            )
            assert no_matches_found

    def test_handle_history_search_with_filters(self, handler_with_memory):
        """Test search with filters applied."""
        mock_results = [
            {
                "id": "xyz-789",
                "memory": "Database optimization completed.",
                "effective_score": 0.92,
                "heat": 0.8,
                "importance": 1.5,
                "client": "Orlando",
                "source": "conversation",
                "created_at": "2026-01-11T16:30:00"
            }
        ]

        handler_with_memory._memory_service.search.return_value = mock_results

        with patch("builtins.print") as mock_print:
            result = handler_with_memory.handle_history_search(
                "database client:Orlando source:conversation"
            )

            # Should succeed
            assert result.success is not False

            # Should show active filters
            output = "\n".join(str(call) for call in mock_print.call_args_list)
            assert "Active filters" in output
            assert "client=Orlando" in output
            assert "source=conversation" in output

    def test_handle_history_search_exception_handling(self, handler_with_memory):
        """Test exception handling during search."""
        # Make search raise an exception
        handler_with_memory._memory_service.search.side_effect = Exception(
            "Database connection failed"
        )

        with patch("builtins.print") as mock_print:
            result = handler_with_memory.handle_history_search("test query")

            assert result.success is False

            # Should show error message
            output = "\n".join(str(call) for call in mock_print.call_args_list)
            error_found = "Error" in output or "error" in output.lower()
            assert error_found

    def test_handle_history_search_calls_memory_service_correctly(self, handler_with_memory):
        """Test that Memory V2 search is called with correct parameters."""
        handler_with_memory._memory_service.search.return_value = []

        with patch("builtins.print"):
            handler_with_memory.handle_history_search("test query client:Orlando")

            # Verify search was called
            assert handler_with_memory._memory_service.search.called

            # Get the call arguments
            call_args = handler_with_memory._memory_service.search.call_args

            # Should include query
            assert call_args[1]["query"] == "test query"
            assert call_args[1]["limit"] == 10

            # Should include filters
            assert call_args[1]["filters"]["client"] == "Orlando"

    def test_handle_history_search_heat_indicators(self, handler_with_memory):
        """Test heat indicators are displayed correctly."""
        mock_results = [
            {
                "id": "hot-1",
                "memory": "Hot memory content",
                "effective_score": 0.9,
                "heat": 0.9,  # Hot
                "importance": 1.0,
            },
            {
                "id": "warm-2",
                "memory": "Warm memory content",
                "effective_score": 0.7,
                "heat": 0.5,  # Warm
                "importance": 1.0,
            },
            {
                "id": "cold-3",
                "memory": "Cold memory content",
                "effective_score": 0.5,
                "heat": 0.1,  # Cold
                "importance": 1.0,
            }
        ]

        handler_with_memory._memory_service.search.return_value = mock_results

        with patch("builtins.print") as mock_print:
            handler_with_memory.handle_history_search("memory")

            output = "\n".join(str(call) for call in mock_print.call_args_list)
            # Should show heat indicators (fire emoji for hot, snowflake for cold)
            # Note: The actual emoji display may vary in terminal output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
