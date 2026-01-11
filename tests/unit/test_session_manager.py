"""
Unit tests for SessionManager.

Tests cover:
- Message addition and token tracking
- Sliding window history management (MAX_HISTORY)
- History trimming logic
- Session statistics
- Agent switching
- History clearing
- Session persistence
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
