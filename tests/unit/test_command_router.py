#!/usr/bin/env python3
"""
Unit tests for CommandRouter

Tests command routing, execution, and all command handlers with mocked dependencies.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from Tools.command_router import Colors, CommandAction, CommandResult, CommandRouter


# ========================================================================
# Module-level Fixtures
# ========================================================================


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for CommandRouter"""
    orchestrator = Mock()
    # Agents need explicit triggers=[] to avoid Mock iteration errors
    orchestrator.agents = {
        "ops": Mock(name="Ops", role="Operations Manager", voice="Professional", triggers=[]),
        "strategy": Mock(
            name="Strategy", role="Strategic Advisor", voice="Thoughtful", triggers=[]
        ),
        "coach": Mock(name="Coach", role="Accountability Coach", voice="Direct", triggers=[]),
        "health": Mock(name="Health", role="Health Optimizer", voice="Supportive", triggers=[]),
    }
    orchestrator._build_system_prompt = Mock(return_value="Test system prompt")
    orchestrator.run_command = Mock()

    session_manager = Mock()
    session_manager.get_stats = Mock(
        return_value={
            "duration_minutes": 10,
            "message_count": 5,
            "total_input_tokens": 1000,
            "total_output_tokens": 2000,
            "total_cost": 0.05,
        }
    )
    session_manager.clear = Mock()
    session_manager.save = Mock(return_value=Path("/fake/session.md"))
    session_manager.get_messages_for_api = Mock(return_value=[])

    context_manager = Mock()
    context_manager.get_usage_report = Mock(
        return_value={
            "system_tokens": 500,
            "history_tokens": 1500,
            "total_used": 2000,
            "available": 200000,
            "usage_percent": 1.0,
            "messages_in_context": 5,
        }
    )

    state_reader = Mock()
    state_reader.get_quick_context = Mock(
        return_value={
            "focus": "Test focus",
            "top3": ["Task 1", "Task 2", "Task 3"],
            "pending_commitments": 3,
            "blockers": ["Blocker 1"],
            "energy": "High",
            "week_theme": "Testing week",
        }
    )

    thanos_dir = Path("/fake/thanos")

    return {
        "orchestrator": orchestrator,
        "session_manager": session_manager,
        "context_manager": context_manager,
        "state_reader": state_reader,
        "thanos_dir": thanos_dir,
    }


@pytest.fixture
def router(mock_dependencies):
    """Create CommandRouter with mocked dependencies"""
    return CommandRouter(
        orchestrator=mock_dependencies["orchestrator"],
        session_manager=mock_dependencies["session_manager"],
        context_manager=mock_dependencies["context_manager"],
        state_reader=mock_dependencies["state_reader"],
        thanos_dir=mock_dependencies["thanos_dir"],
    )


# ========================================================================
# Test Classes
# ========================================================================


class TestCommandRouter:
    """Test CommandRouter initialization and routing"""

    def test_initialization(self, router):
        """Test CommandRouter initializes with correct dependencies"""
        assert router.orchestrator is not None
        assert router.session is not None
        assert router.context_mgr is not None
        assert router.state_reader is not None
        assert router.thanos_dir == Path("/fake/thanos")
        assert router.current_agent == "ops"
        assert len(router._commands) > 0

    def test_command_registration(self, router):
        """Test all expected commands are registered"""
        expected_commands = [
            "agent",
            "a",  # Agent switching
            "clear",  # History management
            "save",  # Session saving
            "usage",  # Usage stats
            "context",  # Context window
            "state",
            "s",  # State display
            "commitments",
            "c",  # Commitments
            "help",
            "h",  # Help
            "quit",
            "q",
            "exit",  # Exit
            "run",  # Command execution
            "agents",  # List agents
            "prompt",
            "p",  # Prompt mode switching
        ]
        for cmd in expected_commands:
            assert cmd in router._commands

    def test_unknown_command(self, router, capsys):
        """Test unknown command handling"""
        result = router.route_command("/unknown")
        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        captured = capsys.readouterr()
        assert "Unknown command" in captured.out

    def test_command_aliases(self, router):
        """Test command aliases route to same handler"""
        # State aliases
        assert router._commands.get("state")[0] == router._commands.get("s")[0]
        # Commitments aliases
        assert router._commands.get("commitments")[0] == router._commands.get("c")[0]
        # Agent aliases
        assert router._commands.get("agent")[0] == router._commands.get("a")[0]
        # Help aliases
        assert router._commands.get("help")[0] == router._commands.get("h")[0]
        # Quit aliases
        assert router._commands.get("quit")[0] == router._commands.get("q")[0]
        assert router._commands.get("quit")[0] == router._commands.get("exit")[0]
        # Prompt aliases
        assert router._commands.get("prompt")[0] == router._commands.get("p")[0]


