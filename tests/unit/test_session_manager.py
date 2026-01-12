"""
Unit tests for SessionManager.

Tests cover:
- Message addition and token tracking
- Sliding window history management (MAX_HISTORY)
- History trimming logic
- Session statistics
- Agent switching
- History clearing
- Session persistence (JSON and Markdown formats)
- ChromaAdapter integration for semantic search indexing
- Auto-indexing on message addition
- Batch indexing with index_session()
- Session loading and listing functionality
- Graceful error handling when ChromaAdapter not configured
"""

from datetime import datetime
from pathlib import Path

import pytest

from Tools.session_manager import MAX_HISTORY, Message, Session, SessionManager


@pytest.mark.unit
class TestMessage:
    """Test Message dataclass."""

    def test_message_creation_with_defaults(self):
        """Test message creation with default values."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)
        assert msg.tokens == 0

    def test_message_creation_with_tokens(self):
        """Test message creation with explicit token count."""
        msg = Message(role="assistant", content="Response", tokens=50)
        assert msg.tokens == 50


@pytest.mark.unit
class TestSession:
    """Test Session dataclass."""

    def test_session_creation_with_defaults(self):
        """Test session creation with default values."""
        session = Session()
        assert len(session.id) == 8  # UUID first 8 chars
        assert isinstance(session.started_at, datetime)
        assert session.agent == "ops"
        assert session.history == []
        assert session.total_input_tokens == 0
        assert session.total_output_tokens == 0
        assert session.total_cost == 0.0

    def test_session_creation_with_custom_agent(self):
        """Test session creation with custom agent."""
        session = Session(agent="coach")
        assert session.agent == "coach"


@pytest.mark.unit
class TestSessionManager:
    """Test SessionManager class."""

    @pytest.fixture
    def session_manager(self, tmp_path):
        """Create a session manager with temporary history directory."""
        history_dir = tmp_path / "history"
        return SessionManager(history_dir=history_dir)

    def test_initialization(self, session_manager):
        """Test session manager initialization."""
        assert isinstance(session_manager.session, Session)
        assert isinstance(session_manager.history_dir, Path)

    def test_add_user_message(self, session_manager):
        """Test adding a user message."""
        session_manager.add_user_message("Hello", tokens=10)

        assert len(session_manager.session.history) == 1
        assert session_manager.session.history[0].role == "user"
        assert session_manager.session.history[0].content == "Hello"
        assert session_manager.session.history[0].tokens == 10
        assert session_manager.session.total_input_tokens == 10

    def test_add_assistant_message(self, session_manager):
        """Test adding an assistant message."""
        session_manager.add_assistant_message("Response", tokens=20)

        assert len(session_manager.session.history) == 1
        assert session_manager.session.history[0].role == "assistant"
        assert session_manager.session.history[0].content == "Response"
        assert session_manager.session.history[0].tokens == 20
        assert session_manager.session.total_output_tokens == 20

    def test_message_sequence_tracking(self, session_manager):
        """Test tracking sequence of messages with token accumulation."""
        session_manager.add_user_message("Q1", tokens=5)
        session_manager.add_assistant_message("A1", tokens=10)
        session_manager.add_user_message("Q2", tokens=7)
        session_manager.add_assistant_message("A2", tokens=15)

        assert len(session_manager.session.history) == 4
        assert session_manager.session.total_input_tokens == 12  # 5 + 7
        assert session_manager.session.total_output_tokens == 25  # 10 + 15

    def test_sliding_window_user_message(self, session_manager):
        """Test sliding window removes oldest messages when MAX_HISTORY exceeded (user)."""
        # Add MAX_HISTORY + 1 messages (alternating user/assistant)
        for i in range(MAX_HISTORY // 2 + 1):
            session_manager.add_user_message(f"User {i}", tokens=5)
            session_manager.add_assistant_message(f"Assistant {i}", tokens=10)

        # History should be trimmed to MAX_HISTORY
        assert len(session_manager.session.history) == MAX_HISTORY

        # First message should be removed
        assert "User 0" not in [m.content for m in session_manager.session.history]
        assert "Assistant 0" not in [m.content for m in session_manager.session.history]

        # Most recent message should remain
        assert session_manager.session.history[-1].content == f"Assistant {MAX_HISTORY // 2}"

    def test_sliding_window_assistant_message(self, session_manager):
        """Test sliding window removes oldest messages when MAX_HISTORY exceeded (assistant)."""
        # Add messages up to MAX_HISTORY
        for i in range(MAX_HISTORY // 2):
            session_manager.add_user_message(f"User {i}", tokens=5)
            session_manager.add_assistant_message(f"Assistant {i}", tokens=10)

        # Add one more pair to trigger trimming
        session_manager.add_user_message(f"User {MAX_HISTORY // 2}", tokens=5)
        session_manager.add_assistant_message(f"Assistant {MAX_HISTORY // 2}", tokens=10)

        # Should maintain MAX_HISTORY messages
        assert len(session_manager.session.history) == MAX_HISTORY

        # Oldest pair should be removed
        assert "User 0" not in [m.content for m in session_manager.session.history]
        assert "Assistant 0" not in [m.content for m in session_manager.session.history]

    def test_token_counts_persist_after_trimming(self, session_manager):
        """Test that cumulative token counts persist after history trimming."""
        # Track expected totals
        expected_input = 0
        expected_output = 0

        # Add enough messages to trigger multiple trims
        for i in range(MAX_HISTORY + 10):
            session_manager.add_user_message(f"User {i}", tokens=5)
            expected_input += 5
            session_manager.add_assistant_message(f"Assistant {i}", tokens=10)
            expected_output += 10

        # Token counts should include all messages, even trimmed ones
        assert session_manager.session.total_input_tokens == expected_input
        assert session_manager.session.total_output_tokens == expected_output

        # But history should be limited
        assert len(session_manager.session.history) == MAX_HISTORY

    def test_get_messages_for_api(self, session_manager):
        """Test converting history to API format."""
        session_manager.add_user_message("Hello", tokens=5)
        session_manager.add_assistant_message("Hi there", tokens=10)

        api_messages = session_manager.get_messages_for_api()

        assert len(api_messages) == 2
        assert api_messages[0] == {"role": "user", "content": "Hello"}
        assert api_messages[1] == {"role": "assistant", "content": "Hi there"}

    def test_is_history_trimmed_false(self, session_manager):
        """Test is_history_trimmed returns False when below limit."""
        for i in range(10):
            session_manager.add_user_message(f"Message {i}")

        assert not session_manager.is_history_trimmed()

    def test_is_history_trimmed_true(self, session_manager):
        """Test is_history_trimmed returns True when at or above limit."""
        # Add exactly MAX_HISTORY messages
        for i in range(MAX_HISTORY // 2):
            session_manager.add_user_message(f"User {i}")
            session_manager.add_assistant_message(f"Assistant {i}")

        assert session_manager.is_history_trimmed()

    def test_switch_agent(self, session_manager):
        """Test switching to a different agent."""
        assert session_manager.session.agent == "ops"

        session_manager.switch_agent("coach")
        assert session_manager.session.agent == "coach"

        session_manager.switch_agent("health")
        assert session_manager.session.agent == "health"

    def test_clear_history(self, session_manager):
        """Test clearing conversation history."""
        # Add some messages
        session_manager.add_user_message("Hello", tokens=5)
        session_manager.add_assistant_message("Response", tokens=10)

        # Store token counts before clearing
        input_tokens = session_manager.session.total_input_tokens
        output_tokens = session_manager.session.total_output_tokens

        # Clear history
        session_manager.clear()

        # History should be empty
        assert len(session_manager.session.history) == 0

        # But session data should persist
        assert session_manager.session.total_input_tokens == input_tokens
        assert session_manager.session.total_output_tokens == output_tokens
        assert session_manager.session.id is not None

    def test_get_stats(self, session_manager):
        """Test getting session statistics."""
        session_manager.add_user_message("Hello", tokens=100)
        session_manager.add_assistant_message("Response", tokens=200)
        session_manager.session.total_cost = 0.05

        stats = session_manager.get_stats()

        assert stats["session_id"] == session_manager.session.id
        assert stats["message_count"] == 2
        assert stats["total_input_tokens"] == 100
        assert stats["total_output_tokens"] == 200
        assert stats["total_cost"] == 0.05
        assert stats["current_agent"] == "ops"
        assert "duration_minutes" in stats

    def test_save_session(self, session_manager):
        """Test saving session to markdown file."""
        session_manager.add_user_message("Hello")
        session_manager.add_assistant_message("Response")
        session_manager.session.total_cost = 0.01

        filepath = session_manager.save()

        # Check file was created
        assert filepath.exists()
        assert filepath.suffix == ".md"

        # Check file content
        content = filepath.read_text()
        assert "Interactive Session" in content
        assert session_manager.session.id in content
        assert "**You:** Hello" in content
        assert "**Ops:** Response" in content
        assert "Saved by Thanos Interactive Mode" in content

    def test_save_session_creates_directory(self, tmp_path):
        """Test that save creates history directory if it doesn't exist."""
        history_dir = tmp_path / "nonexistent" / "history"
        session_manager = SessionManager(history_dir=history_dir)

        session_manager.add_user_message("Test")
        filepath = session_manager.save()

        assert history_dir.exists()
        assert filepath.exists()

    def test_save_session_filename_format(self, session_manager):
        """Test session filename format includes timestamp and session ID."""
        filepath = session_manager.save()

        # Filename should be: YYYY-MM-DD-HHMM-sessionid.md
        assert filepath.stem.count("-") == 4
        assert session_manager.session.id in filepath.stem

    def test_empty_session_stats(self, session_manager):
        """Test statistics for empty session."""
        stats = session_manager.get_stats()

        assert stats["message_count"] == 0
        assert stats["total_input_tokens"] == 0
        assert stats["total_output_tokens"] == 0
        assert stats["total_cost"] == 0.0

    def test_session_duration_tracking(self, session_manager):
        """Test that session duration is tracked correctly."""
        # Get initial stats
        stats1 = session_manager.get_stats()
        assert stats1["duration_minutes"] >= 0

        # Simulate time passing (in real implementation, would use time.sleep or mock)
        # For testing, we verify the calculation logic
        duration = datetime.now() - session_manager.session.started_at
        expected_minutes = int(duration.total_seconds() / 60)

        stats2 = session_manager.get_stats()
        assert stats2["duration_minutes"] == expected_minutes

    def test_multiple_trims_preserve_conversation_pairs(self, session_manager):
        """Test that multiple trims maintain conversation coherence by removing pairs."""
        # Add many messages to trigger multiple trims
        for i in range(MAX_HISTORY + 20):
            session_manager.add_user_message(f"User {i}", tokens=5)
            session_manager.add_assistant_message(f"Assistant {i}", tokens=10)

        # History should be at MAX_HISTORY
        assert len(session_manager.session.history) == MAX_HISTORY

        # Verify conversation pairs are maintained
        # (user messages should still be followed by assistant messages)
        for i in range(0, len(session_manager.session.history) - 1, 2):
            assert session_manager.session.history[i].role == "user"
            if i + 1 < len(session_manager.session.history):
                assert session_manager.session.history[i + 1].role == "assistant"


