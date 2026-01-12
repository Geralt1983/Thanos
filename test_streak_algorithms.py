#!/usr/bin/env python3
"""
Test script for streak calculation algorithms.

This script tests the enhanced streak tracking functionality for:
- Current streak calculation
- Longest streak tracking
- Completion rate calculation
- Different recurrence patterns (daily, weekly, weekdays, weekends)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import shutil

# Add Tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "Tools"))

from commitment_tracker import (
    CommitmentTracker,
    CommitmentType,
    RecurrencePattern,
    CompletionRecord
)


def test_daily_streak():
    """Test daily habit streak calculation."""
    print("\n" + "=" * 60)
    print("TEST: Daily Habit Streak")
    print("=" * 60)

    # Create tracker with temp state
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    tracker = CommitmentTracker(state_dir=temp_dir)

    # Create daily habit
    habit = tracker.create_commitment(
        title="Daily meditation",
        commitment_type=CommitmentType.HABIT,
        recurrence_pattern=RecurrencePattern.DAILY,
        domain="health"
    )

    # Manually set created_date to 5 days ago for testing
    habit.created_date = (datetime.now() - timedelta(days=5)).isoformat()

    # Add completions for the last 3 days (consecutive)
    for i in range(3):
        timestamp = (datetime.now() - timedelta(days=2-i)).isoformat()
        record = CompletionRecord(
            timestamp=timestamp,
            status="completed",
            notes=f"Day {i+1}"
        )
        habit.completion_history.append(record)

    # Update streak
    tracker._update_streak(habit)

    print(f"Created: {habit.created_date}")
    print(f"Completions: {len(habit.completion_history)}")
    print(f"Current Streak: {habit.streak_count}")
    print(f"Longest Streak: {habit.longest_streak}")
    print(f"Completion Rate: {habit.completion_rate:.1f}%")

    # Verify results
    assert habit.streak_count == 3, f"Expected streak of 3, got {habit.streak_count}"
    assert habit.longest_streak == 3, f"Expected longest streak of 3, got {habit.longest_streak}"

    print("✓ Daily streak test passed!")

    # Cleanup
    shutil.rmtree(temp_dir)


def test_streak_break():
    """Test that missing a day breaks the streak."""
    print("\n" + "=" * 60)
    print("TEST: Streak Break Detection")
    print("=" * 60)

    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    tracker = CommitmentTracker(state_dir=temp_dir)

    habit = tracker.create_commitment(
        title="Daily exercise",
        commitment_type=CommitmentType.HABIT,
        recurrence_pattern=RecurrencePattern.DAILY
    )

    # Set created date to 10 days ago
    habit.created_date = (datetime.now() - timedelta(days=10)).isoformat()

    # Add completions: days 10, 9, 8 (missed), 7, 6, 5 (missed), 4, 3, 2, 1, 0
    # This should give a current streak of 4 (days 3, 2, 1, 0)
    completion_days = [10, 9, 7, 6, 3, 2, 1, 0]
    for day in completion_days:
        timestamp = (datetime.now() - timedelta(days=day)).isoformat()
        record = CompletionRecord(
            timestamp=timestamp,
            status="completed"
        )
        habit.completion_history.append(record)

    tracker._update_streak(habit)

    print(f"Completion days (days ago): {completion_days}")
    print(f"Current Streak: {habit.streak_count}")
    print(f"Longest Streak: {habit.longest_streak}")
    print(f"Completion Rate: {habit.completion_rate:.1f}%")

    # Current streak should be 4 (missed day 4)
    assert habit.streak_count == 4, f"Expected streak of 4, got {habit.streak_count}"
    # Longest streak should be 3 (days 9, 8 was missed, so days 10, 9)
    # Actually, looking at the pattern: days 10, 9 = 2, then gap, days 7, 6 = 2, gap, days 3,2,1,0 = 4
    assert habit.longest_streak >= 4, f"Expected longest streak >= 4, got {habit.longest_streak}"

    print("✓ Streak break test passed!")


def test_weekday_pattern():
    """Test weekday-only habit streak."""
    print("\n" + "=" * 60)
    print("TEST: Weekday Pattern")
    print("=" * 60)

    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    tracker = CommitmentTracker(state_dir=temp_dir)

    habit = tracker.create_commitment(
        title="Work meditation",
        commitment_type=CommitmentType.HABIT,
        recurrence_pattern=RecurrencePattern.WEEKDAYS
    )

    # Set created date to 14 days ago
    habit.created_date = (datetime.now() - timedelta(days=14)).isoformat()

    # Add completions for weekdays only in the last week
    for i in range(14):
        date = datetime.now() - timedelta(days=i)
        # Only complete on weekdays (0-4)
        if date.weekday() < 5 and i < 7:  # Last 7 days, weekdays only
            timestamp = date.isoformat()
            record = CompletionRecord(
                timestamp=timestamp,
                status="completed"
            )
            habit.completion_history.append(record)

    tracker._update_streak(habit)

    print(f"Current Streak: {habit.streak_count}")
    print(f"Longest Streak: {habit.longest_streak}")
    print(f"Completion Rate: {habit.completion_rate:.1f}%")

    # Should have a streak for weekdays in the last week
    assert habit.streak_count > 0, "Expected positive streak for weekdays"

    print("✓ Weekday pattern test passed!")


def test_completion_rate():
    """Test completion rate calculation."""
    print("\n" + "=" * 60)
    print("TEST: Completion Rate")
    print("=" * 60)

    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    tracker = CommitmentTracker(state_dir=temp_dir)

    habit = tracker.create_commitment(
        title="Daily reading",
        commitment_type=CommitmentType.HABIT,
        recurrence_pattern=RecurrencePattern.DAILY
    )

    # Set created date to 10 days ago
    habit.created_date = (datetime.now() - timedelta(days=10)).isoformat()

    # Complete 7 out of 10 days (70% completion rate)
    for i in [9, 8, 7, 5, 4, 2, 1]:
        timestamp = (datetime.now() - timedelta(days=i)).isoformat()
        record = CompletionRecord(
            timestamp=timestamp,
            status="completed"
        )
        habit.completion_history.append(record)

    tracker._update_streak(habit)

    print(f"Days tracked: 10")
    print(f"Days completed: 7")
    print(f"Completion Rate: {habit.completion_rate:.1f}%")

    # Should be approximately 70%
    # Note: Actual rate might differ slightly due to today being counted or not
    assert 60 <= habit.completion_rate <= 80, \
        f"Expected completion rate around 70%, got {habit.completion_rate:.1f}%"

    print("✓ Completion rate test passed!")


def test_mark_completed_updates_streak():
    """Test that marking as completed updates streak automatically."""
    print("\n" + "=" * 60)
    print("TEST: Mark Completed Updates Streak")
    print("=" * 60)

    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    tracker = CommitmentTracker(state_dir=temp_dir)

    habit = tracker.create_commitment(
        title="Daily pushups",
        commitment_type=CommitmentType.HABIT,
        recurrence_pattern=RecurrencePattern.DAILY
    )

    # Set created date to 2 days ago so we can complete on consecutive days
    habit.created_date = (datetime.now() - timedelta(days=2)).isoformat()

    print(f"Initial streak: {habit.streak_count}")
    assert habit.streak_count == 0, "Initial streak should be 0"

    # Mark as completed yesterday
    yesterday_timestamp = (datetime.now() - timedelta(days=1)).isoformat()
    tracker.mark_completed(habit.id, notes="First completion", timestamp=yesterday_timestamp)
    habit = tracker.get_commitment(habit.id)

    print(f"After 1st completion (yesterday): {habit.streak_count}")
    assert habit.streak_count == 1, f"Expected streak of 1, got {habit.streak_count}"

    # Mark as completed today
    tracker.mark_completed(habit.id, notes="Second completion")
    habit = tracker.get_commitment(habit.id)

    print(f"After 2nd completion (today): {habit.streak_count}")
    assert habit.streak_count == 2, f"Expected streak of 2, got {habit.streak_count}"

    print("✓ Mark completed updates streak test passed!")


def test_non_recurring_commitment():
    """Test that non-recurring commitments handle completion rate correctly."""
    print("\n" + "=" * 60)
    print("TEST: Non-Recurring Commitment")
    print("=" * 60)

    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    tracker = CommitmentTracker(state_dir=temp_dir)

    task = tracker.create_commitment(
        title="File taxes",
        commitment_type=CommitmentType.TASK,
        recurrence_pattern=RecurrencePattern.NONE
    )

    print(f"Initial completion rate: {task.completion_rate}%")
    assert task.completion_rate == 0.0, "Incomplete task should have 0% rate"

    tracker.mark_completed(task.id)
    task = tracker.get_commitment(task.id)

    print(f"After completion: {task.completion_rate}%")
    assert task.completion_rate == 100.0, "Completed task should have 100% rate"

    print("✓ Non-recurring commitment test passed!")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("STREAK ALGORITHM TEST SUITE")
    print("=" * 60)

    try:
        test_daily_streak()
        test_streak_break()
        test_weekday_pattern()
        test_completion_rate()
        test_mark_completed_updates_streak()
        test_non_recurring_commitment()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
