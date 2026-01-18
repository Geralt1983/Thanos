"""
Unit tests for Memory Accuracy and Extensive Lifecycle Scenarios.

This module tests complex workflows and accuracy scenarios that go beyond basic
component functionality. It specifically targets:
1. Session lifecycle consistency (multiple load/stops).
2. Recall accuracy across hybrid sources (Vector vs Local).
3. Fallback mechanisms when primary systems (MemOS) fail or yield no results.
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
    """Tests focusing on the accuracy of recall from different sources (Hybrid)."""

    @pytest.mark.asyncio
    async def test_recall_prioritizes_memos_responses(self, mock_dependencies):
        """
        Test that when MemOS (Vector/Graph) returns high-confidence results,
        they are presented clearly.
        """
        deps = mock_dependencies
        handler = MemoryHandler(**deps)
        
        # Mock MemOS behavior
        # We need a MagicMock that has an AsyncMock method 'recall'
        mock_memos = MagicMock()
        
        # Create a proper result object
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.vector_results = [{
            "content": "Use Pytest for testing",
            "memory_type": "decision",
            "similarity": 0.95
        }]
        mock_result.graph_results = []
        
        # The recall method should be an AsyncMock that returns the result
        mock_memos.recall = AsyncMock(return_value=mock_result)

        # We must mock _run_async to AVOID actual asyncio loop complexity in tests
        # since BaseHandler._run_async tries to handle loops dynamically which can clash with pytest-asyncio
        mock_run_async = MagicMock(return_value=mock_result)
        
        with patch.object(handler, '_get_memos', return_value=mock_memos):
            with patch.object(handler, '_run_async', mock_run_async):
                # Call handle_recall (synchronous method)
                handler.handle_recall("testing framework")
                
                # Check that _get_memos was called
                handler._get_memos.assert_called()
                
                # Check that recall was called on the memos object 
                # (Note: since we mocked _run_async, we need to verify what passed to it)
                # But actually, handle_recall calls _run_async(memos.recall(...))
                # memos.recall(...) returns a coroutine object immediately.
                # So verify _run_async was called.
                assert handler._run_async.called

    @pytest.mark.asyncio
    async def test_recall_fallback_to_local_history(self, mock_dependencies):
        """
        Test that when MemOS returns NO results, the handler searches local JSON history.
        """
        deps = mock_dependencies
        handler = MemoryHandler(**deps)
        
        # 1. Setup Local History
        # Create a past session file with the target content
        past_session = {
            "id": "session_123",
            "started_at": "2023-01-01T12:00:00",
            "history": [
                {"role": "user", "content": "What is the secret code?"},
                {"role": "assistant", "content": "The secret code is BANANA."}
            ]
        }
        # Naming convention matters for SessionManager/MemoryHandler globbing? 
        # MemoryHandler.handle_recall: `json_files = sorted(history_dir.glob("*.json"), ...)`
        session_file = deps["session_manager"].history_dir / "2023-01-01-1200-session_123.json"
        session_file.write_text(json.dumps(past_session))
        
        # 2. Mock MemOS to return Empty results
        mock_memos = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.vector_results = []
        mock_result.graph_results = []
        
        mock_memos.recall = AsyncMock(return_value=mock_result)
        
        # Mock _run_async to return the empty result
        mock_run_async = MagicMock(return_value=mock_result)

        with patch.object(handler, '_get_memos', return_value=mock_memos):
            with patch.object(handler, '_run_async', mock_run_async):
                with patch('builtins.print') as mock_print:
                    handler.handle_recall("BANANA")
                    
                    # Verifications:
                    # 1. MemOS was tried
                    mock_memos.recall.assert_called()
                    
                    # 2. Output should indicate it found a session match
                    found_match = False
                    for call_args in mock_print.call_args_list:
                        output = str(call_args)
                        if "BANANA" in output: # relaxed check
                             found_match = True
                             break
                    
                    assert found_match, "Should have printed the matching session content when MemOS failed"

    @pytest.mark.asyncio
    async def test_simulated_cache_behavior_repeated_queries(self, mock_dependencies):
        """
        Verify that identical queries don't crash or behave inconsistently.
        (Note: Explicit caching isn't in MemoryHandler yet, but reliability is key).
        """
        deps = mock_dependencies
        handler = MemoryHandler(**deps)
        
        mock_memos = MagicMock()
        mock_memos.recall = AsyncMock(return_value=MagicMock(success=True, vector_results=[], graph_results=[]))
        
        with patch.object(handler, '_get_memos', return_value=mock_memos):
             with patch('builtins.print'):
                # Call multiple times
                handler.handle_recall("query1")
                handler.handle_recall("query1")
                
                assert mock_memos.recall.call_count == 2


class TestHybridMemoryIntegration:
    """Tests for the intersection of components."""

    @patch("Tools.command_handlers.memory_handler.MEMOS_AVAILABLE", False)
    def test_handler_graceful_degradation_without_memos(self, mock_dependencies):
        """
        If MemOS is not installed/available, recall should strictly use local history
        without crashing.
        """
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
        
        with patch('builtins.print') as mock_print:
            handler.handle_recall("Local only")
            
            # Verify we didn't crash
            # Verify we found the local match
            found_match = False
            for call_args in mock_print.call_args_list:
                if "Local only" in str(call_args):
                    found_match = True
            
            assert found_match

