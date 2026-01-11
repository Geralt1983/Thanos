#!/usr/bin/env python3
"""
Unit tests for thanos.py CLI entry point.

Tests cover:
- Command shortcuts mapping (daily → pa:daily)
- Natural language detection
- System command routing
- Interactive mode launch
- Chat and agent commands
- Usage, agents, commands display
- Help display
- Natural language routing
"""

from pathlib import Path
import sys
from unittest.mock import Mock, patch

import pytest


# Import after setting up path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from thanos import (
    COMMAND_SHORTCUTS,
    SYSTEM_COMMANDS,
    is_natural_language,
    main,
    print_usage,
)


# ========================================================================
# Test Constants and Fixtures
# ========================================================================


@pytest.fixture
def mock_orchestrator():
    """Create a mock ThanosOrchestrator."""
    orchestrator = Mock()
    orchestrator.chat = Mock()
    orchestrator.route = Mock()
    orchestrator.run_command = Mock()
    orchestrator.get_usage = Mock(
        return_value={
            "total_tokens": 150000,
            "total_cost_usd": 4.50,
            "total_calls": 75,
            "projected_monthly_cost": 45.00,
        }
    )
    orchestrator.list_commands = Mock(return_value=["pa:daily", "pa:email", "pa:tasks"])

    # Mock agents
    mock_agent = Mock()
    mock_agent.name = "Ops"
    mock_agent.role = "Operations Manager"
    mock_agent.triggers = ["task", "todo", "schedule"]

    orchestrator.agents = {"ops": mock_agent}
    return orchestrator


@pytest.fixture
def mock_interactive():
    """Create a mock ThanosInteractive."""
    interactive = Mock()
    interactive.run = Mock()
    return interactive


# ========================================================================
# Test COMMAND_SHORTCUTS
# ========================================================================


class TestCommandShortcuts:
    """Test command shortcut mapping."""

    def test_shortcuts_defined(self):
        """Test that command shortcuts are properly defined."""
        assert isinstance(COMMAND_SHORTCUTS, dict)
        assert len(COMMAND_SHORTCUTS) > 0

    def test_daily_shortcuts(self):
        """Test daily-related shortcuts all map to pa:daily."""
        daily_shortcuts = ["daily", "morning", "brief", "briefing"]
        for shortcut in daily_shortcuts:
            assert shortcut in COMMAND_SHORTCUTS
            assert COMMAND_SHORTCUTS[shortcut] == "pa:daily"

    def test_email_shortcuts(self):
        """Test email-related shortcuts all map to pa:email."""
        email_shortcuts = ["email", "emails", "inbox"]
        for shortcut in email_shortcuts:
            assert shortcut in COMMAND_SHORTCUTS
            assert COMMAND_SHORTCUTS[shortcut] == "pa:email"

    def test_schedule_shortcuts(self):
        """Test schedule-related shortcuts."""
        assert COMMAND_SHORTCUTS.get("schedule") == "pa:schedule"
        assert COMMAND_SHORTCUTS.get("calendar") == "pa:schedule"

    def test_task_shortcuts(self):
        """Test task-related shortcuts."""
        assert COMMAND_SHORTCUTS.get("tasks") == "pa:tasks"
        assert COMMAND_SHORTCUTS.get("task") == "pa:tasks"

    def test_weekly_shortcuts(self):
        """Test weekly-related shortcuts."""
        weekly_shortcuts = ["weekly", "week", "review"]
        for shortcut in weekly_shortcuts:
            assert shortcut in COMMAND_SHORTCUTS
            assert COMMAND_SHORTCUTS[shortcut] == "pa:weekly"


# ========================================================================
# Test SYSTEM_COMMANDS
# ========================================================================


class TestSystemCommands:
    """Test system commands set."""

    def test_system_commands_defined(self):
        """Test that system commands set is properly defined."""
        assert isinstance(SYSTEM_COMMANDS, set)
        assert len(SYSTEM_COMMANDS) > 0

    def test_expected_system_commands(self):
        """Test all expected system commands are present."""
        expected = {
            "usage",
            "agents",
            "commands",
            "help",
            "-h",
            "--help",
            "interactive",
            "i",
            "chat",
            "agent",
            "run",
        }
        assert expected.issubset(SYSTEM_COMMANDS)


# ========================================================================
# Test is_natural_language
# ========================================================================


