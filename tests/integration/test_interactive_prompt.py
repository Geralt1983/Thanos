"""
Integration tests for interactive prompt with token/cost display.

These tests validate that the prompt updates correctly during interactive sessions
with real-time token usage and cost estimates. Uses mock orchestrator and session
stats to simulate real interactive scenarios.

Tests can be run with pytest markers:
  - pytest -m integration         # Run all integration tests
  - pytest tests/integration/test_interactive_prompt.py -v  # Run just prompt tests

Test Coverage:
- Prompt updates after each interaction in all display modes
- Session statistics progression (tokens, cost, duration)
- Agent switching with prompt updates
- Slash command integration with prompt state
- Configuration enable/disable functionality
- Error handling and graceful degradation
- Multi-message conversation flows
- Cost threshold color coding during session
"""

from pathlib import Path
import sys
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta

import pytest


# Ensure Thanos is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.thanos_interactive import ThanosInteractive
from Tools.prompt_formatter import PromptFormatter
from Tools.session_manager import SessionManager
from Tools.command_router import CommandAction


# ========================================================================
# Pytest Markers and Fixtures
# ========================================================================

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_orchestrator():
    """Create mock orchestrator for testing"""
    orchestrator = MagicMock()
    orchestrator.agents = {
        "ops": MagicMock(name="Ops"),
        "coach": MagicMock(name="Coach"),
        "strategy": MagicMock(name="Strategy"),
    }
    orchestrator.chat.return_value = "Test response"
    return orchestrator


@pytest.fixture
def mock_state_reader():
    """Create mock state reader"""
    state_reader = MagicMock()
    state_reader.get_quick_context.return_value = {
        "focus": None,
        "top3": []
    }
    return state_reader


# =============================================================================
# Test Prompt Updates During Interactive Sessions
# =============================================================================


