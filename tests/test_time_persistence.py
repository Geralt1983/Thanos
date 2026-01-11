"""
Unit tests for Time Persistence functionality.

Tests cover:
- TimeState.json creation on first interaction
- Elapsed time calculation for various time gaps
- Human-readable time formatting (minutes, hours, days)
- Corrupted file handling and recovery
- System prompt temporal context inclusion
"""
import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
from Tools.state_reader import StateReader


@pytest.mark.unit
class TestTimeStateCreation:
    """Test TimeState.json creation and persistence."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def state_reader(self, temp_state_dir):
        """Create a StateReader with temporary state directory."""
        return StateReader(temp_state_dir)

    def test_time_state_file_created_on_first_interaction(self, state_reader, temp_state_dir):
        """Test that TimeState.json is created when updating interaction."""
        time_state_path = temp_state_dir / "TimeState.json"

        # Verify file doesn't exist initially
        assert not time_state_path.exists()

        # Update last interaction
        result = state_reader.update_last_interaction("chat", "ops")

        # Verify file was created
        assert result is True
        assert time_state_path.exists()

        # Verify content is valid JSON
        data = json.loads(time_state_path.read_text())
        assert "last_interaction" in data
        assert "timestamp" in data["last_interaction"]
        assert "type" in data["last_interaction"]

    def test_time_state_preserves_session_data(self, state_reader, temp_state_dir):
        """Test that session data persists across updates."""
        # First interaction
        state_reader.update_last_interaction("chat", "ops")

        # Read first session_started
        data1 = json.loads((temp_state_dir / "TimeState.json").read_text())
        session_started = data1.get("session_started")

        # Second interaction
        state_reader.update_last_interaction("command", "coach")

        # Read again
        data2 = json.loads((temp_state_dir / "TimeState.json").read_text())

        # Session started should be preserved
        assert data2.get("session_started") == session_started

        # Interaction count should increment
        assert data2.get("interaction_count_today", 0) == 2

    def test_interaction_count_resets_on_new_day(self, state_reader, temp_state_dir):
        """Test that interaction count resets when date changes."""
        time_state_path = temp_state_dir / "TimeState.json"

        # Create state file with yesterday's timestamp
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_state = {
            "last_interaction": {
                "timestamp": yesterday.astimezone().isoformat(),
                "type": "chat"
            },
            "session_started": yesterday.astimezone().isoformat(),
            "interaction_count_today": 10
        }
        time_state_path.write_text(json.dumps(yesterday_state))

        # Update with today's interaction
        state_reader.update_last_interaction("chat")

        # Count should reset to 1
        data = json.loads(time_state_path.read_text())
        assert data.get("interaction_count_today") == 1


@pytest.mark.unit
class TestTimeDeltaCalculation:
    """Test elapsed time calculation for various gaps."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def state_reader(self, temp_state_dir):
        """Create a StateReader with temporary state directory."""
        return StateReader(temp_state_dir)

    def test_calculate_elapsed_time_first_interaction(self, state_reader, temp_state_dir):
        """Test that elapsed time returns None for first interaction."""
        # No TimeState.json exists
        elapsed = state_reader.calculate_elapsed_time()
        assert elapsed is None

    def test_calculate_elapsed_time_returns_timedelta(self, state_reader, temp_state_dir):
        """Test that elapsed time returns a timedelta after interaction."""
        # Record an interaction
        state_reader.update_last_interaction("chat")

        # Calculate elapsed time
        elapsed = state_reader.calculate_elapsed_time()

        # Should return a timedelta (close to 0)
        assert isinstance(elapsed, timedelta)
        assert elapsed.total_seconds() < 5  # Should be very recent

    def test_calculate_elapsed_time_accurate_for_hours(self, state_reader, temp_state_dir):
        """Test elapsed time calculation for hour-scale gaps."""
        time_state_path = temp_state_dir / "TimeState.json"

        # Create state with timestamp 2 hours ago
        two_hours_ago = datetime.now().astimezone() - timedelta(hours=2)
        state_data = {
            "last_interaction": {
                "timestamp": two_hours_ago.isoformat(),
                "type": "chat"
            }
        }
        time_state_path.write_text(json.dumps(state_data))

        # Calculate elapsed
        elapsed = state_reader.calculate_elapsed_time()

        # Should be approximately 2 hours (with some tolerance)
        assert elapsed is not None
        elapsed_hours = elapsed.total_seconds() / 3600
        assert 1.9 < elapsed_hours < 2.1

    def test_calculate_elapsed_time_accurate_for_days(self, state_reader, temp_state_dir):
        """Test elapsed time calculation for day-scale gaps."""
        time_state_path = temp_state_dir / "TimeState.json"

        # Create state with timestamp 3 days ago
        three_days_ago = datetime.now().astimezone() - timedelta(days=3)
        state_data = {
            "last_interaction": {
                "timestamp": three_days_ago.isoformat(),
                "type": "chat"
            }
        }
        time_state_path.write_text(json.dumps(state_data))

        # Calculate elapsed
        elapsed = state_reader.calculate_elapsed_time()

        # Should be approximately 3 days
        assert elapsed is not None
        elapsed_days = elapsed.total_seconds() / 86400
        assert 2.9 < elapsed_days < 3.1

    def test_calculate_elapsed_time_handles_missing_file(self, state_reader):
        """Test that missing TimeState.json returns None gracefully."""
        elapsed = state_reader.calculate_elapsed_time()
        assert elapsed is None


