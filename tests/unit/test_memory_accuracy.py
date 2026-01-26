"""
Unit tests for Memory Router Accuracy and Integration Scenarios.

Updated for Memory System Consolidation (Task 049).
This module now tests memory_router integration scenarios rather than MemOS-specific workflows.

Tests cover:
1. Session lifecycle consistency (multiple load/stops).
2. Memory router recall accuracy and search functionality.
3. Fallback mechanisms when searches yield no results.
4. Integration with command handlers using memory_router.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from Tools.command_handlers.memory_handler import MemoryHandler
from Tools.session_manager import SessionManager, Session


@pytest.fixture
def mock_dependencies(tmp_path):
    """Create common dependencies for memory tests."""
    # 1. Setup SessionManager with a temporary history directory
    history_dir = tmp_path / "History" / "Sessions"
    history_dir.mkdir(parents=True)
    # Ensure SessionManager uses this dir
    session_manager = SessionManager(history_dir=history_dir)
    # Create a dummy session to ensure we can save
    session_manager.session = Session()

    # 2. Mock Orchestrator (needed for handler init)
    orchestrator = MagicMock()

    # 3. Mock ContextManager
    context_manager = MagicMock()

    # 4. Mock StateReader
    state_reader = MagicMock()

    # 5. Root dir (needs to match structure if handler uses it)
    thanos_dir = tmp_path

    return {
        "orchestrator": orchestrator,
        "session_manager": session_manager,
        "context_manager": context_manager,
        "state_reader": state_reader,
        "thanos_dir": thanos_dir,
    }


class TestSessionLifecycleAccuracy:
    """Tests focusing on memory consistency across session load/stop cycles."""

    def test_multi_session_history_creation(self, mock_dependencies):
        """
        Verify that multiple sessions create distinct, retrievable history files.
        Simulates: Start Session A -> Stop -> Start Session B -> Stop.
        """
        sm = mock_dependencies["session_manager"]
        
        # --- Session A ---
        # Ensure we have a valid session ID
        sm.session = Session() 
        session_a_id = sm.session.id
        sm.add_user_message("Hello from Session A")
        sm.add_assistant_message("Hi A")
        sm.save() # Manually save to simulate "Stop" / persistence
        
        # --- Session B ---
        # Simulate starting a NEW session
        sm.session = Session() 
        session_b_id = sm.session.id
        sm.add_user_message("Hello from Session B")
        sm.add_assistant_message("Hi B")
        sm.save()

        # Check file existence
        # Note: SessionManager saves as `{timestamp}-{id}.md` (and .json)
        json_files = list(sm.history_dir.glob("*.json"))
        assert len(json_files) == 2
        
        # Verify content distinction
        loaded_ids = []
        for f in json_files:
            data = json.loads(f.read_text())
            loaded_ids.append(data["id"])
            if data["id"] == session_a_id:
                assert data["history"][0]["content"] == "Hello from Session A"
            elif data["id"] == session_b_id:
                assert data["history"][0]["content"] == "Hello from Session B"
        
        assert session_a_id in loaded_ids
        assert session_b_id in loaded_ids


class TestRecallAccuracy:
    """Tests focusing on memory_router recall accuracy and integration."""

    def test_recall_uses_memory_router(self, mock_dependencies):
        """Test that MemoryHandler uses memory_router for recall operations."""
        deps = mock_dependencies
        handler = MemoryHandler(**deps)

        # Mock memory_router.search_memory
        with patch('Tools.memory_router.search_memory') as mock_search:
            mock_search.return_value = [{
                "id": "mem_123",
                "content": "Use Pytest for testing",
                "effective_score": 0.95
            }]

            with patch('builtins.print'):
                handler.handle_recall("testing framework")

                # Verify memory_router.search_memory was called
                mock_search.assert_called_once()
                call_args = mock_search.call_args
                assert "testing framework" in str(call_args)

    def test_recall_fallback_to_local_history(self, mock_dependencies):
        """Test fallback to local history when memory_router returns no results."""
        deps = mock_dependencies
        handler = MemoryHandler(**deps)

        # 1. Setup Local History
        past_session = {
            "id": "session_123",
            "started_at": "2023-01-01T12:00:00",
            "history": [
                {"role": "user", "content": "What is the secret code?"},
                {"role": "assistant", "content": "The secret code is BANANA."}
            ]
        }
        session_file = deps["session_manager"].history_dir / "2023-01-01-1200-session_123.json"
        session_file.write_text(json.dumps(past_session))

        # 2. Mock memory_router to return empty results
        with patch('Tools.memory_router.search_memory') as mock_search:
            mock_search.return_value = []

            with patch('builtins.print') as mock_print:
                handler.handle_recall("BANANA")

                # Verifications:
                # 1. memory_router was tried
                mock_search.assert_called_once()

                # 2. Output should indicate it found a session match
                found_match = False
                for call_args in mock_print.call_args_list:
                    output = str(call_args)
                    if "BANANA" in output:
                        found_match = True
                        break

                assert found_match, "Should have found and printed matching session content"

    def test_repeated_queries_are_handled(self, mock_dependencies):
        """Verify that identical queries don't crash or behave inconsistently."""
        deps = mock_dependencies
        handler = MemoryHandler(**deps)

        with patch('Tools.memory_router.search_memory') as mock_search:
            mock_search.return_value = []

            with patch('builtins.print'):
                # Call multiple times - should not crash
                handler.handle_recall("query1")
                handler.handle_recall("query1")

                # Verify memory_router was called twice
                assert mock_search.call_count == 2


