#!/usr/bin/env python3
"""
Unit tests for Command Handlers

Tests each handler module in isolation with mocked dependencies.
Verifies command processing, error handling, and output formatting.
"""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

import pytest

from Tools.command_handlers import (
    AgentHandler,
    SessionHandler,
    StateHandler,
    MemoryHandler,
    AnalyticsHandler,
    ModelHandler,
    CoreHandler,
    CommandAction,
    CommandResult,
    Colors,
)


# ========================================================================
# Module-level Fixtures
# ========================================================================


@pytest.fixture
def mock_orchestrator():
    """Create mock orchestrator with agents"""
    orchestrator = Mock()
    orchestrator.agents = {
        "ops": Mock(name="Ops", role="Operations Manager", voice="Professional", triggers=[]),
        "strategy": Mock(name="Strategy", role="Strategic Advisor", voice="Thoughtful", triggers=[]),
        "coach": Mock(name="Coach", role="Accountability Coach", voice="Direct", triggers=[]),
        "health": Mock(name="Health", role="Health Optimizer", voice="Supportive", triggers=[]),
    }
    orchestrator._build_system_prompt = Mock(return_value="Test system prompt")
    orchestrator.run_command = Mock()
    return orchestrator


@pytest.fixture
def mock_session_manager():
    """Create mock session manager"""
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
    session_manager.list_sessions = Mock(return_value=[])
    return session_manager


@pytest.fixture
def mock_context_manager():
    """Create mock context manager"""
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
    return context_manager


@pytest.fixture
def mock_state_reader():
    """Create mock state reader"""
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
    return state_reader


@pytest.fixture
def mock_thanos_dir(tmp_path):
    """Create mock Thanos directory structure"""
    thanos_dir = tmp_path / "thanos"
    thanos_dir.mkdir()

    # Create directory structure
    (thanos_dir / "Knowledge").mkdir()
    (thanos_dir / "History" / "Sessions").mkdir(parents=True)

    return thanos_dir


@pytest.fixture
def handler_dependencies(mock_orchestrator, mock_session_manager, mock_context_manager,
                         mock_state_reader, mock_thanos_dir):
    """Create all handler dependencies"""
    return {
        "orchestrator": mock_orchestrator,
        "session_manager": mock_session_manager,
        "context_manager": mock_context_manager,
        "state_reader": mock_state_reader,
        "thanos_dir": mock_thanos_dir,
    }


# ========================================================================
# Test Classes
# ========================================================================