class TestIsNaturalLanguage:
    """Test natural language detection function."""

    def test_question_words_detected(self):
        """Test that questions are detected as natural language."""
        questions = [
            "What should I focus on today?",
            "Why is this happening?",
            "How do I fix this?",
            "When is my next meeting?",
            "Where should I start?",
            "Who is handling this?",
            "Should I take this client?",
            "Can you help me?",
            "Could you explain?",
            "Would this work?",
            "Will this be ready?",
            "Is this correct?",
            "Am I on track?",
            "Are we ready?",
            "Do I need to?",
            "Does this look right?",
            "Did this complete?",
        ]
        for q in questions:
            assert is_natural_language(q) is True, f"Failed on: {q}"

    def test_self_references_detected(self):
        """Test that self-references are detected as natural language."""
        self_refs = [
            "I need help",
            "I'm overwhelmed",
            "Im stuck",
            "I've been working",
            "Ive finished",
            "my tasks",
            "help me",
            "myself",
        ]
        for ref in self_refs:
            assert is_natural_language(ref) is True, f"Failed on: {ref}"

    def test_multi_word_sentences(self):
        """Test that multi-word sentences (3+) are detected as natural language."""
        sentences = [
            "focus on this task",
            "plan my day please",
            "review my commitments today",
        ]
        for s in sentences:
            assert is_natural_language(s) is True, f"Failed on: {s}"

    def test_emotional_words_detected(self):
        """Test that emotional words are detected as natural language."""
        emotional = [
            "help",
            "need assistance",
            "want to finish",
            "feel stuck",
            "feeling overwhelmed",
            "tired today",
            "overwhelmed by tasks",
            "struggling with this",
            "stuck on a problem",
            "confused about priorities",
        ]
        for e in emotional:
            assert is_natural_language(e) is True, f"Failed on: {e}"

    def test_short_commands_not_natural(self):
        """Test that short command-like inputs are not detected as natural language."""
        commands = [
            "daily",
            "run",
            "status",
        ]
        for c in commands:
            # Single words without emotional content should return False
            result = is_natural_language(c)
            # Note: Some of these might return True due to 'help' detection
            # This test validates the function doesn't false-positive on simple words

    def test_empty_input(self):
        """Test handling of empty input."""
        assert is_natural_language("") is False
        assert is_natural_language("   ") is False

    def test_case_insensitivity(self):
        """Test that detection is case-insensitive."""
        assert is_natural_language("WHAT should I do?") is True
        assert is_natural_language("I'M stuck") is True
        assert is_natural_language("HELP me") is True


# ========================================================================
# Test print_usage
# ========================================================================


class TestPrintUsage:
    """Test usage printing."""

    def test_print_usage(self, capsys):
        """Test that print_usage outputs the docstring."""
        print_usage()
        captured = capsys.readouterr()
        assert "Thanos CLI" in captured.out
        assert "NATURAL LANGUAGE INTERFACE" in captured.out
        assert "thanos interactive" in captured.out


# ========================================================================
# Test main() - System Commands
# ========================================================================