@pytest.mark.unit
class TestHumanReadableFormat:
    """Test human-readable time formatting."""

    @pytest.fixture
    def state_reader(self, tmp_path):
        """Create a StateReader with temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return StateReader(state_dir)

    def test_format_just_now(self, state_reader):
        """Test formatting for very short gaps (< 1 minute)."""
        result = state_reader.format_elapsed_time(timedelta(seconds=30))
        assert result == "just now"

    def test_format_minutes(self, state_reader):
        """Test formatting for minute-scale gaps."""
        result = state_reader.format_elapsed_time(timedelta(minutes=5))
        assert result == "5 minutes ago"

    def test_format_single_minute(self, state_reader):
        """Test singular 'minute' for exactly 1 minute."""
        result = state_reader.format_elapsed_time(timedelta(minutes=1))
        assert result == "1 minute ago"

    def test_format_hours(self, state_reader):
        """Test formatting for hour-scale gaps."""
        result = state_reader.format_elapsed_time(timedelta(hours=2))
        assert result == "2 hours ago"

    def test_format_single_hour(self, state_reader):
        """Test singular 'hour' for exactly 1 hour."""
        result = state_reader.format_elapsed_time(timedelta(hours=1))
        assert result == "1 hour ago"

    def test_format_hours_and_minutes(self, state_reader):
        """Test formatting for hours and minutes combined."""
        result = state_reader.format_elapsed_time(timedelta(hours=2, minutes=30))
        assert result == "2 hours and 30 minutes ago"

    def test_format_single_hour_and_single_minute(self, state_reader):
        """Test singular forms when both are 1."""
        result = state_reader.format_elapsed_time(timedelta(hours=1, minutes=1))
        assert result == "1 hour and 1 minute ago"

    def test_format_days(self, state_reader):
        """Test formatting for day-scale gaps."""
        result = state_reader.format_elapsed_time(timedelta(days=3))
        assert result == "3 days ago"

    def test_format_single_day(self, state_reader):
        """Test singular 'day' for exactly 1 day."""
        result = state_reader.format_elapsed_time(timedelta(days=1))
        assert result == "1 day ago"

    def test_format_days_and_hours(self, state_reader):
        """Test formatting for days and hours combined."""
        result = state_reader.format_elapsed_time(timedelta(days=1, hours=3))
        assert result == "1 day and 3 hours ago"

    def test_format_long_gap_includes_date(self, state_reader):
        """Test that gaps >7 days include the actual date."""
        result = state_reader.format_elapsed_time(timedelta(days=10))
        assert "ago" in result
        assert "on" in result.lower()

    def test_format_first_interaction(self, state_reader):
        """Test formatting when elapsed is None (first interaction)."""
        result = state_reader.format_elapsed_time(None)
        assert result == "This is our first interaction"


@pytest.mark.unit
class TestCorruptedFileHandling:
    """Test recovery from corrupted TimeState.json files."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def state_reader(self, temp_state_dir):
        """Create a StateReader with temporary state directory."""
        return StateReader(temp_state_dir)

    def test_handles_corrupted_json(self, state_reader, temp_state_dir):
        """Test recovery when TimeState.json contains invalid JSON."""
        time_state_path = temp_state_dir / "TimeState.json"
        time_state_path.write_text("corrupted{{{")

        # Should return None, not raise
        elapsed = state_reader.calculate_elapsed_time()
        assert elapsed is None

        last_time = state_reader.get_last_interaction_time()
        assert last_time is None

    def test_handles_empty_file(self, state_reader, temp_state_dir):
        """Test recovery when TimeState.json is empty."""
        time_state_path = temp_state_dir / "TimeState.json"
        time_state_path.write_text("")

        elapsed = state_reader.calculate_elapsed_time()
        assert elapsed is None

    def test_handles_wrong_structure(self, state_reader, temp_state_dir):
        """Test recovery when JSON has unexpected structure."""
        time_state_path = temp_state_dir / "TimeState.json"
        time_state_path.write_text('{"foo": "bar"}')

        elapsed = state_reader.calculate_elapsed_time()
        assert elapsed is None

        last_time = state_reader.get_last_interaction_time()
        assert last_time is None

    def test_handles_null_timestamp(self, state_reader, temp_state_dir):
        """Test recovery when timestamp is null."""
        time_state_path = temp_state_dir / "TimeState.json"
        time_state_path.write_text('{"last_interaction": {"timestamp": null}}')

        last_time = state_reader.get_last_interaction_time()
        assert last_time is None

    def test_handles_invalid_timestamp_format(self, state_reader, temp_state_dir):
        """Test recovery when timestamp is not a valid ISO format."""
        time_state_path = temp_state_dir / "TimeState.json"
        time_state_path.write_text('{"last_interaction": {"timestamp": "not-a-date"}}')

        last_time = state_reader.get_last_interaction_time()
        assert last_time is None

    def test_update_recovers_from_corruption(self, state_reader, temp_state_dir):
        """Test that update_last_interaction recovers corrupted files."""
        time_state_path = temp_state_dir / "TimeState.json"

        # Corrupt the file
        time_state_path.write_text("corrupted{{{")

        # Update should succeed and create valid state
        result = state_reader.update_last_interaction("chat")
        assert result is True

        # File should now be valid
        data = json.loads(time_state_path.read_text())
        assert "last_interaction" in data
        assert "timestamp" in data["last_interaction"]


