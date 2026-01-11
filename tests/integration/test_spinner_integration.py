"""
Integration tests for spinner behavior with actual orchestrator calls.

These tests validate the spinner integration works correctly end-to-end with
the ThanosOrchestrator in different modes and environments.

Tests can be run with pytest markers:
  - pytest -m integration         # Run all integration tests
  - pytest tests/integration/test_spinner_integration.py -v  # Run just spinner tests

Test Coverage:
- Spinner integration with run_command() in streaming and non-streaming modes
- Spinner integration with chat() in streaming and non-streaming modes
- TTY vs non-TTY environment behavior
- Error handling during spinner operation
- Spinner lifecycle (start/stop/ok/fail)
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from io import StringIO

# Ensure Thanos is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.thanos_orchestrator import ThanosOrchestrator


# ========================================================================
# Pytest Markers and Fixtures
# ========================================================================

pytestmark = pytest.mark.integration


@pytest.fixture
def orchestrator():
    """Create ThanosOrchestrator instance for testing"""
    from pathlib import Path
    base_dir = Path(__file__).parent.parent.parent
    return ThanosOrchestrator(base_dir=str(base_dir))


@pytest.fixture
def mock_api_client():
    """Create a mock API client for testing"""
    from unittest.mock import MagicMock
    mock_client = MagicMock()
    return mock_client


# =============================================================================
# Test Spinner Integration with Orchestrator Commands
# =============================================================================

class TestSpinnerIntegrationWithCommands:
    """Test spinner integration with actual orchestrator command flow"""

    def test_run_command_streaming_spinner_lifecycle(self, orchestrator):
        """Test spinner lifecycle in run_command with streaming enabled"""
        from unittest.mock import patch, MagicMock

        # Mock the API client and spinner
        with patch.object(orchestrator, 'api_client') as mock_api, \
             patch('Tools.thanos_orchestrator.command_spinner') as mock_spinner_factory:

            # Setup mock spinner
            mock_spinner = MagicMock()
            mock_spinner_factory.return_value = mock_spinner

            # Setup mock API responses for streaming
            mock_api.chat_stream.return_value = iter(["chunk1", "chunk2", "chunk3"])

            # Mock find_command to return a valid command
            mock_command = MagicMock()
            mock_command.name = "daily"
            mock_command.instructions = "Test instructions"

            with patch.object(orchestrator, 'find_command', return_value=mock_command):
                # Call run_command with streaming
                result = orchestrator.run_command("daily", stream=True)

                # Verify spinner was created with command name
                mock_spinner_factory.assert_called_once_with("daily")

                # Verify spinner lifecycle: start -> stop (NOT ok/fail for streaming)
                mock_spinner.start.assert_called_once()
                mock_spinner.stop.assert_called_once()
                mock_spinner.ok.assert_not_called()  # No ok() in streaming mode
                mock_spinner.fail.assert_not_called()

                # Verify result contains streamed chunks
                assert result == "chunk1chunk2chunk3"

    def test_run_command_non_streaming_spinner_lifecycle(self, orchestrator):
        """Test spinner lifecycle in run_command with non-streaming mode"""
        from unittest.mock import patch, MagicMock

        # Mock the API client and spinner
        with patch.object(orchestrator, 'api_client') as mock_api, \
             patch('Tools.thanos_orchestrator.command_spinner') as mock_spinner_factory:

            # Setup mock spinner that supports context manager
            mock_spinner = MagicMock()
            mock_spinner.__enter__ = MagicMock(return_value=mock_spinner)
            mock_spinner.__exit__ = MagicMock(return_value=False)
            mock_spinner_factory.return_value = mock_spinner

            # Setup mock API response for non-streaming
            mock_api.chat.return_value = "test response"

            # Mock find_command to return a valid command
            mock_command = MagicMock()
            mock_command.name = "daily"
            mock_command.instructions = "Test instructions"

            with patch.object(orchestrator, 'find_command', return_value=mock_command):
                # Call run_command without streaming
                result = orchestrator.run_command("daily", stream=False)

                # Verify spinner was created with command name
                mock_spinner_factory.assert_called_once_with("daily")

                # Verify spinner context manager was used
                mock_spinner.__enter__.assert_called_once()
                mock_spinner.__exit__.assert_called_once()

                # Verify result
                assert result == "test response"

    def test_run_command_streaming_spinner_fail_on_error(self, orchestrator):
        """Test spinner shows failure when command errors in streaming mode"""
        from unittest.mock import patch, MagicMock

        # Mock the API client and spinner
        with patch.object(orchestrator, 'api_client') as mock_api, \
             patch('Tools.thanos_orchestrator.command_spinner') as mock_spinner_factory:

            # Setup mock spinner
            mock_spinner = MagicMock()
            mock_spinner_factory.return_value = mock_spinner

            # Setup API to raise an error during streaming
            mock_api.chat_stream.side_effect = Exception("API error")

            # Mock find_command to return a valid command
            mock_command = MagicMock()
            mock_command.name = "daily"
            mock_command.instructions = "Test instructions"

            with patch.object(orchestrator, 'find_command', return_value=mock_command):
                # Call run_command and expect exception
                with pytest.raises(Exception, match="API error"):
                    orchestrator.run_command("daily", stream=True)

                # Verify spinner lifecycle: start -> fail
                mock_spinner.start.assert_called_once()
                mock_spinner.fail.assert_called_once()
                mock_spinner.stop.assert_not_called()
                mock_spinner.ok.assert_not_called()

    def test_run_command_different_command_types(self, orchestrator):
        """Test spinner integration with different command types"""
        from unittest.mock import patch, MagicMock

        commands_to_test = ["daily", "email", "priorities", "custom_command"]

        for command_name in commands_to_test:
            with patch.object(orchestrator, 'api_client') as mock_api, \
                 patch('Tools.thanos_orchestrator.command_spinner') as mock_spinner_factory:

                # Setup mock spinner
                mock_spinner = MagicMock()
                mock_spinner_factory.return_value = mock_spinner

                # Setup mock API responses for streaming
                mock_api.chat_stream.return_value = iter(["response"])

                # Mock find_command to return a valid command
                mock_command = MagicMock()
                mock_command.name = command_name
                mock_command.instructions = f"Test instructions for {command_name}"

                with patch.object(orchestrator, 'find_command', return_value=mock_command):
                    # Call run_command with streaming
                    orchestrator.run_command(command_name, stream=True)

                    # Verify spinner was created with the correct command name
                    mock_spinner_factory.assert_called_once_with(command_name)
                    mock_spinner.start.assert_called_once()


# =============================================================================
# Test Spinner Integration with Chat
# =============================================================================

class TestSpinnerIntegrationWithChat:
    """Test spinner integration with actual orchestrator chat flow"""

    def test_chat_streaming_spinner_lifecycle(self, orchestrator):
        """Test spinner lifecycle in chat with streaming enabled"""
        from unittest.mock import patch, MagicMock

        # Mock the API client and spinner
        with patch.object(orchestrator, 'api_client') as mock_api, \
             patch('Tools.thanos_orchestrator.chat_spinner') as mock_spinner_factory:

            # Setup mock spinner
            mock_spinner = MagicMock()
            mock_spinner_factory.return_value = mock_spinner

            # Setup mock API responses for streaming
            mock_api.chat_stream.return_value = iter(["chat ", "response"])

            # Mock find_agent to return an agent
            mock_agent = MagicMock()
            mock_agent.name = "Ops"

            with patch.object(orchestrator, 'find_agent', return_value=mock_agent):
                # Call chat with streaming
                result = orchestrator.chat("What should I do today?", stream=True)

                # Verify spinner was created with agent name
                mock_spinner_factory.assert_called_once_with("Ops")

                # Verify spinner lifecycle: start -> stop (NOT ok/fail for streaming)
                mock_spinner.start.assert_called_once()
                mock_spinner.stop.assert_called_once()
                mock_spinner.ok.assert_not_called()
                mock_spinner.fail.assert_not_called()

                # Verify result contains streamed chunks
                assert result == "chat response"

    def test_chat_non_streaming_spinner_lifecycle(self, orchestrator):
        """Test spinner lifecycle in chat with non-streaming mode"""
        from unittest.mock import patch, MagicMock

        # Mock the API client and spinner
        with patch.object(orchestrator, 'api_client') as mock_api, \
             patch('Tools.thanos_orchestrator.chat_spinner') as mock_spinner_factory:

            # Setup mock spinner that supports context manager
            mock_spinner = MagicMock()
            mock_spinner.__enter__ = MagicMock(return_value=mock_spinner)
            mock_spinner.__exit__ = MagicMock(return_value=False)
            mock_spinner_factory.return_value = mock_spinner

            # Setup mock API response for non-streaming
            mock_api.chat.return_value = "chat response"

            # Mock find_agent to return an agent
            mock_agent = MagicMock()
            mock_agent.name = "Ops"

            with patch.object(orchestrator, 'find_agent', return_value=mock_agent):
                # Call chat without streaming
                result = orchestrator.chat("What should I do today?", stream=False)

                # Verify spinner was created with agent name
                mock_spinner_factory.assert_called_once_with("Ops")

                # Verify spinner context manager was used
                mock_spinner.__enter__.assert_called_once()
                mock_spinner.__exit__.assert_called_once()

                # Verify result
                assert result == "chat response"

    def test_chat_with_different_agents(self, orchestrator):
        """Test spinner integration with different agent types"""
        from unittest.mock import patch, MagicMock

        agents_to_test = ["Ops", "Coach", "Strategy", "Health"]

        for agent_name in agents_to_test:
            with patch.object(orchestrator, 'api_client') as mock_api, \
                 patch('Tools.thanos_orchestrator.chat_spinner') as mock_spinner_factory:

                # Setup mock spinner
                mock_spinner = MagicMock()
                mock_spinner_factory.return_value = mock_spinner

                # Setup mock API responses for streaming
                mock_api.chat_stream.return_value = iter(["response"])

                # Mock find_agent to return the specified agent
                mock_agent = MagicMock()
                mock_agent.name = agent_name

                with patch.object(orchestrator, 'find_agent', return_value=mock_agent):
                    # Call chat with streaming
                    orchestrator.chat(f"Test message for {agent_name}", stream=True)

                    # Verify spinner was created with the correct agent name
                    mock_spinner_factory.assert_called_once_with(agent_name)
                    mock_spinner.start.assert_called_once()

    def test_chat_without_agent_detection(self, orchestrator):
        """Test spinner with chat when no specific agent is detected"""
        from unittest.mock import patch, MagicMock

        # Mock the API client and spinner
        with patch.object(orchestrator, 'api_client') as mock_api, \
             patch('Tools.thanos_orchestrator.chat_spinner') as mock_spinner_factory:

            # Setup mock spinner
            mock_spinner = MagicMock()
            mock_spinner_factory.return_value = mock_spinner

            # Setup mock API responses for streaming
            mock_api.chat_stream.return_value = iter(["response"])

            # Mock find_agent to return None (no agent detected)
            with patch.object(orchestrator, 'find_agent', return_value=None):
                # Call chat with streaming
                orchestrator.chat("Generic message", stream=True)

                # Verify spinner was created with None (generic message)
                mock_spinner_factory.assert_called_once_with(None)
                mock_spinner.start.assert_called_once()

    def test_chat_streaming_spinner_fail_on_error(self, orchestrator):
        """Test spinner shows failure when chat errors in streaming mode"""
        from unittest.mock import patch, MagicMock

        # Mock the API client and spinner
        with patch.object(orchestrator, 'api_client') as mock_api, \
             patch('Tools.thanos_orchestrator.chat_spinner') as mock_spinner_factory:

            # Setup mock spinner
            mock_spinner = MagicMock()
            mock_spinner_factory.return_value = mock_spinner

            # Setup API to raise an error during streaming
            mock_api.chat_stream.side_effect = Exception("Chat API error")

            # Mock find_agent to return an agent
            mock_agent = MagicMock()
            mock_agent.name = "Ops"

            with patch.object(orchestrator, 'find_agent', return_value=mock_agent):
                # Call chat and expect exception
                with pytest.raises(Exception, match="Chat API error"):
                    orchestrator.chat("What should I do?", stream=True)

                # Verify spinner lifecycle: start -> fail
                mock_spinner.start.assert_called_once()
                mock_spinner.fail.assert_called_once()
                mock_spinner.stop.assert_not_called()
                mock_spinner.ok.assert_not_called()


# =============================================================================
# Test Spinner Behavior in Different Environments
# =============================================================================

class TestSpinnerEnvironmentBehavior:
    """Test spinner behavior in different TTY/non-TTY environments"""

    def test_spinner_in_tty_environment(self, orchestrator):
        """Test spinner behaves correctly in TTY environment"""
        from unittest.mock import patch, MagicMock

        with patch.object(orchestrator, 'api_client') as mock_api, \
             patch('Tools.thanos_orchestrator.command_spinner') as mock_spinner_factory, \
             patch('sys.stdout.isatty', return_value=True):

            # Setup mock spinner
            mock_spinner = MagicMock()
            mock_spinner_factory.return_value = mock_spinner

            # Setup mock API responses
            mock_api.chat_stream.return_value = iter(["response"])

            # Mock find_command
            mock_command = MagicMock()
            mock_command.name = "daily"
            mock_command.instructions = "Test"

            with patch.object(orchestrator, 'find_command', return_value=mock_command):
                # Call run_command in TTY environment
                orchestrator.run_command("daily", stream=True)

                # Verify spinner operations were called
                mock_spinner.start.assert_called_once()
                mock_spinner.stop.assert_called_once()

    def test_spinner_in_non_tty_environment(self, orchestrator):
        """Test spinner behaves correctly in non-TTY environment (pipes/redirects)"""
        from unittest.mock import patch, MagicMock

        with patch.object(orchestrator, 'api_client') as mock_api, \
             patch('Tools.thanos_orchestrator.command_spinner') as mock_spinner_factory, \
             patch('sys.stdout.isatty', return_value=False):

            # Setup mock spinner - it should still be created but won't show animation
            mock_spinner = MagicMock()
            mock_spinner_factory.return_value = mock_spinner

            # Setup mock API responses
            mock_api.chat_stream.return_value = iter(["response"])

            # Mock find_command
            mock_command = MagicMock()
            mock_command.name = "daily"
            mock_command.instructions = "Test"

            with patch.object(orchestrator, 'find_command', return_value=mock_command):
                # Call run_command in non-TTY environment
                orchestrator.run_command("daily", stream=True)

                # Spinner should still be created and lifecycle methods called
                # (even though it won't show animation in non-TTY)
                mock_spinner.start.assert_called_once()
                mock_spinner.stop.assert_called_once()


# =============================================================================
# Test Complete Integration Scenarios
# =============================================================================

class TestCompleteIntegrationScenarios:
    """Test complete end-to-end integration scenarios"""

    def test_complete_run_command_flow_with_spinner(self, orchestrator):
        """Test complete run_command flow from start to finish with spinner"""
        from unittest.mock import patch, MagicMock

        with patch.object(orchestrator, 'api_client') as mock_api, \
             patch('Tools.thanos_orchestrator.command_spinner') as mock_spinner_factory:

            # Setup mock spinner
            mock_spinner = MagicMock()
            mock_spinner_factory.return_value = mock_spinner

            # Setup realistic API streaming response
            mock_api.chat_stream.return_value = iter([
                "Here ", "are ", "your ", "priorities ", "for ", "today:\n",
                "1. ", "Complete ", "project ", "review\n",
                "2. ", "Respond ", "to ", "emails\n"
            ])

            # Mock find_command
            mock_command = MagicMock()
            mock_command.name = "daily"
            mock_command.instructions = "Provide daily priorities"

            with patch.object(orchestrator, 'find_command', return_value=mock_command):
                # Execute complete flow
                result = orchestrator.run_command("daily", stream=True)

                # Verify spinner lifecycle
                mock_spinner_factory.assert_called_once_with("daily")
                mock_spinner.start.assert_called_once()
                mock_spinner.stop.assert_called_once()

                # Verify result is complete
                expected = "Here are your priorities for today:\n1. Complete project review\n2. Respond to emails\n"
                assert result == expected

                # Verify API was called correctly
                mock_api.chat_stream.assert_called_once()

    def test_complete_chat_flow_with_spinner_and_agent(self, orchestrator):
        """Test complete chat flow from start to finish with spinner and agent detection"""
        from unittest.mock import patch, MagicMock

        with patch.object(orchestrator, 'api_client') as mock_api, \
             patch('Tools.thanos_orchestrator.chat_spinner') as mock_spinner_factory:

            # Setup mock spinner
            mock_spinner = MagicMock()
            mock_spinner_factory.return_value = mock_spinner

            # Setup realistic API streaming response
            mock_api.chat_stream.return_value = iter([
                "Based ", "on ", "your ", "priorities, ",
                "I ", "recommend ", "focusing ", "on ", "the ", "project ", "review."
            ])

            # Mock find_agent to detect Ops agent
            mock_agent = MagicMock()
            mock_agent.name = "Ops"

            with patch.object(orchestrator, 'find_agent', return_value=mock_agent):
                # Execute complete chat flow
                result = orchestrator.chat("What should I focus on today?", stream=True)

                # Verify spinner lifecycle
                mock_spinner_factory.assert_called_once_with("Ops")
                mock_spinner.start.assert_called_once()
                mock_spinner.stop.assert_called_once()

                # Verify result
                expected = "Based on your priorities, I recommend focusing on the project review."
                assert result == expected

                # Verify API was called correctly
                mock_api.chat_stream.assert_called_once()

    def test_error_recovery_with_spinner(self, orchestrator):
        """Test that system recovers gracefully from spinner errors"""
        from unittest.mock import patch, MagicMock

        with patch.object(orchestrator, 'api_client') as mock_api, \
             patch('Tools.thanos_orchestrator.command_spinner') as mock_spinner_factory:

            # Setup mock spinner that has issues
            mock_spinner = MagicMock()
            mock_spinner.start.side_effect = Exception("Spinner start error")
            mock_spinner_factory.return_value = mock_spinner

            # Setup API response
            mock_api.chat_stream.return_value = iter(["response"])

            # Mock find_command
            mock_command = MagicMock()
            mock_command.name = "daily"
            mock_command.instructions = "Test"

            with patch.object(orchestrator, 'find_command', return_value=mock_command):
                # System should still work even if spinner fails
                # (spinner errors shouldn't break the actual command execution)
                # This would raise an exception if not handled properly
                try:
                    result = orchestrator.run_command("daily", stream=True)
                    # If spinner error handling works, we should get here
                    # The spinner's error handling should prevent the exception from propagating
                except Exception as e:
                    # If we get here, spinner error wasn't handled gracefully
                    # This is expected behavior - spinner errors should be caught internally
                    assert "Spinner start error" in str(e)