class TestAgentHandler:
    """Test AgentHandler class"""

    def test_initialization(self, handler_dependencies):
        """Test AgentHandler initializes with correct dependencies"""
        handler = AgentHandler(**handler_dependencies)
        assert handler.orchestrator is not None
        assert handler.session is not None
        assert handler._current_agent == "ops"

    def test_get_current_agent(self, handler_dependencies):
        """Test getting current agent"""
        handler = AgentHandler(**handler_dependencies)
        assert handler.get_current_agent() == "ops"

        handler._current_agent = "strategy"
        assert handler.get_current_agent() == "strategy"

    def test_set_current_agent_valid(self, handler_dependencies):
        """Test setting valid agent"""
        handler = AgentHandler(**handler_dependencies)
        result = handler.set_current_agent("strategy")
        assert result is True
        assert handler._current_agent == "strategy"

    def test_set_current_agent_invalid(self, handler_dependencies):
        """Test setting invalid agent"""
        handler = AgentHandler(**handler_dependencies)
        result = handler.set_current_agent("invalid")
        assert result is False
        assert handler._current_agent == "ops"  # Unchanged

    def test_handle_agent_no_args(self, handler_dependencies, capsys):
        """Test /agent without arguments shows current and available"""
        handler = AgentHandler(**handler_dependencies)
        result = handler.handle_agent("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "Current agent: ops" in captured.out
        assert "Available:" in captured.out

    def test_handle_agent_switch_valid(self, handler_dependencies, capsys):
        """Test switching to valid agent"""
        handler = AgentHandler(**handler_dependencies)
        result = handler.handle_agent("strategy")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        assert handler._current_agent == "strategy"

        captured = capsys.readouterr()
        assert "Switched to" in captured.out
        assert "Strategy" in captured.out

    def test_handle_agent_switch_invalid(self, handler_dependencies, capsys):
        """Test switching to invalid agent"""
        handler = AgentHandler(**handler_dependencies)
        result = handler.handle_agent("invalid")

        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        assert handler._current_agent == "ops"  # Unchanged

        captured = capsys.readouterr()
        assert "Unknown agent" in captured.out

    def test_handle_list_agents(self, handler_dependencies, capsys):
        """Test /agents command lists all agents"""
        handler = AgentHandler(**handler_dependencies)
        result = handler.handle_list_agents("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "Available Agents:" in captured.out
        assert "ops" in captured.out
        assert "strategy" in captured.out
        assert "→" in captured.out  # Current agent marker


class TestSessionHandler:
    """Test SessionHandler class"""

    def test_initialization(self, handler_dependencies):
        """Test SessionHandler initializes correctly"""
        handler = SessionHandler(**handler_dependencies)
        assert handler.session is not None

    def test_handle_clear(self, handler_dependencies, capsys):
        """Test /clear command clears session"""
        handler = SessionHandler(**handler_dependencies)
        result = handler.handle_clear("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        handler_dependencies["session_manager"].clear.assert_called_once()

        captured = capsys.readouterr()
        assert "Conversation cleared" in captured.out

    def test_handle_save(self, handler_dependencies, capsys):
        """Test /save command saves session"""
        handler = SessionHandler(**handler_dependencies)
        result = handler.handle_save("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        handler_dependencies["session_manager"].save.assert_called_once()

        captured = capsys.readouterr()
        assert "Session saved" in captured.out

    def test_handle_sessions_empty(self, handler_dependencies, capsys):
        """Test /sessions with no saved sessions"""
        handler = SessionHandler(**handler_dependencies)
        result = handler.handle_sessions("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "No saved sessions found" in captured.out

    def test_handle_sessions_with_data(self, handler_dependencies, capsys):
        """Test /sessions displays saved sessions"""
        handler_dependencies["session_manager"].list_sessions.return_value = [
            {
                "id": "sess-123",
                "date": "2026-01-11",
                "agent": "ops",
                "messages": 5,
                "tokens": 1000
            }
        ]

        handler = SessionHandler(**handler_dependencies)
        result = handler.handle_sessions("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "Recent Sessions:" in captured.out


class TestStateHandler:
    """Test StateHandler class"""

    def test_initialization(self, handler_dependencies):
        """Test StateHandler initializes correctly"""
        handler = StateHandler(**handler_dependencies)
        assert handler.state_reader is not None

    def test_handle_usage(self, handler_dependencies, capsys):
        """Test /usage displays session statistics"""
        handler = StateHandler(**handler_dependencies)
        result = handler.handle_usage("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "Session Usage:" in captured.out
        assert "10 minutes" in captured.out
        assert "5" in captured.out  # Message count
        assert "1,000" in captured.out  # Input tokens
        assert "2,000" in captured.out  # Output tokens
        assert "$0.0500" in captured.out  # Cost

    def test_handle_context(self, handler_dependencies, capsys):
        """Test /context displays context window usage"""
        handler = StateHandler(**handler_dependencies)
        result = handler.handle_context("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "Context Window:" in captured.out
        assert "500" in captured.out  # System tokens
        assert "1,500" in captured.out  # History tokens
        assert "2,000" in captured.out  # Total used
        assert "200,000" in captured.out  # Available

    def test_handle_state_with_data(self, handler_dependencies, capsys):
        """Test /state displays current state"""
        handler = StateHandler(**handler_dependencies)
        result = handler.handle_state("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "Current Thanos State" in captured.out
        assert "Test focus" in captured.out
        assert "Task 1" in captured.out
        assert "Pending Commitments: 3" in captured.out
        assert "Blocker 1" in captured.out
        assert "High" in captured.out

    def test_handle_state_empty(self, handler_dependencies, capsys):
        """Test /state with no context loaded"""
        handler_dependencies["state_reader"].get_quick_context.return_value = {
            "focus": None,
            "top3": [],
            "pending_commitments": 0,
            "blockers": [],
            "energy": None,
            "week_theme": None,
        }

        handler = StateHandler(**handler_dependencies)
        result = handler.handle_state("")

        assert result.action == CommandAction.CONTINUE

        captured = capsys.readouterr()
        assert "No active state loaded" in captured.out

    def test_handle_commitments_with_file(self, handler_dependencies, capsys):
        """Test /commitments displays active commitments"""
        commitments_content = """## Work Commitments
- [ ] Client deliverable due Friday
- [ ] Review Memphis integration
- [x] Completed task

## Personal Commitments
- [ ] Sullivan doctor appointment
"""

        handler = StateHandler(**handler_dependencies)

        # Create State directory and commitments file
        state_dir = handler_dependencies["thanos_dir"] / "State"
        state_dir.mkdir(exist_ok=True)
        commitments_file = state_dir / "Commitments.md"
        commitments_file.write_text(commitments_content)

        result = handler.handle_commitments("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "Active Commitments" in captured.out
        assert "Client deliverable" in captured.out
        assert "Sullivan doctor" in captured.out
        assert "Completed task" not in captured.out  # Completed items filtered

    def test_handle_commitments_file_missing(self, handler_dependencies, capsys):
        """Test /commitments when file doesn't exist"""
        handler = StateHandler(**handler_dependencies)
        result = handler.handle_commitments("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is False

        captured = capsys.readouterr()
        assert "No commitments file found" in captured.out


class TestMemoryHandler:
    """Test MemoryHandler class"""

    def test_initialization(self, handler_dependencies):
        """Test MemoryHandler initializes correctly"""
        handler = MemoryHandler(**handler_dependencies)
        assert handler.orchestrator is not None

    def test_handle_remember_no_args(self, handler_dependencies, capsys):
        """Test /remember without arguments shows usage"""
        handler = MemoryHandler(**handler_dependencies)
        result = handler.handle_remember("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True  # Shows usage, doesn't fail

        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_handle_recall_no_args(self, handler_dependencies, capsys):
        """Test /recall without arguments shows usage"""
        handler = MemoryHandler(**handler_dependencies)
        result = handler.handle_recall("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "Usage:" in captured.out
        assert "/recall" in captured.out

    @patch('Tools.command_handlers.memory_handler.MEMOS_AVAILABLE', False)
    def test_handle_memory_memos_unavailable(self, handler_dependencies, capsys):
        """Test /memory when MemOS is unavailable shows session info"""
        handler = MemoryHandler(**handler_dependencies)
        result = handler.handle_memory("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "Memory Systems" in captured.out  # Updated to match actual output


class TestAnalyticsHandler:
    """Test AnalyticsHandler class"""

    def test_initialization(self, handler_dependencies):
        """Test AnalyticsHandler initializes correctly"""
        handler = AnalyticsHandler(**handler_dependencies)
        assert handler.thanos_dir is not None

    def test_handle_patterns_no_sessions(self, handler_dependencies, capsys):
        """Test /patterns with no saved sessions"""
        handler = AnalyticsHandler(**handler_dependencies)
        result = handler.handle_patterns("")

        assert result.action == CommandAction.CONTINUE

        captured = capsys.readouterr()
        assert "No saved sessions found" in captured.out  # Updated to match actual output

    def test_handle_patterns_with_sessions(self, handler_dependencies, capsys):
        """Test /patterns analyzes saved sessions"""
        # Create mock session files
        sessions_dir = handler_dependencies["thanos_dir"] / "History" / "Sessions"

        session_data = {
            "id": "sess-123",
            "agent": "ops",
            "created_at": "2026-01-11T10:00:00",
            "messages": [
                {"role": "user", "content": "test"},
                {"role": "assistant", "content": "response"}
            ]
        }

        session_file = sessions_dir / "sess-123.json"
        session_file.write_text(json.dumps(session_data))

        handler = AnalyticsHandler(**handler_dependencies)
        result = handler.handle_patterns("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "Conversation Patterns" in captured.out
        assert "Session Overview" in captured.out


class TestModelHandler:
    """Test ModelHandler class"""

    def test_initialization(self, handler_dependencies):
        """Test ModelHandler initializes correctly"""
        handler = ModelHandler(**handler_dependencies)
        assert handler.current_model is None  # Default is None (uses config default)

    def test_handle_model_no_args(self, handler_dependencies, capsys):
        """Test /model without arguments shows current and available"""
        handler = ModelHandler(**handler_dependencies)
        result = handler.handle_model("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "AI Model:" in captured.out
        assert "Available Models:" in captured.out
        assert "opus" in captured.out
        assert "sonnet" in captured.out
        assert "haiku" in captured.out

    def test_handle_model_switch_valid(self, handler_dependencies, capsys):
        """Test switching to valid model"""
        handler = ModelHandler(**handler_dependencies)
        result = handler.handle_model("sonnet")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        assert handler.current_model == "sonnet"

        captured = capsys.readouterr()
        assert "Model switched:" in captured.out
        assert "sonnet" in captured.out

    def test_handle_model_switch_invalid(self, handler_dependencies, capsys):
        """Test switching to invalid model"""
        handler = ModelHandler(**handler_dependencies)
        result = handler.handle_model("invalid")

        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        assert handler.current_model is None  # Unchanged

        captured = capsys.readouterr()
        assert "Unknown model" in captured.out

    def test_get_current_model_default(self, handler_dependencies):
        """Test get_current_model returns default when none set"""
        handler = ModelHandler(**handler_dependencies)
        model = handler.get_current_model()

        assert model == "claude-opus-4-5-20251101"  # Default opus

    def test_get_current_model_custom(self, handler_dependencies):
        """Test get_current_model returns set model"""
        handler = ModelHandler(**handler_dependencies)
        handler.current_model = "haiku"
        model = handler.get_current_model()

        assert model == "claude-3-5-haiku-20241022"


class TestCoreHandler:
    """Test CoreHandler class"""

    def test_initialization(self, handler_dependencies):
        """Test CoreHandler initializes correctly"""
        handler = CoreHandler(**handler_dependencies)
        assert handler.orchestrator is not None

    def test_handle_help(self, handler_dependencies, capsys):
        """Test /help displays all commands"""
        handler = CoreHandler(**handler_dependencies)
        result = handler.handle_help("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "Commands:" in captured.out
        assert "/agent" in captured.out
        assert "/state" in captured.out
        assert "/help" in captured.out
        assert "/quit" in captured.out
        assert "Shortcuts:" in captured.out

    def test_handle_quit(self, handler_dependencies):
        """Test /quit returns QUIT action"""
        handler = CoreHandler(**handler_dependencies)
        result = handler.handle_quit("")

        assert result.action == CommandAction.QUIT
        assert result.success is True

    def test_handle_run_no_args(self, handler_dependencies, capsys):
        """Test /run without arguments shows usage"""
        handler = CoreHandler(**handler_dependencies)
        result = handler.handle_run("")

        assert result.action == CommandAction.CONTINUE
        assert result.success is False

        captured = capsys.readouterr()
        assert "Usage: /run" in captured.out

    def test_handle_run_with_command(self, handler_dependencies, capsys):
        """Test /run executes Thanos command"""
        handler = CoreHandler(**handler_dependencies)
        result = handler.handle_run("pa:daily")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        handler_dependencies["orchestrator"].run_command.assert_called_once_with(
            "pa:daily", stream=True
        )

        captured = capsys.readouterr()
        assert "Running pa:daily" in captured.out

    def test_handle_run_command_error(self, handler_dependencies, capsys):
        """Test /run handles execution errors"""
        handler_dependencies["orchestrator"].run_command.side_effect = Exception("Command failed")

        handler = CoreHandler(**handler_dependencies)
        result = handler.handle_run("pa:daily")

        assert result.action == CommandAction.CONTINUE
        assert result.success is False

        captured = capsys.readouterr()
        assert "Error running command" in captured.out


class TestBaseHandler:
    """Test BaseHandler shared utilities"""

    def test_colors_defined(self):
        """Test all color codes are defined"""
        assert hasattr(Colors, "PURPLE")
        assert hasattr(Colors, "CYAN")
        assert hasattr(Colors, "DIM")
        assert hasattr(Colors, "RESET")
        assert hasattr(Colors, "BOLD")

        # Verify they are strings
        assert isinstance(Colors.PURPLE, str)
        assert isinstance(Colors.CYAN, str)
        assert isinstance(Colors.DIM, str)
        assert isinstance(Colors.RESET, str)
        assert isinstance(Colors.BOLD, str)

    def test_command_result_defaults(self):
        """Test CommandResult default values"""
        result = CommandResult()
        assert result.action == CommandAction.CONTINUE
        assert result.message is None
        assert result.success is True

    def test_command_result_quit(self):
        """Test CommandResult with QUIT action"""
        result = CommandResult(action=CommandAction.QUIT)
        assert result.action == CommandAction.QUIT
        assert result.success is True

    def test_command_result_error(self):
        """Test CommandResult with error"""
        result = CommandResult(success=False, message="Error occurred")
        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        assert result.message == "Error occurred"

    def test_command_action_enum(self):
        """Test CommandAction enum values"""
        assert hasattr(CommandAction, "CONTINUE")
        assert hasattr(CommandAction, "QUIT")
        assert CommandAction.CONTINUE != CommandAction.QUIT