class TestPromptUpdatesWithMockStats:
    """Test that prompt displays update correctly as session stats change"""

    def test_prompt_progression_in_compact_mode(self, mock_orchestrator, tmp_path):
        """Test prompt updates with increasing tokens/cost in compact mode"""

        # Create ThanosInteractive with temporary history directory
        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Verify initial state: no tokens, no cost
            # Note: When both tokens and cost are 0, formatter returns default prompt
            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="compact")
            assert prompt == "Thanos> "  # Falls back to default when no usage

            # Simulate first interaction: user message + assistant response
            interactive.session_manager.add_user_message("Hello", tokens=50)
            interactive.session_manager.add_assistant_message("Hi there!", tokens=100)
            interactive.session_manager.session.total_cost = 0.01

            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="compact")
            # Check for content, accounting for color codes
            assert "150" in prompt
            assert "$0.01" in prompt
            assert "Thanos> " in prompt

            # Simulate second interaction: more tokens, higher cost
            interactive.session_manager.add_user_message("What's my schedule?", tokens=200)
            interactive.session_manager.add_assistant_message("Here's your schedule...", tokens=500)
            interactive.session_manager.session.total_cost = 0.05

            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="compact")
            # Total: 850 tokens
            assert "850" in prompt
            assert "$0.05" in prompt
            assert "Thanos> " in prompt

            # Simulate third interaction: crosses 1K threshold
            interactive.session_manager.add_user_message("Tell me more", tokens=300)
            interactive.session_manager.add_assistant_message("Sure, here's more detail...", tokens=800)
            interactive.session_manager.session.total_cost = 0.15

            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="compact")
            # Total: 1950 tokens -> 1.9K
            assert "1.9K" in prompt
            assert "$0.15" in prompt
            assert "Thanos> " in prompt

    def test_prompt_progression_in_standard_mode(self, mock_orchestrator, tmp_path):
        """Test prompt updates with duration in standard mode"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Mock session start time to control duration
            start_time = datetime.now() - timedelta(minutes=15)
            interactive.session_manager.session.started_at = start_time

            # Add some interaction
            interactive.session_manager.add_user_message("Hello", tokens=50)
            interactive.session_manager.add_assistant_message("Hi!", tokens=100)
            interactive.session_manager.session.total_cost = 0.02

            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="standard")

            # Should show duration (15m), tokens (150), and cost ($0.02)
            assert "15m" in prompt
            assert "150 tokens" in prompt
            assert "$0.02" in prompt

    def test_prompt_progression_in_verbose_mode(self, mock_orchestrator, tmp_path):
        """Test prompt updates with full details in verbose mode"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Mock session start time
            start_time = datetime.now() - timedelta(minutes=45)
            interactive.session_manager.session.started_at = start_time

            # Add multiple interactions
            interactive.session_manager.add_user_message("First message", tokens=100)
            interactive.session_manager.add_assistant_message("First response", tokens=200)
            interactive.session_manager.add_user_message("Second message", tokens=150)
            interactive.session_manager.add_assistant_message("Second response", tokens=300)
            interactive.session_manager.session.total_cost = 0.08

            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="verbose")

            # Should show duration, message count, input/output tokens, cost
            assert "45m" in prompt
            assert "4 msgs" in prompt  # 4 messages total
            assert "250 in" in prompt  # 100 + 150 input tokens
            assert "500 out" in prompt  # 200 + 300 output tokens
            assert "$0.08" in prompt

    def test_cost_threshold_color_progression(self, mock_orchestrator, tmp_path):
        """Test prompt color changes as cost crosses thresholds"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Start with low cost (green threshold: <= $0.50)
            interactive.session_manager.add_user_message("Message 1", tokens=1000)
            interactive.session_manager.add_assistant_message("Response 1", tokens=2000)
            interactive.session_manager.session.total_cost = 0.30

            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="compact")
            # With colors enabled (default), should contain green ANSI code
            assert "\033[32m" in prompt  # Green color code
            assert "$0.30" in prompt

            # Increase to medium cost (yellow threshold: $0.51 - $2.00)
            interactive.session_manager.add_user_message("Message 2", tokens=5000)
            interactive.session_manager.add_assistant_message("Response 2", tokens=8000)
            interactive.session_manager.session.total_cost = 1.20

            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="compact")
            # Should contain yellow ANSI code
            assert "\033[33m" in prompt  # Yellow color code
            assert "$1.20" in prompt

            # Increase to high cost (red threshold: > $2.00)
            interactive.session_manager.add_user_message("Message 3", tokens=10000)
            interactive.session_manager.add_assistant_message("Response 3", tokens=15000)
            interactive.session_manager.session.total_cost = 2.50

            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="compact")
            # Should contain red ANSI code
            assert "\033[31m" in prompt  # Red color code
            assert "$2.50" in prompt


# =============================================================================
# Test Integration with Command Router
# =============================================================================


class TestPromptWithCommandIntegration:
    """Test prompt updates correctly with slash commands"""

    def test_prompt_mode_switching_via_command(self, mock_orchestrator, tmp_path):
        """Test /prompt command changes display mode dynamically"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Add some session data
            interactive.session_manager.add_user_message("Test", tokens=500)
            interactive.session_manager.add_assistant_message("Response", tokens=700)
            interactive.session_manager.session.total_cost = 0.10

            # Initial mode should be default from config
            initial_mode = interactive.command_router.current_prompt_mode
            stats = interactive.session_manager.get_stats()
            prompt_initial = interactive.prompt_formatter.format(stats, mode=initial_mode)

            # Switch to verbose mode
            interactive.command_router.route_command("/prompt verbose")
            assert interactive.command_router.current_prompt_mode == "verbose"

            prompt_verbose = interactive.prompt_formatter.format(
                stats,
                mode=interactive.command_router.current_prompt_mode
            )
            # Verbose should include "msgs"
            assert "msgs" in prompt_verbose

            # Switch to compact mode
            interactive.command_router.route_command("/prompt compact")
            assert interactive.command_router.current_prompt_mode == "compact"

            prompt_compact = interactive.prompt_formatter.format(
                stats,
                mode=interactive.command_router.current_prompt_mode
            )
            # Compact should NOT include "msgs" or duration
            assert "msgs" not in prompt_compact
            # Check for content, accounting for color codes
            assert "1.2K" in prompt_compact
            assert "$0.10" in prompt_compact
            assert "Thanos> " in prompt_compact

    def test_prompt_persists_after_clear_command(self, mock_orchestrator, tmp_path):
        """Test prompt still shows cumulative stats after /clear"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Add messages and build up stats
            interactive.session_manager.add_user_message("Message 1", tokens=500)
            interactive.session_manager.add_assistant_message("Response 1", tokens=700)
            interactive.session_manager.session.total_cost = 0.10

            # Get stats before clear
            stats_before = interactive.session_manager.get_stats()
            assert stats_before["total_input_tokens"] == 500
            assert stats_before["total_output_tokens"] == 700
            assert stats_before["total_cost"] == 0.10

            # Clear history (but stats remain cumulative)
            interactive.command_router.route_command("/clear")

            # Get stats after clear - history is empty but cumulative stats remain
            stats_after = interactive.session_manager.get_stats()
            assert stats_after["message_count"] == 0  # History cleared
            assert stats_after["total_input_tokens"] == 500  # Cumulative preserved
            assert stats_after["total_output_tokens"] == 700  # Cumulative preserved
            assert stats_after["total_cost"] == 0.10  # Cumulative preserved

            # Prompt should still show cumulative stats
            prompt = interactive.prompt_formatter.format(stats_after, mode="compact")
            # Check for content, accounting for color codes
            assert "1.2K" in prompt
            assert "$0.10" in prompt
            assert "Thanos> " in prompt

    def test_agent_switching_updates_session_context(self, mock_orchestrator, tmp_path):
        """Test agent switching updates session manager correctly"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Initial agent should be ops
            assert interactive.session_manager.session.agent == "ops"

            # Switch to coach agent using correct command
            interactive.command_router.route_command("/agent coach")
            assert interactive.command_router.current_agent == "coach"

            # Session stats should reflect current agent
            stats = interactive.session_manager.get_stats()
            assert stats["current_agent"] == "ops"  # Session manager maintains its own agent

            # Explicitly switch in session manager (as would happen in real flow)
            interactive.session_manager.switch_agent("coach")
            stats = interactive.session_manager.get_stats()
            assert stats["current_agent"] == "coach"


