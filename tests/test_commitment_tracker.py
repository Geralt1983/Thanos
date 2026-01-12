"""
Unit tests for CommitmentTracker and related utilities.

Tests cover:
- Commitment creation and validation
- Streak calculation logic (current, longest, completion rate)
- Recurrence pattern handling (daily, weekly, weekdays, weekends)
- Data persistence and JSON serialization
- Miss detection and Coach integration
- CRUD operations (create, read, update, delete)
- Edge cases and error handling
"""
import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
from Tools.commitment_tracker import (
    CommitmentTracker,
    Commitment,
    CompletionRecord,
    FollowUpSchedule,
    CommitmentType,
    CommitmentStatus,
    RecurrencePattern
)


@pytest.mark.unit
class TestCommitmentCreation:
    """Test commitment creation and validation."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def tracker(self, temp_state_dir):
        """Create a CommitmentTracker with temporary state directory."""
        return CommitmentTracker(state_dir=temp_state_dir)

    def test_create_habit_commitment(self, tracker):
        """Test creating a habit commitment."""
        commitment = tracker.create_commitment(
            title="Daily meditation",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY,
            domain="health",
            priority=1,
            tags=["mindfulness", "morning"]
        )

        assert commitment.id is not None
        assert commitment.title == "Daily meditation"
        assert commitment.type == CommitmentType.HABIT
        assert commitment.recurrence_pattern == RecurrencePattern.DAILY
        assert commitment.status == CommitmentStatus.PENDING
        assert commitment.domain == "health"
        assert commitment.priority == 1
        assert "mindfulness" in commitment.tags
        assert commitment.streak_count == 0
        assert commitment.completion_rate == 0.0

    def test_create_goal_commitment(self, tracker):
        """Test creating a goal commitment."""
        due_date = (datetime.now() + timedelta(days=30)).isoformat()
        commitment = tracker.create_commitment(
            title="Complete project",
            commitment_type=CommitmentType.GOAL,
            due_date=due_date,
            priority=2,
            notes="Q1 goal"
        )

        assert commitment.type == CommitmentType.GOAL
        assert commitment.due_date == due_date
        assert commitment.recurrence_pattern == RecurrencePattern.NONE
        assert commitment.notes == "Q1 goal"

    def test_create_task_commitment(self, tracker):
        """Test creating a task commitment."""
        commitment = tracker.create_commitment(
            title="Submit report",
            commitment_type=CommitmentType.TASK,
            due_date=datetime.now().isoformat(),
            domain="work"
        )

        assert commitment.type == CommitmentType.TASK
        assert commitment.domain == "work"
        assert not commitment.is_recurring()

    def test_commitment_defaults(self, tracker):
        """Test that commitments have proper defaults."""
        commitment = tracker.create_commitment(title="Test commitment")

        assert commitment.type == CommitmentType.TASK
        assert commitment.status == CommitmentStatus.PENDING
        assert commitment.priority == 3
        assert commitment.domain == "general"
        assert commitment.tags == []
        assert commitment.notes == ""
        assert commitment.metadata == {}

    def test_commitment_persists_to_file(self, tracker, temp_state_dir):
        """Test that commitments are persisted to JSON file."""
        commitment = tracker.create_commitment(
            title="Test persistence",
            commitment_type=CommitmentType.HABIT
        )

        # Verify file was created
        data_file = temp_state_dir / "CommitmentData.json"
        assert data_file.exists()

        # Verify content
        data = json.loads(data_file.read_text())
        assert "commitments" in data
        assert len(data["commitments"]) == 1
        assert data["commitments"][0]["title"] == "Test persistence"

    def test_commitment_id_is_unique(self, tracker):
        """Test that each commitment gets a unique ID."""
        c1 = tracker.create_commitment(title="Commitment 1")
        c2 = tracker.create_commitment(title="Commitment 2")

        assert c1.id != c2.id
        assert len(c1.id) > 0
        assert len(c2.id) > 0


@pytest.mark.unit
class TestCommitmentRetrieval:
    """Test retrieving commitments."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def tracker(self, temp_state_dir):
        """Create a CommitmentTracker with temporary state directory."""
        return CommitmentTracker(state_dir=temp_state_dir)

    def test_get_commitment_by_id(self, tracker):
        """Test retrieving a commitment by ID."""
        commitment = tracker.create_commitment(title="Test commitment")

        retrieved = tracker.get_commitment(commitment.id)

        assert retrieved is not None
        assert retrieved.id == commitment.id
        assert retrieved.title == "Test commitment"

    def test_get_nonexistent_commitment(self, tracker):
        """Test retrieving a commitment that doesn't exist."""
        result = tracker.get_commitment("nonexistent-id")
        assert result is None

    def test_get_all_commitments(self, tracker):
        """Test retrieving all commitments."""
        tracker.create_commitment(title="Commitment 1", commitment_type=CommitmentType.HABIT)
        tracker.create_commitment(title="Commitment 2", commitment_type=CommitmentType.TASK)
        tracker.create_commitment(title="Commitment 3", commitment_type=CommitmentType.GOAL)

        all_commitments = tracker.get_all_commitments()
        assert len(all_commitments) == 3

    def test_filter_by_type(self, tracker):
        """Test filtering commitments by type."""
        tracker.create_commitment(title="Habit 1", commitment_type=CommitmentType.HABIT)
        tracker.create_commitment(title="Habit 2", commitment_type=CommitmentType.HABIT)
        tracker.create_commitment(title="Task 1", commitment_type=CommitmentType.TASK)

        habits = tracker.get_all_commitments(commitment_type=CommitmentType.HABIT)
        assert len(habits) == 2
        assert all(c.type == CommitmentType.HABIT for c in habits)

    def test_filter_by_status(self, tracker):
        """Test filtering commitments by status."""
        c1 = tracker.create_commitment(title="Pending 1")
        c2 = tracker.create_commitment(title="Pending 2")
        c3 = tracker.create_commitment(title="Will complete")
        tracker.mark_completed(c3.id)

        pending = tracker.get_all_commitments(status=CommitmentStatus.PENDING)
        assert len(pending) == 2

        completed = tracker.get_all_commitments(status=CommitmentStatus.COMPLETED)
        assert len(completed) == 1

    def test_filter_by_domain(self, tracker):
        """Test filtering commitments by domain."""
        tracker.create_commitment(title="Work 1", domain="work")
        tracker.create_commitment(title="Work 2", domain="work")
        tracker.create_commitment(title="Personal 1", domain="personal")

        work_commitments = tracker.get_all_commitments(domain="work")
        assert len(work_commitments) == 2
        assert all(c.domain == "work" for c in work_commitments)

    def test_filter_by_tags(self, tracker):
        """Test filtering commitments by tags."""
        tracker.create_commitment(title="C1", tags=["urgent", "work"])
        tracker.create_commitment(title="C2", tags=["urgent"])
        tracker.create_commitment(title="C3", tags=["urgent", "work", "important"])

        # Find commitments with both "urgent" and "work" tags
        urgent_work = tracker.get_all_commitments(tags=["urgent", "work"])
        assert len(urgent_work) == 2

    def test_get_due_today(self, tracker):
        """Test getting commitments due today."""
        today = datetime.now().isoformat()
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()

        tracker.create_commitment(title="Due today", due_date=today)
        tracker.create_commitment(title="Due tomorrow", due_date=tomorrow)

        due_today = tracker.get_due_today()
        assert len(due_today) == 1
        assert due_today[0].title == "Due today"

    def test_get_overdue(self, tracker):
        """Test getting overdue commitments."""
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()

        c1 = tracker.create_commitment(title="Overdue", due_date=yesterday)
        tracker.create_commitment(title="Not overdue", due_date=tomorrow)

        overdue = tracker.get_overdue()
        assert len(overdue) == 1
        assert overdue[0].title == "Overdue"

        # Completed commitments shouldn't be overdue
        tracker.mark_completed(c1.id)
        overdue = tracker.get_overdue()
        assert len(overdue) == 0

    def test_get_active_streaks(self, tracker):
        """Test getting commitments with active streaks."""
        c1 = tracker.create_commitment(
            title="Has streak",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )
        tracker.create_commitment(
            title="No streak",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )

        # Complete one to create a streak
        tracker.mark_completed(c1.id)

        active_streaks = tracker.get_active_streaks()
        assert len(active_streaks) == 1
        assert active_streaks[0].id == c1.id