@pytest.mark.unit
class TestSessionManagerJsonPersistence:
    """Test SessionManager JSON persistence features."""

    @pytest.fixture
    def session_manager(self, tmp_path):
        """Create a session manager with temporary history directory."""
        history_dir = tmp_path / "history"
        return SessionManager(history_dir=history_dir)

    def test_save_creates_json_file(self, session_manager):
        """Test that save() creates a JSON file in addition to markdown."""
        session_manager.add_user_message("Hello", tokens=10)
        session_manager.add_assistant_message("Hi there", tokens=20)
        session_manager.session.total_cost = 0.05

        md_filepath = session_manager.save()

        # Check JSON file was created
        json_filepath = md_filepath.with_suffix(".json")
        assert json_filepath.exists()
        assert json_filepath.suffix == ".json"

    def test_json_contains_full_session_data(self, session_manager):
        """Test that JSON file contains complete session metadata and messages."""
        session_manager.add_user_message("Question", tokens=15)
        session_manager.add_assistant_message("Answer", tokens=25)
        session_manager.session.total_cost = 0.03

        md_filepath = session_manager.save()
        json_filepath = md_filepath.with_suffix(".json")

        # Read and verify JSON content
        import json

        with open(json_filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["id"] == session_manager.session.id
        assert data["agent"] == "ops"
        assert data["total_input_tokens"] == 15
        assert data["total_output_tokens"] == 25
        assert data["total_cost"] == 0.03
        assert len(data["history"]) == 2
        assert data["history"][0]["role"] == "user"
        assert data["history"][0]["content"] == "Question"
        assert data["history"][1]["role"] == "assistant"
        assert data["history"][1]["content"] == "Answer"

    def test_json_messages_include_timestamps_and_tokens(self, session_manager):
        """Test that JSON messages include timestamp and token information."""
        session_manager.add_user_message("Test message", tokens=50)

        md_filepath = session_manager.save()
        json_filepath = md_filepath.with_suffix(".json")

        import json

        with open(json_filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        message = data["history"][0]
        assert "timestamp" in message
        assert "tokens" in message
        assert message["tokens"] == 50

    def test_json_and_markdown_have_same_basename(self, session_manager):
        """Test that JSON and markdown files share the same base filename."""
        session_manager.add_user_message("Test")

        md_filepath = session_manager.save()
        json_filepath = md_filepath.with_suffix(".json")

        assert md_filepath.stem == json_filepath.stem
        assert md_filepath.parent == json_filepath.parent


@pytest.mark.unit
class TestSessionManagerChromaIntegration:
    """Test SessionManager ChromaAdapter integration features."""

    @pytest.fixture
    def mock_chroma_adapter(self):
        """Create a mock ChromaAdapter for testing."""
        from unittest.mock import AsyncMock, MagicMock

        mock = MagicMock()
        # Mock the _store_memory method to return success
        result = MagicMock()
        result.success = True
        mock._store_memory = AsyncMock(return_value=result)
        # Mock the _store_batch method to return success
        mock._store_batch = AsyncMock(return_value=result)
        return mock

    @pytest.fixture
    def session_manager_with_chroma(self, tmp_path, mock_chroma_adapter):
        """Create a session manager with ChromaAdapter configured."""
        history_dir = tmp_path / "history"
        return SessionManager(history_dir=history_dir, chroma_adapter=mock_chroma_adapter)

    @pytest.fixture
    def session_manager_without_chroma(self, tmp_path):
        """Create a session manager without ChromaAdapter."""
        history_dir = tmp_path / "history"
        return SessionManager(history_dir=history_dir, chroma_adapter=None)

    def test_initialization_with_chroma_adapter(self, session_manager_with_chroma):
        """Test session manager initializes correctly with ChromaAdapter."""
        assert session_manager_with_chroma._chroma is not None
        assert session_manager_with_chroma._indexing_enabled is True

    def test_initialization_without_chroma_adapter(self, session_manager_without_chroma):
        """Test session manager initializes correctly without ChromaAdapter."""
        assert session_manager_without_chroma._chroma is None
        assert session_manager_without_chroma._indexing_enabled is False

    def test_set_chroma_adapter(self, session_manager_without_chroma, mock_chroma_adapter):
        """Test setting ChromaAdapter after initialization."""
        assert session_manager_without_chroma._indexing_enabled is False

        session_manager_without_chroma.set_chroma_adapter(mock_chroma_adapter)

        assert session_manager_without_chroma._chroma is not None
        assert session_manager_without_chroma._indexing_enabled is True

    def test_index_message_with_chroma_enabled(self, session_manager_with_chroma):
        """Test index_message succeeds when ChromaAdapter is configured."""
        message = Message(role="user", content="Test message", tokens=10)

        result = session_manager_with_chroma.index_message(message)

        assert result is True
        # Verify _store_memory was called
        assert session_manager_with_chroma._chroma._store_memory.called

    def test_index_message_without_chroma(self, session_manager_without_chroma):
        """Test index_message returns False when ChromaAdapter not configured."""
        message = Message(role="user", content="Test message", tokens=10)

        result = session_manager_without_chroma.index_message(message)

        assert result is False

    def test_index_message_metadata_structure(self, session_manager_with_chroma):
        """Test that index_message passes correct metadata to ChromaAdapter."""
        message = Message(role="user", content="Test message", tokens=10)

        session_manager_with_chroma.index_message(message)

        # Get the call arguments
        call_args = session_manager_with_chroma._chroma._store_memory.call_args[0][0]

        assert call_args["content"] == "Test message"
        assert call_args["collection"] == "conversations"
        assert "metadata" in call_args

        metadata = call_args["metadata"]
        assert metadata["session_id"] == session_manager_with_chroma.session.id
        assert metadata["role"] == "user"
        assert metadata["agent"] == "ops"
        assert "timestamp" in metadata
        assert "date" in metadata

    def test_index_session_batch_indexing(self, session_manager_with_chroma):
        """Test index_session performs batch indexing of all messages."""
        # Add multiple messages
        session_manager_with_chroma.session.history.clear()  # Clear auto-indexed messages
        session_manager_with_chroma._chroma._store_memory.reset_mock()

        # Manually add messages to history without triggering auto-indexing
        for i in range(5):
            msg = Message(role="user", content=f"Message {i}", tokens=10)
            session_manager_with_chroma.session.history.append(msg)

        result = session_manager_with_chroma.index_session()

        assert result["success"] is True
        assert result["indexed"] == 5
        assert result["error"] is None
        # Verify _store_batch was called
        assert session_manager_with_chroma._chroma._store_batch.called

    def test_index_session_without_chroma(self, session_manager_without_chroma):
        """Test index_session returns error when ChromaAdapter not configured."""
        session_manager_without_chroma.add_user_message("Test", tokens=5)

        result = session_manager_without_chroma.index_session()

        assert result["success"] is False
        assert result["indexed"] == 0
        assert "not configured" in result["error"]

    def test_index_session_empty_history(self, session_manager_with_chroma):
        """Test index_session handles empty history gracefully."""
        result = session_manager_with_chroma.index_session()

        assert result["success"] is True
        assert result["indexed"] == 0
        assert result["error"] is None

    def test_auto_indexing_on_add_user_message(self, session_manager_with_chroma):
        """Test that add_user_message automatically indexes to ChromaAdapter."""
        session_manager_with_chroma._chroma._store_memory.reset_mock()

        session_manager_with_chroma.add_user_message("User message", tokens=10)

        # Verify index_message was called via _store_memory
        assert session_manager_with_chroma._chroma._store_memory.called

    def test_auto_indexing_on_add_assistant_message(self, session_manager_with_chroma):
        """Test that add_assistant_message automatically indexes to ChromaAdapter."""
        session_manager_with_chroma._chroma._store_memory.reset_mock()

        session_manager_with_chroma.add_assistant_message("Assistant message", tokens=20)

        # Verify index_message was called via _store_memory
        assert session_manager_with_chroma._chroma._store_memory.called

    def test_auto_indexing_silent_failure_without_chroma(self, session_manager_without_chroma):
        """Test that auto-indexing fails silently when ChromaAdapter not configured."""
        # Should not raise exception
        session_manager_without_chroma.add_user_message("Test", tokens=5)
        session_manager_without_chroma.add_assistant_message("Response", tokens=10)

        assert len(session_manager_without_chroma.session.history) == 2

    def test_index_message_handles_chroma_errors(self, session_manager_with_chroma):
        """Test that index_message handles ChromaAdapter errors gracefully."""
        from unittest.mock import AsyncMock

        # Make _store_memory raise an exception
        session_manager_with_chroma._chroma._store_memory = AsyncMock(side_effect=Exception("Test error"))

        message = Message(role="user", content="Test", tokens=5)
        result = session_manager_with_chroma.index_message(message)

        # Should return False instead of raising exception
        assert result is False

    def test_index_session_handles_chroma_errors(self, session_manager_with_chroma):
        """Test that index_session handles ChromaAdapter errors gracefully."""
        from unittest.mock import AsyncMock

        session_manager_with_chroma.add_user_message("Test", tokens=5)

        # Make _store_batch raise an exception
        session_manager_with_chroma._chroma._store_batch = AsyncMock(side_effect=Exception("Test error"))

        result = session_manager_with_chroma.index_session()

        assert result["success"] is False
        assert result["indexed"] == 0
        assert "Test error" in result["error"]

    def test_batch_indexing_includes_all_message_metadata(self, session_manager_with_chroma):
        """Test that batch indexing includes complete metadata for all messages."""
        # Clear history and add messages manually
        session_manager_with_chroma.session.history.clear()
        session_manager_with_chroma._chroma._store_batch.reset_mock()

        msg1 = Message(role="user", content="Question 1", tokens=5)
        msg2 = Message(role="assistant", content="Answer 1", tokens=10)
        session_manager_with_chroma.session.history.extend([msg1, msg2])

        session_manager_with_chroma.index_session()

        # Get the call arguments
        call_args = session_manager_with_chroma._chroma._store_batch.call_args[0][0]

        assert call_args["collection"] == "conversations"
        assert "items" in call_args
        assert len(call_args["items"]) == 2

        # Verify first item
        item1 = call_args["items"][0]
        assert item1["content"] == "Question 1"
        assert item1["metadata"]["role"] == "user"
        assert item1["metadata"]["session_id"] == session_manager_with_chroma.session.id

        # Verify second item
        item2 = call_args["items"][1]
        assert item2["content"] == "Answer 1"
        assert item2["metadata"]["role"] == "assistant"


@pytest.mark.unit
class TestSessionManagerLoadAndList:
    """Test SessionManager session loading and listing features."""

    @pytest.fixture
    def session_manager(self, tmp_path):
        """Create a session manager with temporary history directory."""
        history_dir = tmp_path / "history"
        return SessionManager(history_dir=history_dir)

    def test_list_sessions_empty_directory(self, session_manager):
        """Test list_sessions returns empty list when no sessions exist."""
        sessions = session_manager.list_sessions()
        assert sessions == []

    def test_list_sessions_returns_saved_sessions(self, session_manager):
        """Test list_sessions returns metadata for saved sessions."""
        # Save a session
        session_manager.add_user_message("Test message", tokens=10)
        session_manager.save()

        # List sessions
        sessions = session_manager.list_sessions()

        assert len(sessions) == 1
        assert sessions[0]["id"] == session_manager.session.id
        assert sessions[0]["agent"] == "ops"
        assert sessions[0]["messages"] == 1
        assert sessions[0]["tokens"] == 10

    def test_list_sessions_respects_limit(self, session_manager):
        """Test list_sessions respects the limit parameter."""
        # Create multiple sessions
        for i in range(5):
            manager = SessionManager(history_dir=session_manager.history_dir)
            manager.add_user_message(f"Message {i}", tokens=5)
            manager.save()

        # List with limit
        sessions = session_manager.list_sessions(limit=3)

        assert len(sessions) <= 3

    def test_load_session_success(self, session_manager):
        """Test load_session successfully loads a saved session."""
        # Save a session
        session_manager.add_user_message("Original message", tokens=15)
        original_id = session_manager.session.id
        session_manager.save()

        # Create new manager and load session
        new_manager = SessionManager(history_dir=session_manager.history_dir)
        success = new_manager.load_session(original_id)

        assert success is True
        assert new_manager.session.id == original_id
        assert len(new_manager.session.history) == 1
        assert new_manager.session.history[0].content == "Original message"
        assert new_manager.session.total_input_tokens == 15

    def test_load_session_nonexistent(self, session_manager):
        """Test load_session returns False for nonexistent session."""
        success = session_manager.load_session("nonexistent")
        assert success is False

    def test_load_session_last_shortcut(self, session_manager):
        """Test load_session 'last' shortcut loads most recent session."""
        # Save a session
        session_manager.add_user_message("Test", tokens=5)
        original_id = session_manager.session.id
        session_manager.save()

        # Create new manager and load "last"
        new_manager = SessionManager(history_dir=session_manager.history_dir)
        success = new_manager.load_session("last")

        assert success is True
        assert new_manager.session.id == original_id