# =============================================================================
# Test Configuration Integration
# =============================================================================


class TestPromptConfigurationIntegration:
    """Test prompt behavior with different configuration settings"""

    def test_disabled_prompt_shows_default(self, mock_orchestrator, tmp_path):
        """Test prompt falls back to default when disabled in config"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            # Create formatter with disabled stats
            formatter = PromptFormatter(enable_colors=False)
            formatter.enabled = False  # Disable prompt stats

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.prompt_formatter = formatter
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Add session data
            interactive.session_manager.add_user_message("Test", tokens=1000)
            interactive.session_manager.add_assistant_message("Response", tokens=1500)
            interactive.session_manager.session.total_cost = 0.20

            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="compact")

            # When disabled, should show default prompt without stats
            assert prompt == "Thanos> "
            assert "2.5K" not in prompt
            assert "$0.20" not in prompt

    def test_custom_color_thresholds(self, mock_orchestrator, tmp_path):
        """Test prompt uses custom color thresholds from config"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            # Create formatter with custom thresholds
            # Low: $1.00, Medium: $5.00
            formatter = PromptFormatter(
                low_cost_threshold=1.00,
                medium_cost_threshold=5.00
            )

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.prompt_formatter = formatter
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Test cost at $0.80 (should be green with custom threshold of $1.00)
            interactive.session_manager.add_user_message("Test", tokens=5000)
            interactive.session_manager.add_assistant_message("Response", tokens=8000)
            interactive.session_manager.session.total_cost = 0.80

            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="compact")
            assert "\033[32m" in prompt  # Green (below $1.00 threshold)

            # Test cost at $3.00 (should be yellow: between $1.00 and $5.00)
            interactive.session_manager.session.total_cost = 3.00
            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="compact")
            assert "\033[33m" in prompt  # Yellow

            # Test cost at $6.00 (should be red: above $5.00 threshold)
            interactive.session_manager.session.total_cost = 6.00
            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="compact")
            assert "\033[31m" in prompt  # Red


