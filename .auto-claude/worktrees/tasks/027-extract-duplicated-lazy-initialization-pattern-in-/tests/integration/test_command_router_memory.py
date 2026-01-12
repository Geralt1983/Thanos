"""
Integration tests for CommandRouter memory commands.

Tests the /memory, /recall, /remember commands with lazy-initialized adapters.
"""

import asyncio
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import pytest
import sys
import os

# Add Tools to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Tools"))

from command_router import CommandRouter, CommandAction


@pytest.fixture
def mock_orchestrator():
    """Mock ThanosOrchestrator."""
    orchestrator = Mock()
    orchestrator.agents = {
        "ops": Mock(triggers=["task", "todo", "work"]),
        "coach": Mock(triggers=["goal", "habit", "progress"]),
        "health": Mock(triggers=["sleep", "exercise", "wellness"]),
    }
    return orchestrator


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager."""
    session = Mock()
    session.session = Mock(id="test-session-123")
    session.create_branch = Mock(return_value="branch-456")
    session.get_branch_info = Mock(
        return_value={
            "name": "main",
            "parent_id": None,
            "branch_point": 0,
        }
    )
    return session


@pytest.fixture
def mock_context_manager():
    """Mock ContextManager."""
    return Mock()


@pytest.fixture
def mock_state_reader():
    """Mock StateReader."""
    return Mock()


@pytest.fixture
def thanos_dir(tmp_path):
    """Create temporary Thanos directory structure."""
    thanos = tmp_path / "thanos"
    thanos.mkdir()

    # Create History/Sessions directory
    sessions_dir = thanos / "History" / "Sessions"
    sessions_dir.mkdir(parents=True)

    # Create .swarm directory
    swarm_dir = thanos / ".swarm"
    swarm_dir.mkdir()

    # Create .hive-mind directory
    hive_dir = thanos / ".hive-mind"
    hive_dir.mkdir()

    return thanos


@pytest.fixture
def command_router(
    mock_orchestrator,
    mock_session_manager,
    mock_context_manager,
    mock_state_reader,
    thanos_dir,
):
    """Create CommandRouter instance with mocked dependencies."""
    router = CommandRouter(
        orchestrator=mock_orchestrator,
        session_manager=mock_session_manager,
        context_manager=mock_context_manager,
        state_reader=mock_state_reader,
        thanos_dir=thanos_dir,
    )
    return router


class TestMemoryCommand:
    """Test /memory command that displays memory system information."""

    def test_memory_command_basic(self, command_router, capsys):
        """Test /memory command displays memory system information."""
        result = command_router.route_command("/memory")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "Memory Systems:" in captured.out
        assert "Session History:" in captured.out

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_memory_command_with_memos_available(
        self, mock_get_memos, command_router, capsys
    ):
        """Test /memory command when MemOS is available."""
        # Mock MemOS instance
        mock_memos = Mock()
        mock_get_memos.return_value = mock_memos

        # Patch environment variables
        with patch.dict(os.environ, {
            "NEO4J_URL": "bolt://localhost:7687",
            "CHROMADB_PATH": "~/.chromadb"
        }):
            result = command_router.route_command("/memory")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "MemOS" in captured.out
        assert "Neo4j" in captured.out
        assert "ChromaDB" in captured.out

    @patch("command_router.MEMOS_AVAILABLE", False)
    def test_memory_command_without_memos(self, command_router, capsys):
        """Test /memory command when MemOS is not available."""
        result = command_router.route_command("/memory")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True

        captured = capsys.readouterr()
        assert "MemOS not available" in captured.out or "Memory Systems:" in captured.out

    def test_memory_command_shows_session_history(self, command_router, thanos_dir, capsys):
        """Test /memory command shows session history count."""
        # Create some session files
        sessions_dir = thanos_dir / "History" / "Sessions"
        (sessions_dir / "session1.json").write_text("{}")
        (sessions_dir / "session2.json").write_text("{}")
        (sessions_dir / "session3.json").write_text("{}")

        result = command_router.route_command("/memory")

        assert result.action == CommandAction.CONTINUE
        captured = capsys.readouterr()
        assert "3 saved sessions" in captured.out

    def test_memory_command_shows_swarm_memory(self, command_router, thanos_dir, capsys):
        """Test /memory command shows swarm memory database."""
        # Create swarm memory database
        swarm_db = thanos_dir / ".swarm" / "memory.db"
        swarm_db.write_text("x" * 1024)  # 1KB file

        result = command_router.route_command("/memory")

        assert result.action == CommandAction.CONTINUE
        captured = capsys.readouterr()
        assert "Swarm Memory:" in captured.out
        assert "KB" in captured.out

    def test_memory_command_shows_hive_memory(self, command_router, thanos_dir, capsys):
        """Test /memory command shows hive-mind memory database."""
        # Create hive-mind memory database
        hive_db = thanos_dir / ".hive-mind" / "memory.db"
        hive_db.write_text("x" * 2048)  # 2KB file

        result = command_router.route_command("/memory")

        assert result.action == CommandAction.CONTINUE
        captured = capsys.readouterr()
        assert "Hive Mind Memory:" in captured.out
        assert "KB" in captured.out


class TestRecallCommand:
    """Test /recall command that searches memories."""

    def test_recall_command_no_args(self, command_router, capsys):
        """Test /recall command without arguments shows usage."""
        result = command_router.route_command("/recall")

        assert result.action == CommandAction.CONTINUE
        captured = capsys.readouterr()
        assert "Usage: /recall" in captured.out

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_recall_command_with_memos(self, mock_get_memos, command_router, capsys):
        """Test /recall command searches MemOS when available."""
        # Mock MemOS instance and recall result
        mock_memos = Mock()
        mock_recall_result = Mock()
        mock_recall_result.success = True
        mock_recall_result.vector_results = [
            {
                "content": "Meeting with client about project deadline",
                "memory_type": "observation",
                "similarity": 0.95,
            },
            {
                "content": "Decision to use TypeScript for frontend",
                "memory_type": "decision",
                "similarity": 0.87,
            },
        ]
        mock_recall_result.graph_results = {
            "nodes": [
                {
                    "id": "node-123",
                    "labels": ["Decision"],
                    "properties": {
                        "content": "Use microservices architecture",
                        "description": "Architectural decision for scalability",
                    },
                }
            ]
        }

        # Setup async mock
        async def mock_recall(query, limit, use_graph, use_vector):
            return mock_recall_result

        mock_memos.recall = mock_recall
        mock_get_memos.return_value = mock_memos

        result = command_router.route_command("/recall client project")

        assert result.action == CommandAction.CONTINUE
        captured = capsys.readouterr()
        assert "MemOS Knowledge Graph" in captured.out
        assert "observation" in captured.out or "decision" in captured.out

    @patch("command_router.MEMOS_AVAILABLE", False)
    def test_recall_command_without_memos(self, command_router, thanos_dir, capsys):
        """Test /recall command falls back to session search when MemOS unavailable."""
        # Create some session files with searchable content
        sessions_dir = thanos_dir / "History" / "Sessions"
        (sessions_dir / "session1.json").write_text('{"messages": []}')

        result = command_router.route_command("/recall test query")

        assert result.action == CommandAction.CONTINUE
        # Should at least complete without crashing

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_recall_command_sessions_only_flag(self, mock_get_memos, command_router, capsys):
        """Test /recall command with --sessions flag skips MemOS."""
        result = command_router.route_command("/recall --sessions test query")

        assert result.action == CommandAction.CONTINUE
        # Should not call get_memos when --sessions flag is present
        mock_get_memos.assert_not_called()

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_recall_command_handles_memos_failure(self, mock_get_memos, command_router, capsys):
        """Test /recall command handles MemOS failure gracefully."""
        # Mock MemOS that returns failed result
        mock_memos = Mock()
        mock_recall_result = Mock()
        mock_recall_result.success = False
        mock_recall_result.error = "Connection timeout"

        async def mock_recall(query, limit, use_graph, use_vector):
            return mock_recall_result

        mock_memos.recall = mock_recall
        mock_get_memos.return_value = mock_memos

        result = command_router.route_command("/recall test query")

        # Should handle failure gracefully and continue
        assert result.action == CommandAction.CONTINUE

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_recall_command_vector_results(self, mock_get_memos, command_router, capsys):
        """Test /recall command displays vector search results."""
        mock_memos = Mock()
        mock_recall_result = Mock()
        mock_recall_result.success = True
        mock_recall_result.vector_results = [
            {
                "content": "Important project deadline approaching next week",
                "memory_type": "observation",
                "similarity": 0.92,
            }
        ]
        mock_recall_result.graph_results = None

        async def mock_recall(query, limit, use_graph, use_vector):
            return mock_recall_result

        mock_memos.recall = mock_recall
        mock_get_memos.return_value = mock_memos

        result = command_router.route_command("/recall deadline")

        assert result.action == CommandAction.CONTINUE
        captured = capsys.readouterr()
        assert "MemOS Knowledge Graph" in captured.out
        assert "observation" in captured.out

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_recall_command_graph_results(self, mock_get_memos, command_router, capsys):
        """Test /recall command displays graph search results."""
        mock_memos = Mock()
        mock_recall_result = Mock()
        mock_recall_result.success = True
        mock_recall_result.vector_results = None
        mock_recall_result.graph_results = {
            "nodes": [
                {
                    "id": "node-456",
                    "labels": ["Pattern"],
                    "properties": {
                        "description": "Daily standup pattern at 9 AM",
                    },
                }
            ]
        }

        async def mock_recall(query, limit, use_graph, use_vector):
            return mock_recall_result

        mock_memos.recall = mock_recall
        mock_get_memos.return_value = mock_memos

        result = command_router.route_command("/recall standup pattern")

        assert result.action == CommandAction.CONTINUE
        captured = capsys.readouterr()
        assert "MemOS Knowledge Graph" in captured.out


class TestRememberCommand:
    """Test /remember command that stores memories."""

    def test_remember_command_no_args(self, command_router, capsys):
        """Test /remember command without arguments shows usage."""
        result = command_router.route_command("/remember")

        assert result.action == CommandAction.CONTINUE
        captured = capsys.readouterr()
        assert "Usage: /remember" in captured.out

    @patch("command_router.MEMOS_AVAILABLE", False)
    def test_remember_command_without_memos(self, command_router, capsys):
        """Test /remember command when MemOS is not available."""
        result = command_router.route_command("/remember test memory")

        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        captured = capsys.readouterr()
        assert "MemOS not available" in captured.out

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_remember_command_stores_observation(self, mock_get_memos, command_router, capsys):
        """Test /remember command stores observation memory."""
        mock_memos = Mock()
        mock_remember_result = Mock()
        mock_remember_result.success = True
        mock_remember_result.graph_results = {"node_id": "node-789"}
        mock_remember_result.vector_results = {"id": "vector-123"}

        async def mock_remember(content, memory_type, domain, entities, metadata):
            return mock_remember_result

        mock_memos.remember = mock_remember
        mock_get_memos.return_value = mock_memos

        result = command_router.route_command("/remember Team meeting went well")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        captured = capsys.readouterr()
        assert "Memory stored:" in captured.out
        assert "observation" in captured.out

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_remember_command_stores_decision(self, mock_get_memos, command_router, capsys):
        """Test /remember command stores decision memory with type prefix."""
        mock_memos = Mock()
        mock_remember_result = Mock()
        mock_remember_result.success = True
        mock_remember_result.graph_results = {"node_id": "decision-456"}
        mock_remember_result.vector_results = {"id": "vector-456"}

        async def mock_remember(content, memory_type, domain, entities, metadata):
            assert memory_type == "decision"
            assert "microservices" in content.lower()
            return mock_remember_result

        mock_memos.remember = mock_remember
        mock_get_memos.return_value = mock_memos

        result = command_router.route_command("/remember decision: Use microservices architecture")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        captured = capsys.readouterr()
        assert "Memory stored:" in captured.out
        assert "decision" in captured.out

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_remember_command_stores_pattern(self, mock_get_memos, command_router, capsys):
        """Test /remember command stores pattern memory with type prefix."""
        mock_memos = Mock()
        mock_remember_result = Mock()
        mock_remember_result.success = True
        mock_remember_result.graph_results = {"node_id": "pattern-123"}
        mock_remember_result.vector_results = None

        async def mock_remember(content, memory_type, domain, entities, metadata):
            assert memory_type == "pattern"
            return mock_remember_result

        mock_memos.remember = mock_remember
        mock_get_memos.return_value = mock_memos

        result = command_router.route_command("/remember pattern: Daily standup at 9 AM")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        captured = capsys.readouterr()
        assert "Memory stored:" in captured.out
        assert "pattern" in captured.out

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_remember_command_extracts_entities(self, mock_get_memos, command_router, capsys):
        """Test /remember command extracts @entity mentions."""
        mock_memos = Mock()
        mock_remember_result = Mock()
        mock_remember_result.success = True
        mock_remember_result.graph_results = {"node_id": "entity-789"}
        mock_remember_result.vector_results = None

        entities_captured = []

        async def mock_remember(content, memory_type, domain, entities, metadata):
            entities_captured.extend(entities or [])
            return mock_remember_result

        mock_memos.remember = mock_remember
        mock_get_memos.return_value = mock_memos

        result = command_router.route_command("/remember Meeting with @John and @Sarah about @ProjectX")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        assert "John" in entities_captured
        assert "Sarah" in entities_captured
        assert "ProjectX" in entities_captured

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_remember_command_uses_agent_domain(self, mock_get_memos, command_router, capsys):
        """Test /remember command uses current agent to determine domain."""
        mock_memos = Mock()
        mock_remember_result = Mock()
        mock_remember_result.success = True
        mock_remember_result.graph_results = {}
        mock_remember_result.vector_results = {}

        domain_captured = None

        async def mock_remember(content, memory_type, domain, entities, metadata):
            nonlocal domain_captured
            domain_captured = domain
            return mock_remember_result

        mock_memos.remember = mock_remember
        mock_get_memos.return_value = mock_memos

        # Test with ops agent (work domain)
        command_router.current_agent = "ops"
        command_router.route_command("/remember Complete project documentation")
        assert domain_captured == "work"

        # Test with health agent (health domain)
        command_router.current_agent = "health"
        command_router.route_command("/remember Morning workout completed")
        assert domain_captured == "health"

        # Test with coach agent (personal domain)
        command_router.current_agent = "coach"
        command_router.route_command("/remember Reached daily goal")
        assert domain_captured == "personal"

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_remember_command_includes_metadata(self, mock_get_memos, command_router, capsys):
        """Test /remember command includes agent and session metadata."""
        mock_memos = Mock()
        mock_remember_result = Mock()
        mock_remember_result.success = True
        mock_remember_result.graph_results = {}
        mock_remember_result.vector_results = {}

        metadata_captured = None

        async def mock_remember(content, memory_type, domain, entities, metadata):
            nonlocal metadata_captured
            metadata_captured = metadata
            return mock_remember_result

        mock_memos.remember = mock_remember
        mock_get_memos.return_value = mock_memos

        result = command_router.route_command("/remember Test memory with metadata")

        assert result.action == CommandAction.CONTINUE
        assert result.success is True
        assert metadata_captured is not None
        assert "agent" in metadata_captured
        assert "session_id" in metadata_captured
        assert metadata_captured["agent"] == "ops"

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_remember_command_handles_failure(self, mock_get_memos, command_router, capsys):
        """Test /remember command handles storage failure gracefully."""
        mock_memos = Mock()
        mock_remember_result = Mock()
        mock_remember_result.success = False
        mock_remember_result.error = "Database connection failed"

        async def mock_remember(content, memory_type, domain, entities, metadata):
            return mock_remember_result

        mock_memos.remember = mock_remember
        mock_get_memos.return_value = mock_memos

        result = command_router.route_command("/remember This should fail")

        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        captured = capsys.readouterr()
        assert "Failed to store memory" in captured.out

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_remember_command_handles_none_result(self, mock_get_memos, command_router, capsys):
        """Test /remember command handles None result gracefully."""
        mock_memos = Mock()

        async def mock_remember(content, memory_type, domain, entities, metadata):
            return None

        mock_memos.remember = mock_remember
        mock_get_memos.return_value = mock_memos

        result = command_router.route_command("/remember Test with None result")

        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        captured = capsys.readouterr()
        assert "Failed to store memory" in captured.out


class TestLazyInitialization:
    """Test lazy initialization of MemOS adapter in commands."""

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_memos_lazy_initialization_on_memory_command(
        self, mock_get_memos, command_router
    ):
        """Test that MemOS is lazily initialized on first /memory command."""
        mock_memos = Mock()
        mock_get_memos.return_value = mock_memos

        # Verify not initialized yet
        assert command_router._memos is None
        assert command_router._memos_initialized is False

        # Execute memory command
        command_router.route_command("/memory")

        # Verify lazy initialization occurred
        mock_get_memos.assert_called_once()

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_memos_initialization_idempotency(self, mock_get_memos, command_router, capsys):
        """Test that MemOS is only initialized once across multiple commands."""
        mock_memos = Mock()
        mock_remember_result = Mock()
        mock_remember_result.success = True
        mock_remember_result.graph_results = {}
        mock_remember_result.vector_results = {}

        async def mock_remember(content, memory_type, domain, entities, metadata):
            return mock_remember_result

        mock_memos.remember = mock_remember
        mock_get_memos.return_value = mock_memos

        # Execute multiple commands that use MemOS
        command_router.route_command("/memory")
        command_router.route_command("/remember Test memory 1")
        command_router.route_command("/remember Test memory 2")
        command_router.route_command("/memory")

        # get_memos should only be called once due to idempotency
        assert mock_get_memos.call_count == 1

    @patch("command_router.MEMOS_AVAILABLE", False)
    def test_commands_work_without_memos_available(self, command_router, capsys):
        """Test that commands work gracefully when MemOS is not available."""
        # All commands should execute without crashing
        result1 = command_router.route_command("/memory")
        assert result1.action == CommandAction.CONTINUE

        result2 = command_router.route_command("/recall test")
        assert result2.action == CommandAction.CONTINUE

        result3 = command_router.route_command("/remember test")
        assert result3.action == CommandAction.CONTINUE
        assert result3.success is False  # Should fail gracefully

    @patch("command_router.MEMOS_AVAILABLE", True)
    @patch("command_router.get_memos")
    def test_memos_initialization_failure_handling(self, mock_get_memos, command_router, capsys):
        """Test graceful handling of MemOS initialization failure."""
        # Mock get_memos to raise exception
        mock_get_memos.side_effect = Exception("Connection failed")

        # Commands should handle initialization failure gracefully
        result1 = command_router.route_command("/memory")
        assert result1.action == CommandAction.CONTINUE

        # Should not crash, even after failed initialization
        result2 = command_router.route_command("/remember Test")
        assert result2.action == CommandAction.CONTINUE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