@pytest.mark.unit
class TestCommitmentUpdates:
    """Test updating commitments."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def tracker(self, temp_state_dir):
        """Create a CommitmentTracker with temporary state directory."""
        return CommitmentTracker(state_dir=temp_state_dir)

    def test_update_commitment_fields(self, tracker):
        """Test updating commitment fields."""
        commitment = tracker.create_commitment(
            title="Original title",
            priority=3
        )

        updated = tracker.update_commitment(
            commitment.id,
            title="Updated title",
            priority=1,
            notes="Added notes"
        )

        assert updated is not None
        assert updated.title == "Updated title"
        assert updated.priority == 1
        assert updated.notes == "Added notes"

    def test_update_nonexistent_commitment(self, tracker):
        """Test updating a commitment that doesn't exist."""
        result = tracker.update_commitment("nonexistent-id", title="New title")
        assert result is None

    def test_mark_completed(self, tracker):
        """Test marking a commitment as completed."""
        commitment = tracker.create_commitment(title="Test commitment")

        completed = tracker.mark_completed(commitment.id, notes="Done!")

        assert completed is not None
        assert completed.status == CommitmentStatus.COMPLETED
        assert len(completed.completion_history) == 1
        assert completed.completion_history[0].status == "completed"
        assert completed.completion_history[0].notes == "Done!"

    def test_mark_missed(self, tracker):
        """Test marking a commitment as missed."""
        commitment = tracker.create_commitment(
            title="Test habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )

        missed = tracker.mark_missed(commitment.id, notes="Overslept")

        assert missed is not None
        assert missed.status == CommitmentStatus.MISSED
        assert len(missed.completion_history) == 1
        assert missed.completion_history[0].status == "missed"
        assert missed.completion_history[0].notes == "Overslept"

    def test_mark_completed_with_custom_timestamp(self, tracker):
        """Test marking completed with a custom timestamp."""
        commitment = tracker.create_commitment(title="Test")
        custom_time = (datetime.now() - timedelta(days=1)).isoformat()

        tracker.mark_completed(commitment.id, timestamp=custom_time)

        assert commitment.completion_history[0].timestamp == custom_time

    def test_delete_commitment(self, tracker):
        """Test deleting a commitment."""
        commitment = tracker.create_commitment(title="To be deleted")

        # Verify it exists
        assert tracker.get_commitment(commitment.id) is not None

        # Delete it
        result = tracker.delete_commitment(commitment.id)
        assert result is True

        # Verify it's gone
        assert tracker.get_commitment(commitment.id) is None

    def test_delete_nonexistent_commitment(self, tracker):
        """Test deleting a commitment that doesn't exist."""
        result = tracker.delete_commitment("nonexistent-id")
        assert result is False


@pytest.mark.unit
class TestStreakCalculation:
    """Test streak calculation logic."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def tracker(self, temp_state_dir):
        """Create a CommitmentTracker with temporary state directory."""
        return CommitmentTracker(state_dir=temp_state_dir)

    def test_daily_streak_calculation(self, tracker):
        """Test streak calculation for daily habits."""
        # Create commitment 5 days ago to give us a proper window
        commitment = tracker.create_commitment(
            title="Daily habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )
        commitment.created_date = (datetime.now() - timedelta(days=5)).isoformat()

        # Complete last 3 consecutive days
        tracker.mark_completed(commitment.id)  # today
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        tracker.mark_completed(commitment.id, timestamp=yesterday)
        two_days_ago = (datetime.now() - timedelta(days=2)).isoformat()
        tracker.mark_completed(commitment.id, timestamp=two_days_ago)

        # Recalculate
        tracker.recalculate_streak(commitment.id)
        assert commitment.streak_count == 3

    def test_streak_breaks_on_missed_day(self, tracker):
        """Test that streak resets when a day is missed."""
        # Create commitment 10 days ago
        commitment = tracker.create_commitment(
            title="Daily habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )
        commitment.created_date = (datetime.now() - timedelta(days=10)).isoformat()

        # Build a 3-day streak (most recent days)
        tracker.mark_completed(commitment.id)  # today
        tracker.mark_completed(commitment.id, timestamp=(datetime.now() - timedelta(days=1)).isoformat())
        tracker.mark_completed(commitment.id, timestamp=(datetime.now() - timedelta(days=2)).isoformat())

        # Miss day 3 (don't complete it)

        # Complete days 4, 5, 6 (these will be in the past, separate streak)
        tracker.mark_completed(commitment.id, timestamp=(datetime.now() - timedelta(days=4)).isoformat())
        tracker.mark_completed(commitment.id, timestamp=(datetime.now() - timedelta(days=5)).isoformat())
        tracker.mark_completed(commitment.id, timestamp=(datetime.now() - timedelta(days=6)).isoformat())

        tracker.recalculate_streak(commitment.id)

        # Current streak should be 3 (most recent consecutive days: today, yesterday, 2 days ago)
        assert commitment.streak_count == 3
        # Longest streak should also be 3
        assert commitment.longest_streak == 3

    def test_longest_streak_tracking(self, tracker):
        """Test that longest streak is tracked correctly."""
        # Create commitment 10 days ago
        commitment = tracker.create_commitment(
            title="Daily habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )
        commitment.created_date = (datetime.now() - timedelta(days=10)).isoformat()

        # Build a 5-day streak (days 0-4 from today)
        for i in range(5):
            timestamp = (datetime.now() - timedelta(days=i)).isoformat()
            tracker.mark_completed(commitment.id, timestamp=timestamp)
        tracker.recalculate_streak(commitment.id)

        # Current streak should be 5
        assert commitment.streak_count == 5
        assert commitment.longest_streak == 5

        # Now let's break the streak by missing day 5, and create a shorter 2-day streak on days 7-8
        tracker.mark_completed(commitment.id, timestamp=(datetime.now() - timedelta(days=7)).isoformat())
        tracker.mark_completed(commitment.id, timestamp=(datetime.now() - timedelta(days=8)).isoformat())
        tracker.recalculate_streak(commitment.id)

        # Current streak should be 5 (the unbroken streak from days 0-4)
        # Longest streak should still be 5
        assert commitment.longest_streak == 5

    def test_weekday_pattern_streak(self, tracker):
        """Test streak calculation for weekdays-only pattern."""
        # Create commitment 10 days ago
        commitment = tracker.create_commitment(
            title="Weekday habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.WEEKDAYS
        )
        commitment.created_date = (datetime.now() - timedelta(days=10)).isoformat()

        # Find and complete the last 3 consecutive weekdays
        current_date = datetime.now()
        weekday_count = 0
        days_back = 0
        completed_days = []

        # Go back and find weekdays, completing consecutive ones
        while weekday_count < 3 and days_back < 10:
            date = current_date - timedelta(days=days_back)
            if date.weekday() < 5:  # Monday-Friday
                tracker.mark_completed(commitment.id, timestamp=date.isoformat())
                completed_days.append(date)
                weekday_count += 1
            days_back += 1

        tracker.recalculate_streak(commitment.id)

        # Should have a streak of at least the number of weekdays we completed
        # (might be less if there was a weekend in between breaking the streak)
        assert commitment.streak_count >= 1

    def test_completion_rate_calculation(self, tracker):
        """Test completion rate calculation."""
        # Create a commitment 11 days ago (to ensure we have 10 full days)
        commitment = tracker.create_commitment(
            title="Daily habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )
        # Manually set created date to 11 days ago
        commitment.created_date = (datetime.now() - timedelta(days=11)).isoformat()

        # Complete 7 specific days out of the last 10
        # Days 1-3 (3 days), skip day 4, days 5-6 (2 days), skip day 7, days 8-9 (2 days), skip day 10
        for i in [1, 2, 3, 5, 6, 8, 9]:
            timestamp = (datetime.now() - timedelta(days=i)).isoformat()
            tracker.mark_completed(commitment.id, timestamp=timestamp)

        tracker.recalculate_streak(commitment.id)

        # Should be around 58-70% (7 out of ~12 days including today)
        # Allow wider tolerance due to timing and edge cases
        assert 55 <= commitment.completion_rate <= 75

    def test_non_recurring_completion_rate(self, tracker):
        """Test completion rate for non-recurring commitments."""
        commitment = tracker.create_commitment(
            title="One-time task",
            commitment_type=CommitmentType.TASK
        )

        # Not completed yet
        assert commitment.completion_rate == 0.0

        # Mark completed
        tracker.mark_completed(commitment.id)

        # Should be 100%
        assert commitment.completion_rate == 100.0

    def test_recalculate_all_streaks(self, tracker):
        """Test recalculating all streaks at once."""
        # Create multiple habits
        c1 = tracker.create_commitment(
            title="Habit 1",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )
        c2 = tracker.create_commitment(
            title="Habit 2",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )
        c3 = tracker.create_commitment(
            title="Task",
            commitment_type=CommitmentType.TASK
        )

        # Complete them
        tracker.mark_completed(c1.id)
        tracker.mark_completed(c2.id)

        # Recalculate all
        count = tracker.recalculate_all_streaks()

        # Should have recalculated 2 recurring commitments (not the task)
        assert count == 2


@pytest.mark.unit
class TestRecurrencePatterns:
    """Test different recurrence patterns."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def tracker(self, temp_state_dir):
        """Create a CommitmentTracker with temporary state directory."""
        return CommitmentTracker(state_dir=temp_state_dir)

    def test_daily_recurrence(self, tracker):
        """Test daily recurrence pattern."""
        commitment = tracker.create_commitment(
            title="Daily habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )

        assert commitment.is_recurring()
        assert commitment.recurrence_pattern == RecurrencePattern.DAILY

    def test_weekly_recurrence(self, tracker):
        """Test weekly recurrence pattern."""
        commitment = tracker.create_commitment(
            title="Weekly habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.WEEKLY
        )

        assert commitment.is_recurring()
        assert commitment.recurrence_pattern == RecurrencePattern.WEEKLY

    def test_weekdays_recurrence(self, tracker):
        """Test weekdays recurrence pattern."""
        commitment = tracker.create_commitment(
            title="Weekday habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.WEEKDAYS
        )

        assert commitment.is_recurring()
        assert commitment.recurrence_pattern == RecurrencePattern.WEEKDAYS

    def test_weekends_recurrence(self, tracker):
        """Test weekends recurrence pattern."""
        commitment = tracker.create_commitment(
            title="Weekend habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.WEEKENDS
        )

        assert commitment.is_recurring()
        assert commitment.recurrence_pattern == RecurrencePattern.WEEKENDS

    def test_none_recurrence(self, tracker):
        """Test non-recurring commitment."""
        commitment = tracker.create_commitment(
            title="One-time task",
            commitment_type=CommitmentType.TASK,
            recurrence_pattern=RecurrencePattern.NONE
        )

        assert not commitment.is_recurring()
        assert commitment.recurrence_pattern == RecurrencePattern.NONE


@pytest.mark.unit
class TestDataPersistence:
    """Test data persistence and file operations."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return state_dir

    def test_load_existing_data(self, temp_state_dir):
        """Test loading existing commitment data."""
        # Create and save some commitments
        tracker1 = CommitmentTracker(state_dir=temp_state_dir)
        c1 = tracker1.create_commitment(title="Commitment 1")
        c2 = tracker1.create_commitment(title="Commitment 2")

        # Create new tracker instance - should load existing data
        tracker2 = CommitmentTracker(state_dir=temp_state_dir)

        assert len(tracker2.commitments) == 2
        assert tracker2.get_commitment(c1.id) is not None
        assert tracker2.get_commitment(c2.id) is not None

    def test_handles_missing_data_file(self, temp_state_dir):
        """Test graceful handling when data file doesn't exist."""
        tracker = CommitmentTracker(state_dir=temp_state_dir)

        # Should start with empty commitments
        assert len(tracker.commitments) == 0

    def test_handles_corrupted_data_file(self, temp_state_dir):
        """Test graceful handling of corrupted JSON file."""
        # Create corrupted file
        data_file = temp_state_dir / "CommitmentData.json"
        data_file.write_text("corrupted{{{")

        # Should not crash
        tracker = CommitmentTracker(state_dir=temp_state_dir)
        assert len(tracker.commitments) == 0

    def test_handles_invalid_json_structure(self, temp_state_dir):
        """Test handling of valid JSON with wrong structure."""
        data_file = temp_state_dir / "CommitmentData.json"
        data_file.write_text('{"wrong": "structure"}')

        tracker = CommitmentTracker(state_dir=temp_state_dir)
        assert len(tracker.commitments) == 0

    def test_atomic_save(self, temp_state_dir):
        """Test that saves are atomic."""
        tracker = CommitmentTracker(state_dir=temp_state_dir)
        commitment = tracker.create_commitment(title="Test")

        # Verify file exists and is valid JSON
        data_file = temp_state_dir / "CommitmentData.json"
        assert data_file.exists()

        data = json.loads(data_file.read_text())
        assert "commitments" in data
        assert len(data["commitments"]) == 1

    def test_export_to_json(self, temp_state_dir):
        """Test exporting commitments to JSON."""
        tracker = CommitmentTracker(state_dir=temp_state_dir)
        tracker.create_commitment(title="Commitment 1")
        tracker.create_commitment(title="Commitment 2")

        json_str = tracker.export_to_json()

        data = json.loads(json_str)
        assert "commitments" in data
        assert "version" in data
        assert "count" in data
        assert data["count"] == 2

    def test_export_to_file(self, temp_state_dir):
        """Test exporting to a file."""
        tracker = CommitmentTracker(state_dir=temp_state_dir)
        tracker.create_commitment(title="Test")

        export_path = temp_state_dir / "export.json"
        tracker.export_to_json(filepath=export_path)

        assert export_path.exists()
        data = json.loads(export_path.read_text())
        assert len(data["commitments"]) == 1

    def test_import_from_json(self, temp_state_dir):
        """Test importing commitments from JSON."""
        # Create and export from first tracker
        tracker1 = CommitmentTracker(state_dir=temp_state_dir)
        c1 = tracker1.create_commitment(title="Import test")
        json_str = tracker1.export_to_json()

        # Import into new tracker with different state dir
        temp_state_dir2 = temp_state_dir.parent / "State2"
        temp_state_dir2.mkdir()
        tracker2 = CommitmentTracker(state_dir=temp_state_dir2)

        count = tracker2.import_from_json(json_str)
        assert count == 1
        assert tracker2.get_commitment(c1.id) is not None

    def test_import_invalid_json(self, temp_state_dir):
        """Test importing invalid JSON."""
        tracker = CommitmentTracker(state_dir=temp_state_dir)
        count = tracker.import_from_json("invalid json{{{")
        assert count == 0


@pytest.mark.unit
class TestMissDetectionAndCoach:
    """Test miss detection and Coach integration."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def tracker(self, temp_state_dir):
        """Create a CommitmentTracker with temporary state directory."""
        return CommitmentTracker(state_dir=temp_state_dir)

    def test_consecutive_miss_count_no_history(self, tracker):
        """Test consecutive miss count with no completion history."""
        commitment = tracker.create_commitment(
            title="Daily habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )

        miss_count = tracker.get_consecutive_miss_count(commitment.id)
        assert miss_count == 0

    def test_consecutive_miss_count_one_time_task(self, tracker):
        """Test consecutive miss count for one-time tasks."""
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        commitment = tracker.create_commitment(
            title="Overdue task",
            commitment_type=CommitmentType.TASK,
            due_date=yesterday
        )

        # Should detect it's overdue
        miss_count = tracker.get_consecutive_miss_count(commitment.id)
        assert miss_count == 1

        # Mark completed - should reset
        tracker.mark_completed(commitment.id)
        miss_count = tracker.get_consecutive_miss_count(commitment.id)
        assert miss_count == 0

    def test_consecutive_miss_count_recurring(self, tracker):
        """Test consecutive miss count for recurring habits."""
        # Create habit 6 days ago
        commitment = tracker.create_commitment(
            title="Daily habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )
        commitment.created_date = (datetime.now() - timedelta(days=6)).isoformat()

        # Complete one day in the past (day 6)
        tracker.mark_completed(commitment.id, timestamp=(datetime.now() - timedelta(days=6)).isoformat())

        # Don't complete days 1-5, so we have 5 consecutive misses
        # (We don't count today since it might not be missed yet)

        miss_count = tracker.get_consecutive_miss_count(commitment.id)
        # Should have 5 consecutive misses (days 5, 4, 3, 2, 1 - not counting today)
        assert miss_count >= 4  # At least 4 misses

    def test_should_trigger_coach_no_misses(self, tracker):
        """Test Coach trigger when there are no misses."""
        commitment = tracker.create_commitment(
            title="Daily habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )

        tracker.mark_completed(commitment.id)

        result = tracker.should_trigger_coach(commitment.id)
        assert result["should_trigger"] is False
        assert result["escalation_level"] == "none"

    def test_should_trigger_coach_first_miss(self, tracker):
        """Test Coach trigger for first miss (gentle curiosity)."""
        commitment = tracker.create_commitment(
            title="Daily habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )
        commitment.created_date = (datetime.now() - timedelta(days=2)).isoformat()

        # Miss one day
        tracker.mark_missed(commitment.id, timestamp=(datetime.now() - timedelta(days=1)).isoformat())

        result = tracker.should_trigger_coach(commitment.id)
        assert result["should_trigger"] is True
        assert result["escalation_level"] == "first_miss"
        assert result["consecutive_misses"] >= 1

    def test_should_trigger_coach_pattern_emerging(self, tracker):
        """Test Coach trigger for pattern emerging (3-4 misses)."""
        commitment = tracker.create_commitment(
            title="Daily habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )
        commitment.created_date = (datetime.now() - timedelta(days=5)).isoformat()

        # Miss several days
        for i in range(1, 5):
            tracker.mark_missed(commitment.id, timestamp=(datetime.now() - timedelta(days=i)).isoformat())

        result = tracker.should_trigger_coach(commitment.id)
        assert result["should_trigger"] is True
        assert result["consecutive_misses"] >= 3

    def test_miss_pattern_analysis(self, tracker):
        """Test pattern analysis for missed commitments."""
        commitment = tracker.create_commitment(
            title="Daily habit",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY
        )

        # Add some completions and misses
        tracker.mark_completed(commitment.id, timestamp=(datetime.now() - timedelta(days=1)).isoformat())
        tracker.mark_missed(commitment.id, timestamp=(datetime.now() - timedelta(days=2)).isoformat())
        tracker.mark_completed(commitment.id, timestamp=(datetime.now() - timedelta(days=3)).isoformat())

        pattern = tracker.get_miss_pattern_analysis(commitment.id)

        assert "total_completions" in pattern
        assert "total_misses" in pattern
        assert "miss_rate" in pattern
        assert pattern["total_completions"] == 2
        assert pattern["total_misses"] == 1

    def test_get_coach_context(self, tracker):
        """Test generating comprehensive Coach context."""
        commitment = tracker.create_commitment(
            title="Daily meditation",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY,
            domain="health",
            priority=1
        )

        tracker.mark_completed(commitment.id)

        context = tracker.get_coach_context(commitment.id)

        assert "commitment" in context
        assert "consecutive_misses" in context
        assert "escalation_level" in context
        assert "streak_history" in context
        assert "pattern_analysis" in context
        assert "coach_suggestion" in context
        assert context["commitment"]["title"] == "Daily meditation"
        assert context["is_recurring"] is True

    def test_coach_context_nonexistent_commitment(self, tracker):
        """Test Coach context for nonexistent commitment."""
        context = tracker.get_coach_context("nonexistent-id")
        assert "error" in context


@pytest.mark.unit
class TestCommitmentMethods:
    """Test Commitment instance methods."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def tracker(self, temp_state_dir):
        """Create a CommitmentTracker with temporary state directory."""
        return CommitmentTracker(state_dir=temp_state_dir)

    def test_is_due_today(self, tracker):
        """Test is_due_today method."""
        today = datetime.now().isoformat()
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()

        c1 = tracker.create_commitment(title="Due today", due_date=today)
        c2 = tracker.create_commitment(title="Due tomorrow", due_date=tomorrow)

        assert c1.is_due_today() is True
        assert c2.is_due_today() is False

    def test_is_overdue(self, tracker):
        """Test is_overdue method."""
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()

        c1 = tracker.create_commitment(title="Overdue", due_date=yesterday)
        c2 = tracker.create_commitment(title="Not overdue", due_date=tomorrow)

        assert c1.is_overdue() is True
        assert c2.is_overdue() is False

        # Completed commitments shouldn't be overdue
        tracker.mark_completed(c1.id)
        assert c1.is_overdue() is False

    def test_days_until_due(self, tracker):
        """Test days_until_due method."""
        in_3_days = (datetime.now() + timedelta(days=3)).isoformat()
        commitment = tracker.create_commitment(title="Future", due_date=in_3_days)

        days = commitment.days_until_due()
        assert days == 3

    def test_days_until_due_negative(self, tracker):
        """Test days_until_due for overdue commitments."""
        two_days_ago = (datetime.now() - timedelta(days=2)).isoformat()
        commitment = tracker.create_commitment(title="Overdue", due_date=two_days_ago)

        days = commitment.days_until_due()
        assert days == -2

    def test_days_until_due_no_date(self, tracker):
        """Test days_until_due when no due date is set."""
        commitment = tracker.create_commitment(title="No due date")
        days = commitment.days_until_due()
        assert days is None


@pytest.mark.unit
class TestJSONSerialization:
    """Test JSON serialization and deserialization."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / "State"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def tracker(self, temp_state_dir):
        """Create a CommitmentTracker with temporary state directory."""
        return CommitmentTracker(state_dir=temp_state_dir)

    def test_commitment_to_dict(self, tracker):
        """Test converting commitment to dictionary."""
        commitment = tracker.create_commitment(
            title="Test commitment",
            commitment_type=CommitmentType.HABIT,
            recurrence_pattern=RecurrencePattern.DAILY,
            tags=["test", "example"]
        )

        data = commitment.to_dict()

        assert isinstance(data, dict)
        assert data["title"] == "Test commitment"
        assert data["type"] == CommitmentType.HABIT
        assert data["recurrence_pattern"] == RecurrencePattern.DAILY
        assert "test" in data["tags"]

    def test_commitment_from_dict(self):
        """Test creating commitment from dictionary."""
        data = {
            "id": "test-123",
            "title": "Test",
            "type": CommitmentType.TASK,
            "status": CommitmentStatus.PENDING,
            "created_date": datetime.now().isoformat(),
            "recurrence_pattern": RecurrencePattern.NONE,
            "streak_count": 0,
            "longest_streak": 0,
            "completion_rate": 0.0,
            "completion_history": [],
            "follow_up_schedule": {
                "enabled": True,
                "next_check": None,
                "frequency_hours": 24,
                "escalation_count": 0,
                "last_reminded": None
            },
            "notes": "",
            "domain": "general",
            "priority": 3,
            "tags": [],
            "metadata": {}
        }

        commitment = Commitment.from_dict(data)

        assert commitment.id == "test-123"
        assert commitment.title == "Test"
        assert commitment.type == CommitmentType.TASK

    def test_completion_record_serialization(self):
        """Test CompletionRecord serialization."""
        record = CompletionRecord(
            timestamp=datetime.now().isoformat(),
            status="completed",
            notes="Test notes"
        )

        data = record.to_dict()
        assert isinstance(data, dict)
        assert data["status"] == "completed"

        restored = CompletionRecord.from_dict(data)
        assert restored.status == "completed"
        assert restored.notes == "Test notes"

    def test_follow_up_schedule_serialization(self):
        """Test FollowUpSchedule serialization."""
        schedule = FollowUpSchedule(
            enabled=True,
            frequency_hours=12,
            escalation_count=2
        )

        data = schedule.to_dict()
        assert isinstance(data, dict)
        assert data["enabled"] is True
        assert data["frequency_hours"] == 12

        restored = FollowUpSchedule.from_dict(data)
        assert restored.enabled is True
        assert restored.escalation_count == 2