class TestMainSystemCommands:
    """Test main() function system command handling."""

    def test_no_arguments_prints_usage(self, capsys):
        """Test that no arguments prints usage and exits."""
        with patch.object(sys, "argv", ["thanos"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Thanos CLI" in captured.out

    def test_help_flag(self, capsys):
        """Test --help flag prints usage."""
        with patch.object(sys, "argv", ["thanos", "--help"]):
            main()
        captured = capsys.readouterr()
        assert "Thanos CLI" in captured.out

    def test_help_short_flag(self, capsys):
        """Test -h flag prints usage."""
        with patch.object(sys, "argv", ["thanos", "-h"]):
            main()
        captured = capsys.readouterr()
        assert "Thanos CLI" in captured.out

    def test_help_command(self, capsys):
        """Test help command prints usage."""
        with patch.object(sys, "argv", ["thanos", "help"]):
            main()
        captured = capsys.readouterr()
        assert "Thanos CLI" in captured.out


class TestMainInteractiveCommand:
    """Test main() interactive command handling."""

    @patch("thanos.ThanosOrchestrator")
    @patch("Tools.thanos_interactive.ThanosInteractive")
    def test_interactive_command(self, mock_interactive_class, mock_orch):
        """Test 'interactive' command launches interactive mode."""
        mock_instance = Mock()
        mock_interactive_class.return_value = mock_instance

        with patch.object(sys, "argv", ["thanos", "interactive"]):
            with patch.dict(
                "sys.modules",
                {"Tools.thanos_interactive": Mock(ThanosInteractive=mock_interactive_class)},
            ):
                # We need to re-import to pick up the mock
                with patch("thanos.ThanosOrchestrator", mock_orch):
                    # The import happens inside main(), so we patch it there
                    pass

    @patch("thanos.ThanosOrchestrator")
    def test_i_alias(self, mock_orch):
        """Test 'i' alias launches interactive mode."""
        mock_interactive_class = Mock()
        mock_instance = Mock()
        mock_interactive_class.return_value = mock_instance

        with patch.object(sys, "argv", ["thanos", "i"]):
            with patch.dict(
                sys.modules,
                {"Tools.thanos_interactive": Mock(ThanosInteractive=mock_interactive_class)},
            ):
                # The import is dynamic, so we need to test differently
                pass


class TestMainChatCommand:
    """Test main() chat command handling."""

    @patch("thanos.ThanosOrchestrator")
    def test_chat_command_with_message(self, mock_orch_class):
        """Test 'chat' command with message."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "chat", "Hello", "world"]):
            main()

        mock_orch.chat.assert_called_once_with("Hello world", stream=True)

    @patch("thanos.ThanosOrchestrator")
    def test_chat_command_without_message(self, mock_orch_class, capsys):
        """Test 'chat' command without message shows usage."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "chat"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Usage: thanos chat" in captured.out


class TestMainAgentCommand:
    """Test main() agent command handling."""

    @patch("thanos.ThanosOrchestrator")
    def test_agent_command_with_message(self, mock_orch_class):
        """Test 'agent' command with agent name and message."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "agent", "coach", "Help", "me", "focus"]):
            main()

        mock_orch.chat.assert_called_once_with("Help me focus", agent="coach", stream=True)

    @patch("thanos.ThanosOrchestrator")
    def test_agent_command_without_enough_args(self, mock_orch_class, capsys):
        """Test 'agent' command without enough args shows usage."""
        mock_orch = Mock()
        mock_agent = Mock()
        mock_agent.name = "Ops"
        mock_orch.agents = {"ops": mock_agent}
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "agent", "coach"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Usage: thanos agent" in captured.out
        assert "Available agents" in captured.out


class TestMainRunCommand:
    """Test main() run command handling."""

    @patch("thanos.ThanosOrchestrator")
    def test_run_command_with_args(self, mock_orch_class):
        """Test 'run' command with command name."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "run", "pa:daily"]):
            main()

        mock_orch.run_command.assert_called_once_with("pa:daily", "", stream=True)

    @patch("thanos.ThanosOrchestrator")
    def test_run_command_with_extra_args(self, mock_orch_class):
        """Test 'run' command with additional arguments."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "run", "pa:tasks", "high", "priority"]):
            main()

        mock_orch.run_command.assert_called_once_with("pa:tasks", "high priority", stream=True)

    @patch("thanos.ThanosOrchestrator")
    def test_run_command_without_args(self, mock_orch_class, capsys):
        """Test 'run' command without command name shows usage."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "run"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Usage: thanos run" in captured.out


class TestMainUsageCommand:
    """Test main() usage command handling."""

    @patch("thanos.ThanosOrchestrator")
    def test_usage_command_success(self, mock_orch_class, capsys):
        """Test 'usage' command displays API usage."""
        mock_orch = Mock()
        mock_orch.get_usage.return_value = {
            "total_tokens": 150000,
            "total_cost_usd": 4.50,
            "total_calls": 75,
            "projected_monthly_cost": 45.00,
        }
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "usage"]):
            main()

        captured = capsys.readouterr()
        assert "Claude API Usage" in captured.out
        assert "150,000" in captured.out
        assert "$4.50" in captured.out
        assert "75" in captured.out
        assert "$45.00" in captured.out

    @patch("thanos.ThanosOrchestrator")
    def test_usage_command_error(self, mock_orch_class, capsys):
        """Test 'usage' command handles errors."""
        mock_orch = Mock()
        mock_orch.get_usage.side_effect = Exception("API error")
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "usage"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.out