# =============================================================================
# Test Multi-Message Conversation Flows
# =============================================================================


class TestMultiMessageConversationFlows:
    """Test prompt behavior in realistic multi-message conversations"""

    def test_realistic_conversation_flow(self, mock_orchestrator, tmp_path):
        """Test prompt updates through a realistic multi-turn conversation"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Simulate realistic conversation with varying token counts
            conversation = [
                ("Hello", 10, "Hi there!", 20, 0.002),
                ("What's on my schedule today?", 50, "Here's your schedule...", 200, 0.015),
                ("Can you summarize that?", 40, "Sure, you have 3 meetings...", 80, 0.025),
                ("Tell me about the first meeting", 60, "The first meeting is...", 150, 0.040),
                ("What should I prepare?", 40, "You should prepare...", 180, 0.060),
            ]

            for i, (user_msg, user_tokens, asst_msg, asst_tokens, total_cost) in enumerate(conversation):
                # Add messages
                interactive.session_manager.add_user_message(user_msg, tokens=user_tokens)
                interactive.session_manager.add_assistant_message(asst_msg, tokens=asst_tokens)
                interactive.session_manager.session.total_cost = total_cost

                # Check prompt reflects current state
                stats = interactive.session_manager.get_stats()
                prompt = interactive.prompt_formatter.format(stats, mode="compact")

                # Verify message count
                assert stats["message_count"] == (i + 1) * 2  # Each iteration adds 2 messages

                # Verify cumulative tokens
                expected_input = sum(t[1] for t in conversation[:i+1])
                expected_output = sum(t[3] for t in conversation[:i+1])
                assert stats["total_input_tokens"] == expected_input
                assert stats["total_output_tokens"] == expected_output

                # Verify cost is shown in prompt
                assert f"${total_cost:.2f}" in prompt

            # Final state check
            final_stats = interactive.session_manager.get_stats()
            assert final_stats["message_count"] == 10  # 5 turns * 2 messages
            assert final_stats["total_input_tokens"] == 200  # Sum of all user tokens
            assert final_stats["total_output_tokens"] == 630  # Sum of all assistant tokens
            assert final_stats["total_cost"] == 0.060

    def test_long_session_with_history_trimming(self, mock_orchestrator, tmp_path):
        """Test prompt stats remain accurate even when history is trimmed"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Add messages beyond MAX_HISTORY (100) to trigger trimming
            for i in range(60):  # 60 user messages + 60 assistant = 120 total
                interactive.session_manager.add_user_message(
                    f"Message {i}",
                    tokens=100
                )
                interactive.session_manager.add_assistant_message(
                    f"Response {i}",
                    tokens=150
                )

            # Update total cost
            interactive.session_manager.session.total_cost = 3.50

            stats = interactive.session_manager.get_stats()

            # History should be trimmed to 100 messages
            assert stats["message_count"] == 100

            # But cumulative tokens should reflect ALL messages (not just trimmed history)
            assert stats["total_input_tokens"] == 60 * 100  # 6000 tokens
            assert stats["total_output_tokens"] == 60 * 150  # 9000 tokens

            # Prompt should show cumulative stats
            prompt = interactive.prompt_formatter.format(stats, mode="compact")
            assert "15.0K" in prompt  # 15K total tokens
            assert "$3.50" in prompt


# =============================================================================
# Test Error Handling and Edge Cases
# =============================================================================