class TestAgentCommand:
    """Test /agent command"""

    def test_agent_switch_valid(self, router, capsys):
        """Test switching to valid agent"""
        result = router.route_command("/agent strategy")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        assert router.current_agent == "strategy"
        captured = capsys.readouterr()
        assert "Switched to" in captured.out

    def test_agent_switch_invalid(self, router, capsys):
        """Test switching to invalid agent"""
        result = router.route_command("/agent invalid")
        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        assert router.current_agent == "ops"  # Unchanged
        captured = capsys.readouterr()
        assert "Unknown agent" in captured.out

    def test_agent_no_args(self, router, capsys):
        """Test /agent without arguments shows current and available"""
        result = router.route_command("/agent")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        captured = capsys.readouterr()
        assert "Current agent" in captured.out
        assert "Available" in captured.out


class TestStateCommand:
    """Test /state command"""

    def test_state_display(self, router, capsys):
        """Test state command displays all context"""
        result = router.route_command("/state")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        captured = capsys.readouterr()
        assert "Test focus" in captured.out
        assert "Task 1" in captured.out
        assert "Pending Commitments: 3" in captured.out
        assert "Blocker 1" in captured.out
        assert "High" in captured.out

    def test_state_empty(self, mock_dependencies, capsys):
        """Test state with no context loaded"""
        mock_dependencies["state_reader"].get_quick_context.return_value = {
            "focus": None,
            "top3": [],
            "pending_commitments": 0,
            "blockers": [],
            "energy": None,
            "week_theme": None,
        }
        router = CommandRouter(**mock_dependencies)
        result = router.route_command("/state")
        assert result.action == CommandAction.CONTINUE
        captured = capsys.readouterr()
        assert "No active state loaded" in captured.out

    def test_state_alias(self, router, capsys):
        """Test /s alias works"""
        result = router.route_command("/s")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        captured = capsys.readouterr()
        assert "Current Thanos State" in captured.out


class TestCommitmentsCommand:
    """Test /commitments command"""

    def test_commitments_display(self, router, capsys):
        """Test commitments command displays active items"""
        commitments_content = """## Work Commitments
- [ ] Client deliverable due Friday
- [ ] Review Memphis integration
- [x] Completed task

## Personal Commitments
- [ ] Sullivan doctor appointment
- [ ] Home office conversion planning
"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=commitments_content):
                result = router.route_command("/commitments")
                assert result.action == CommandAction.CONTINUE
                assert result.success is True
                captured = capsys.readouterr()
                assert "Active Commitments" in captured.out
                assert "Client deliverable" in captured.out
                assert "Sullivan doctor" in captured.out
                assert "Completed task" not in captured.out  # Completed items filtered

    def test_commitments_file_missing(self, router, capsys):
        """Test commitments when file doesn't exist"""
        with patch("pathlib.Path.exists", return_value=False):
            result = router.route_command("/commitments")
            assert result.action == CommandAction.CONTINUE
            assert result.success is False
            captured = capsys.readouterr()
            assert "No commitments file found" in captured.out

    def test_commitments_read_error(self, router, capsys):
        """Test commitments command handles read errors"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", side_effect=OSError("Read error")):
                result = router.route_command("/commitments")
                assert result.action == CommandAction.CONTINUE
                assert result.success is False
                captured = capsys.readouterr()
                assert "Error reading commitments" in captured.out

    def test_commitments_alias(self, router, capsys):
        """Test /c alias works"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value="## Work Commitments\n- [ ] Test"):
                result = router.route_command("/c")
                assert result.action == CommandAction.CONTINUE
                captured = capsys.readouterr()
                assert "Active Commitments" in captured.out