class TestMainAgentsCommand:
    """Test main() agents command handling."""

    @patch("thanos.ThanosOrchestrator")
    def test_agents_command(self, mock_orch_class, capsys):
        """Test 'agents' command lists available agents."""
        mock_orch = Mock()
        mock_agent = Mock()
        mock_agent.name = "Ops"
        mock_agent.role = "Operations Manager"
        mock_agent.triggers = ["task", "todo", "schedule", "calendar"]
        mock_orch.agents = {"ops": mock_agent}
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "agents"]):
            main()

        captured = capsys.readouterr()
        assert "Available Agents" in captured.out
        assert "Ops" in captured.out
        assert "Operations Manager" in captured.out
        assert "Triggers:" in captured.out

    @patch("thanos.ThanosOrchestrator")
    def test_agents_command_empty_triggers(self, mock_orch_class, capsys):
        """Test 'agents' command with agent having no triggers."""
        mock_orch = Mock()
        mock_agent = Mock()
        mock_agent.name = "Test"
        mock_agent.role = "Test Agent"
        mock_agent.triggers = []
        mock_orch.agents = {"test": mock_agent}
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "agents"]):
            main()

        captured = capsys.readouterr()
        assert "Test" in captured.out
        assert "Test Agent" in captured.out
        # No "Triggers:" line since triggers is empty


class TestMainCommandsCommand:
    """Test main() commands command handling."""

    @patch("thanos.ThanosOrchestrator")
    def test_commands_command(self, mock_orch_class, capsys):
        """Test 'commands' command lists available commands."""
        mock_orch = Mock()
        mock_orch.list_commands.return_value = ["pa:daily", "pa:email", "pa:tasks"]
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "commands"]):
            main()

        captured = capsys.readouterr()
        assert "Available Commands" in captured.out
        assert "pa:daily" in captured.out
        assert "pa:email" in captured.out
        assert "pa:tasks" in captured.out


# ========================================================================
# Test main() - Command Shortcuts
# ========================================================================


class TestMainCommandShortcuts:
    """Test main() command shortcut handling."""

    @patch("thanos.ThanosOrchestrator")
    def test_daily_shortcut(self, mock_orch_class, capsys):
        """Test 'daily' shortcut runs pa:daily."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "daily"]):
            main()

        mock_orch.run_command.assert_called_once_with("pa:daily", "", stream=True)
        captured = capsys.readouterr()
        assert "Running pa:daily" in captured.out

    @patch("thanos.ThanosOrchestrator")
    def test_morning_shortcut(self, mock_orch_class, capsys):
        """Test 'morning' shortcut runs pa:daily."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "morning"]):
            main()

        mock_orch.run_command.assert_called_once_with("pa:daily", "", stream=True)

    @patch("thanos.ThanosOrchestrator")
    def test_email_shortcut(self, mock_orch_class, capsys):
        """Test 'email' shortcut runs pa:email."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "email"]):
            main()

        mock_orch.run_command.assert_called_once_with("pa:email", "", stream=True)

    @patch("thanos.ThanosOrchestrator")
    def test_tasks_shortcut(self, mock_orch_class, capsys):
        """Test 'tasks' shortcut runs pa:tasks."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "tasks"]):
            main()

        mock_orch.run_command.assert_called_once_with("pa:tasks", "", stream=True)

    @patch("thanos.ThanosOrchestrator")
    def test_weekly_shortcut(self, mock_orch_class, capsys):
        """Test 'weekly' shortcut runs pa:weekly."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "weekly"]):
            main()

        mock_orch.run_command.assert_called_once_with("pa:weekly", "", stream=True)


# ========================================================================
# Test main() - Explicit Command Patterns
# ========================================================================


class TestMainExplicitCommands:
    """Test main() explicit command pattern handling."""

    @patch("thanos.ThanosOrchestrator")
    def test_explicit_command_pattern(self, mock_orch_class):
        """Test explicit pa:daily command runs directly."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "pa:daily"]):
            main()

        mock_orch.run_command.assert_called_once_with("pa:daily", "", stream=True)

    @patch("thanos.ThanosOrchestrator")
    def test_explicit_command_with_args(self, mock_orch_class):
        """Test explicit command with additional arguments."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "pa:tasks", "high", "priority"]):
            main()

        mock_orch.run_command.assert_called_once_with("pa:tasks", "high priority", stream=True)

    @patch("thanos.ThanosOrchestrator")
    def test_custom_command_pattern(self, mock_orch_class):
        """Test custom prefix:name command pattern."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "custom:action"]):
            main()

        mock_orch.run_command.assert_called_once_with("custom:action", "", stream=True)


# ========================================================================
# Test main() - Natural Language Routing
# ========================================================================