@pytest.mark.unit
class TestSystemPromptTimeContext:
    """Test that temporal context is included in system prompt."""

    @pytest.fixture
    def temp_base_dir(self, tmp_path):
        """Create a temporary base directory with State subdirectory."""
        base_dir = tmp_path
        state_dir = base_dir / "State"
        state_dir.mkdir()
        context_dir = base_dir / "Context"
        context_dir.mkdir()
        agents_dir = base_dir / "Agents"
        agents_dir.mkdir()
        return base_dir

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client."""
        from unittest.mock import Mock
        return Mock()

    def test_system_prompt_includes_temporal_context(self, temp_base_dir, mock_api_client):
        """Test that _build_system_prompt includes temporal context section."""
        from Tools.thanos_orchestrator import ThanosOrchestrator

        # Create orchestrator with temp directory and mock API client
        orchestrator = ThanosOrchestrator(base_dir=temp_base_dir, api_client=mock_api_client)

        # Build system prompt
        prompt = orchestrator._build_system_prompt()

        # Verify temporal context is included
        assert "## Temporal Context" in prompt

    def test_time_context_includes_current_time(self, temp_base_dir, mock_api_client):
        """Test that time context includes current time."""
        from Tools.thanos_orchestrator import ThanosOrchestrator

        orchestrator = ThanosOrchestrator(base_dir=temp_base_dir, api_client=mock_api_client)
        time_context = orchestrator._build_time_context()

        assert "Current time:" in time_context

    def test_time_context_includes_last_interaction(self, temp_base_dir, mock_api_client):
        """Test that time context includes last interaction info."""
        from Tools.thanos_orchestrator import ThanosOrchestrator

        orchestrator = ThanosOrchestrator(base_dir=temp_base_dir, api_client=mock_api_client)

        # Record an interaction first
        orchestrator.state_reader.update_last_interaction("chat")

        time_context = orchestrator._build_time_context()

        assert "Last interaction:" in time_context

    def test_time_context_first_interaction(self, temp_base_dir, mock_api_client):
        """Test time context when no previous interaction exists."""
        from Tools.thanos_orchestrator import ThanosOrchestrator

        orchestrator = ThanosOrchestrator(base_dir=temp_base_dir, api_client=mock_api_client)
        time_context = orchestrator._build_time_context()

        # Should indicate first interaction
        assert "first" in time_context.lower() or "First" in time_context