class TestUsageCommand:
    """Test /usage command"""

    def test_usage_display(self, router, capsys):
        """Test usage command displays session stats"""
        result = router.route_command("/usage")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        captured = capsys.readouterr()
        assert "Session Usage" in captured.out
        assert "10 minutes" in captured.out
        assert "5" in captured.out  # Message count
        assert "1,000" in captured.out  # Input tokens
        assert "2,000" in captured.out  # Output tokens
        assert "$0.0500" in captured.out  # Cost


class TestContextCommand:
    """Test /context command"""

    def test_context_display(self, router, capsys):
        """Test context command displays usage report"""
        result = router.route_command("/context")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        captured = capsys.readouterr()
        assert "Context Window" in captured.out
        assert "500" in captured.out  # System tokens
        assert "1,500" in captured.out  # History tokens
        assert "2,000" in captured.out  # Total used
        assert "200,000" in captured.out  # Available
        assert "1.0%" in captured.out  # Usage percent


class TestClearCommand:
    """Test /clear command"""

    def test_clear_history(self, router, mock_dependencies, capsys):
        """Test clear command clears session history"""
        result = router.route_command("/clear")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        mock_dependencies["session_manager"].clear.assert_called_once()
        captured = capsys.readouterr()
        assert "Conversation cleared" in captured.out


class TestSaveCommand:
    """Test /save command"""

    def test_save_session(self, router, mock_dependencies, capsys):
        """Test save command saves session"""
        result = router.route_command("/save")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        mock_dependencies["session_manager"].save.assert_called_once()
        captured = capsys.readouterr()
        assert "Session saved" in captured.out


class TestRunCommand:
    """Test /run command"""

    def test_run_with_args(self, router, mock_dependencies, capsys):
        """Test run command with valid arguments"""
        result = router.route_command("/run pa:daily")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        mock_dependencies["orchestrator"].run_command.assert_called_once_with(
            "pa:daily", stream=True
        )
        captured = capsys.readouterr()
        assert "Running pa:daily" in captured.out

    def test_run_without_args(self, router, capsys):
        """Test run command without arguments"""
        result = router.route_command("/run")
        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        captured = capsys.readouterr()
        assert "Usage: /run <command>" in captured.out

    def test_run_command_error(self, router, mock_dependencies, capsys):
        """Test run command handles execution errors"""
        mock_dependencies["orchestrator"].run_command.side_effect = Exception("Command failed")
        result = router.route_command("/run pa:daily")
        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        captured = capsys.readouterr()
        assert "Error running command" in captured.out


class TestListAgentsCommand:
    """Test /agents command"""

    def test_list_agents(self, router, capsys):
        """Test agents command lists all available agents"""
        result = router.route_command("/agents")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        captured = capsys.readouterr()
        assert "Available Agents" in captured.out
        assert "ops" in captured.out
        assert "strategy" in captured.out
        assert "coach" in captured.out
        assert "health" in captured.out
        assert "→" in captured.out  # Current agent marker


class TestHelpCommand:
    """Test /help command"""

    def test_help_display(self, router, capsys):
        """Test help command displays all commands"""
        result = router.route_command("/help")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        captured = capsys.readouterr()
        assert "Commands:" in captured.out
        assert "/agent" in captured.out
        assert "/state" in captured.out
        assert "/commitments" in captured.out
        assert "/usage" in captured.out
        assert "/help" in captured.out
        assert "/quit" in captured.out
        assert "Shortcuts:" in captured.out

    def test_help_alias(self, router, capsys):
        """Test /h alias works"""
        result = router.route_command("/h")
        assert result.action == CommandAction.CONTINUE
        captured = capsys.readouterr()
        assert "Commands:" in captured.out