class TestErrorHandlingInIntegration:
    """Test graceful error handling in integrated system"""

    def test_prompt_with_missing_stats_fields(self, mock_orchestrator, tmp_path):
        """Test prompt handles missing or malformed stats gracefully"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Test with incomplete stats (missing some fields)
            partial_stats = {
                "total_input_tokens": 100,
                "total_output_tokens": 200,
                # Missing total_cost
                # Missing duration_minutes
            }

            # Should not crash, should use defaults
            prompt = interactive.prompt_formatter.format(partial_stats, mode="compact")
            assert "Thanos> " in prompt

    def test_prompt_with_zero_tokens_nonzero_cost(self, mock_orchestrator, tmp_path):
        """Test edge case of zero tokens but non-zero cost"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Set cost without tokens (edge case, but should handle gracefully)
            # Note: Need at least some tokens to show the prompt stats
            interactive.session_manager.add_user_message("test", tokens=0)  # 0 tokens but message exists
            interactive.session_manager.session.total_cost = 0.50

            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="compact")

            # Should show both zero tokens and cost (cost makes it display)
            assert "0" in prompt  # Zero tokens shown
            assert "$0.50" in prompt  # Cost shown
            assert "Thanos> " in prompt

    def test_prompt_formatter_with_none_stats(self, mock_orchestrator):
        """Test formatter handles None stats dict gracefully"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)

            # Test with None stats
            prompt = interactive.prompt_formatter.format(None, mode="compact")
            assert prompt == "Thanos> "

            # Test with empty dict
            prompt = interactive.prompt_formatter.format({}, mode="compact")
            assert prompt == "Thanos> "


# =============================================================================
# Test Session Duration Tracking
# =============================================================================


class TestSessionDurationTracking:
    """Test session duration is tracked and displayed correctly"""

    def test_duration_increases_over_time(self, mock_orchestrator, tmp_path):
        """Test duration increases as session progresses"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Set session start to 2 hours ago
            start_time = datetime.now() - timedelta(hours=2, minutes=15)
            interactive.session_manager.session.started_at = start_time

            # Add some messages
            interactive.session_manager.add_user_message("Test", tokens=500)
            interactive.session_manager.add_assistant_message("Response", tokens=700)
            interactive.session_manager.session.total_cost = 0.10

            stats = interactive.session_manager.get_stats()
            prompt = interactive.prompt_formatter.format(stats, mode="standard")

            # Should show duration in hours (2h15m)
            assert "2h15m" in prompt or "135m" in prompt  # Either format acceptable

    def test_duration_formatting_at_boundaries(self, mock_orchestrator, tmp_path):
        """Test duration formatting at various time boundaries"""

        with patch("Tools.thanos_interactive.StateReader") as mock_state_reader_cls:
            mock_state_reader = MagicMock()
            mock_state_reader.get_quick_context.return_value = {"focus": None, "top3": []}
            mock_state_reader_cls.return_value = mock_state_reader

            interactive = ThanosInteractive(mock_orchestrator)
            interactive.session_manager.history_dir = tmp_path / "sessions"

            # Add some token usage so prompt displays (not just default)
            interactive.session_manager.add_user_message("Test", tokens=500)
            interactive.session_manager.add_assistant_message("Response", tokens=700)
            interactive.session_manager.session.total_cost = 0.10

            test_cases = [
                (timedelta(minutes=0), "0m"),
                (timedelta(minutes=5), "5m"),
                (timedelta(minutes=59), "59m"),
                (timedelta(hours=1), "1h"),
                (timedelta(hours=1, minutes=30), "1h30m"),
                (timedelta(hours=2), "2h"),
            ]

            for delta, expected_in_prompt in test_cases:
                start_time = datetime.now() - delta
                interactive.session_manager.session.started_at = start_time

                stats = interactive.session_manager.get_stats()
                prompt = interactive.prompt_formatter.format(stats, mode="standard")

                # Should contain the expected duration format
                assert expected_in_prompt in prompt, f"Expected '{expected_in_prompt}' in prompt for delta {delta}"