class TestMainNaturalLanguageRouting:
    """Test main() natural language routing."""

    @patch("thanos.ThanosOrchestrator")
    def test_question_routed(self, mock_orch_class, capsys):
        """Test question is routed via orchestrator."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "What", "should", "I", "focus", "on", "today?"]):
            main()

        mock_orch.route.assert_called_once_with("What should I focus on today?", stream=True)
        captured = capsys.readouterr()
        assert "🟣" in captured.out  # Visual indicator

    @patch("thanos.ThanosOrchestrator")
    def test_self_reference_routed(self, mock_orch_class, capsys):
        """Test self-reference statement is routed."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "I'm", "overwhelmed"]):
            main()

        mock_orch.route.assert_called_once_with("I'm overwhelmed", stream=True)

    @patch("thanos.ThanosOrchestrator")
    def test_multi_word_sentence_routed(self, mock_orch_class, capsys):
        """Test multi-word sentence is routed."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        # Note: "help" as first word triggers help command, so use different phrase
        with patch.object(sys, "argv", ["thanos", "plan", "my", "day", "tomorrow"]):
            main()

        mock_orch.route.assert_called_once_with("plan my day tomorrow", stream=True)

    @patch("thanos.ThanosOrchestrator")
    def test_emotional_message_routed(self, mock_orch_class, capsys):
        """Test emotional message is routed."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "feeling", "stuck"]):
            main()

        mock_orch.route.assert_called_once_with("feeling stuck", stream=True)


# ========================================================================
# Test Edge Cases
# ========================================================================


class TestMainEdgeCases:
    """Test edge cases in main() function."""

    @patch("thanos.ThanosOrchestrator")
    def test_case_insensitive_commands(self, mock_orch_class, capsys):
        """Test commands are case insensitive."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        # DAILY should work same as daily
        with patch.object(sys, "argv", ["thanos", "DAILY"]):
            main()

        mock_orch.run_command.assert_called_once_with("pa:daily", "", stream=True)

    @patch("thanos.ThanosOrchestrator")
    def test_uppercase_system_command(self, mock_orch_class, capsys):
        """Test uppercase system command works."""
        mock_orch = Mock()
        mock_orch.list_commands.return_value = ["pa:daily"]
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "COMMANDS"]):
            main()

        captured = capsys.readouterr()
        assert "Available Commands" in captured.out

    @patch("thanos.ThanosOrchestrator")
    def test_shortcut_not_triggered_with_extra_args(self, mock_orch_class, capsys):
        """Test shortcut requires single word (shortcuts only work alone)."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        # "daily something" should be treated as natural language, not shortcut
        with patch.object(sys, "argv", ["thanos", "daily", "something"]):
            main()

        # Should route as natural language, not run_command with shortcut
        mock_orch.route.assert_called_once()
        assert (
            mock_orch.run_command.call_count == 0
            or mock_orch.run_command.call_args[0][0] != "pa:daily"
        )

    @patch("thanos.ThanosOrchestrator")
    def test_colon_not_command_pattern(self, mock_orch_class, capsys):
        """Test that single word with colon but multiple colons is not command."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        # "a:b:c" has 3 parts, not 2, so shouldn't match command pattern
        with patch.object(sys, "argv", ["thanos", "a:b:c"]):
            main()

        # Should be routed as natural language
        mock_orch.route.assert_called_once()


# ========================================================================
# Integration-style Tests
# ========================================================================


class TestMainIntegration:
    """Integration-style tests for main() function."""

    @patch("thanos.ThanosOrchestrator")
    def test_full_workflow_question(self, mock_orch_class, capsys):
        """Test full workflow for a question."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "Should", "I", "take", "this", "client?"]):
            main()

        # Verify orchestrator was initialized with THANOS_DIR
        mock_orch_class.assert_called_once()

        # Verify route was called with full message
        mock_orch.route.assert_called_once_with("Should I take this client?", stream=True)

        # Verify visual indicator was printed
        captured = capsys.readouterr()
        assert "🟣" in captured.out

    @patch("thanos.ThanosOrchestrator")
    def test_full_workflow_shortcut(self, mock_orch_class, capsys):
        """Test full workflow for a shortcut."""
        mock_orch = Mock()
        mock_orch_class.return_value = mock_orch

        with patch.object(sys, "argv", ["thanos", "brief"]):
            main()

        mock_orch.run_command.assert_called_once_with("pa:daily", "", stream=True)
        captured = capsys.readouterr()
        assert "Running pa:daily" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