class TestQuitCommand:
    """Test /quit command"""

    def test_quit_action(self, router):
        """Test quit command returns QUIT action"""
        result = router.route_command("/quit")
        assert result.action == CommandAction.QUIT
        assert result.success is True

    def test_quit_aliases(self, router):
        """Test quit aliases return QUIT action"""
        result = router.route_command("/q")
        assert result.action == CommandAction.QUIT

        result = router.route_command("/exit")
        assert result.action == CommandAction.QUIT


class TestGetAvailableCommands:
    """Test get_available_commands helper"""

    def test_get_available_commands(self, router):
        """Test get_available_commands returns unique commands"""
        commands = router.get_available_commands()
        assert len(commands) > 0

        # Should be sorted
        assert commands == sorted(commands)

        # Check structure: (name, description, args)
        for cmd, desc, args in commands:
            assert isinstance(cmd, str)
            assert isinstance(desc, str)
            assert isinstance(args, list)


class TestPromptCommand:
    """Test /prompt command"""

    def test_prompt_switch_compact(self, router, capsys):
        """Test switching to compact mode"""
        result = router.route_command("/prompt compact")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        assert router.current_prompt_mode == "compact"
        captured = capsys.readouterr()
        assert "Prompt mode switched" in captured.out

    def test_prompt_switch_standard(self, router, capsys):
        """Test switching to standard mode"""
        result = router.route_command("/prompt standard")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        assert router.current_prompt_mode == "standard"
        captured = capsys.readouterr()
        assert "Prompt mode switched" in captured.out

    def test_prompt_switch_verbose(self, router, capsys):
        """Test switching to verbose mode"""
        result = router.route_command("/prompt verbose")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        assert router.current_prompt_mode == "verbose"
        captured = capsys.readouterr()
        assert "Prompt mode switched" in captured.out

    def test_prompt_switch_invalid(self, router, capsys):
        """Test switching to invalid mode"""
        result = router.route_command("/prompt invalid")
        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        assert router.current_prompt_mode is None  # Unchanged
        captured = capsys.readouterr()
        assert "Unknown mode" in captured.out

    def test_prompt_no_args(self, router, capsys):
        """Test /prompt without arguments shows current and available"""
        result = router.route_command("/prompt")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        captured = capsys.readouterr()
        assert "Prompt Display Mode" in captured.out
        assert "Current:" in captured.out
        assert "Available Modes:" in captured.out
        assert "compact" in captured.out
        assert "standard" in captured.out
        assert "verbose" in captured.out

    def test_prompt_alias(self, router, capsys):
        """Test /p alias works"""
        result = router.route_command("/p verbose")
        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        assert router.current_prompt_mode == "verbose"


class TestCommandResult:
    """Test CommandResult dataclass"""

    def test_default_values(self):
        """Test CommandResult default values"""
        result = CommandResult()
        assert result.action == CommandAction.CONTINUE
        assert result.message is None
        assert result.success is True

    def test_quit_result(self):
        """Test CommandResult with QUIT action"""
        result = CommandResult(action=CommandAction.QUIT)
        assert result.action == CommandAction.QUIT
        assert result.success is True

    def test_error_result(self):
        """Test CommandResult with error"""
        result = CommandResult(success=False, message="Error occurred")
        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        assert result.message == "Error occurred"


class TestColors:
    """Test Colors class constants"""

    def test_color_codes_defined(self):
        """Test all color codes are defined"""
        assert hasattr(Colors, "PURPLE")
        assert hasattr(Colors, "CYAN")
        assert hasattr(Colors, "DIM")
        assert hasattr(Colors, "RESET")
        assert hasattr(Colors, "BOLD")

        # Check they are strings
        assert isinstance(Colors.PURPLE, str)
        assert isinstance(Colors.CYAN, str)
        assert isinstance(Colors.DIM, str)
        assert isinstance(Colors.RESET, str)
        assert isinstance(Colors.BOLD, str)