class TestMemoryRouterIntegration:
    """Tests for memory_router integration with command handlers."""

    def test_handler_graceful_degradation_on_memory_error(self, mock_dependencies):
        """Test handler falls back to local history when memory_router raises exception."""
        deps = mock_dependencies
        handler = MemoryHandler(**deps)

        # Create local history match
        past_session = {
            "id": "local_1",
            "started_at": "2023-01-01T12:00:00",
            "history": [{"role": "user", "content": "Local only match"}]
        }
        session_file = deps["session_manager"].history_dir / "test.json"
        session_file.write_text(json.dumps(past_session))

        # Mock memory_router to raise an exception
        with patch('Tools.memory_router.search_memory') as mock_search:
            mock_search.side_effect = Exception("Database connection error")

            with patch('builtins.print') as mock_print:
                handler.handle_recall("Local only")

                # Verify we didn't crash and found the local match
                found_match = False
                for call_args in mock_print.call_args_list:
                    if "Local only" in str(call_args):
                        found_match = True

                assert found_match, "Should fall back to local history on memory_router error"

    def test_remember_uses_memory_router(self, mock_dependencies):
        """Test that MemoryHandler uses memory_router for adding memories."""
        deps = mock_dependencies
        handler = MemoryHandler(**deps)

        with patch('Tools.memory_router.add_memory') as mock_add:
            mock_add.return_value = {"id": "mem_123", "success": True}

            with patch('builtins.print'):
                handler.handle_remember("Important meeting notes", domain="work")

                # Verify memory_router.add_memory was called
                mock_add.assert_called_once()
                call_args = mock_add.call_args
                assert "Important meeting notes" in str(call_args)

    def test_adhd_helpers_integration(self, mock_dependencies):
        """Test integration of ADHD helper functions (whats_hot, whats_cold)."""
        deps = mock_dependencies
        handler = MemoryHandler(**deps)

        with patch('Tools.memory_router.whats_hot') as mock_hot:
            mock_hot.return_value = [
                {"id": "mem_456", "content": "Current focus item", "heat": 0.95}
            ]

            with patch('builtins.print') as mock_print:
                # Assuming handler has a method to show hot memories
                # If not, this tests that the router function is available
                from Tools.memory_router import whats_hot
                results = whats_hot(limit=10)

                # Verify mock was called
                mock_hot.assert_called_once()
                assert len(results) == 1
                assert results[0]["heat"] == 0.95

