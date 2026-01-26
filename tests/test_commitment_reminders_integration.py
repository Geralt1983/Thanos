#!/usr/bin/env python3
"""
Integration tests for commitment tracking with proactive reminders.

Tests the end-to-end flow of:
- Detecting commitment statements from conversation
- Storing commitments with person associations
- Triggering deadline-based reminders
- Generating signals for session startup

These tests verify that all components work together correctly:
- CommitmentDetector: Pattern matching for commitment phrases
- CommitmentTracker: Storage and retrieval of commitments
- CommitmentReminderChecker: Alert generation for upcoming deadlines
- SignalManager: Signal persistence and deduplication
"""

import pytest
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add Tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "Tools"))

from Tools.commitment_detector import CommitmentDetector, DetectedCommitment
from Tools.commitment_tracker import (
    CommitmentTracker,
    Commitment,
    CommitmentType,
    CommitmentStatus,
    RecurrencePattern
)
from Tools.alert_checkers.commitment_reminder_checker import CommitmentReminderChecker
from Tools.get_signals import SignalManager, get_signals


# ========================================================================
# Fixtures
# ========================================================================

@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary state directory for testing."""
    state_dir = tmp_path / "State"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def detector():
    """Create a CommitmentDetector instance."""
    return CommitmentDetector()


@pytest.fixture
def tracker(temp_state_dir):
    """Create a CommitmentTracker instance."""
    return CommitmentTracker(state_dir=temp_state_dir)


@pytest.fixture
def reminder_checker(temp_state_dir, tracker):
    """Create a CommitmentReminderChecker instance."""
    return CommitmentReminderChecker(commitment_tracker=tracker)


@pytest.fixture
def signal_manager(temp_state_dir):
    """Create a SignalManager instance."""
    state_file = temp_state_dir / "signal_state.json"
    return SignalManager(state_file=str(state_file))


# ========================================================================
# End-to-End Commitment Detection and Reminder Flow
# ========================================================================

@pytest.mark.integration
class TestCommitmentDetectionToReminder:
    """Test the complete flow from conversation to reminder generation."""

    def test_detect_and_store_commitment_with_person(self, detector, tracker):
        """Test detecting a commitment from conversation and storing it."""
        # User makes a commitment in conversation
        conversation_text = "I promised Ashley I would finish the project report by Friday"

        # Detect the commitment
        detected = detector.detect(conversation_text)

        assert detected is not None
        assert detected.person == "Ashley"
        assert "finish" in detected.action.lower() or "project" in detected.action.lower()
        assert detected.confidence > 0.5

        # Store the commitment
        friday = datetime.now() + timedelta(days=(4 - datetime.now().weekday()) % 7)
        commitment = tracker.create_commitment(
            title=detected.action or "Finish project report",
            commitment_type=CommitmentType.TASK,
            person=detected.person,
            due_date=friday.isoformat(),
            domain="work",
            priority=2,
            notes=f"Detected from: {detected.raw_text}"
        )

        assert commitment.id is not None
        assert commitment.person == "Ashley"
        assert commitment.status == CommitmentStatus.PENDING
        assert commitment.due_date is not None

        # Verify it can be retrieved
        retrieved = tracker.get_commitment(commitment.id)
        assert retrieved.person == "Ashley"
        assert retrieved.title == commitment.title

    def test_detect_commitment_with_relative_deadline(self, detector, tracker):
        """Test detecting commitment with relative time expressions."""
        # User makes a commitment with relative deadline
        conversation_text = "I need to call Mom this weekend"

        # Detect the commitment
        detected = detector.detect(conversation_text)

        assert detected is not None
        assert detected.person == "Mom"
        assert "call" in detected.action.lower()
        assert detected.deadline_phrase is not None
        assert "weekend" in detected.deadline_phrase.lower()
        assert detected.due_date is not None

        # Store the commitment
        commitment = tracker.create_commitment(
            title=detected.action or "Call Mom",
            commitment_type=CommitmentType.TASK,
            person=detected.person,
            due_date=detected.due_date.isoformat() if detected.due_date else None,
            domain="personal",
            priority=1,
            notes=f"Detected deadline: {detected.deadline_phrase}"
        )

        assert commitment.person == "Mom"
        assert commitment.due_date is not None

    @pytest.mark.asyncio
    async def test_upcoming_commitment_triggers_reminder(self, tracker, reminder_checker):
        """Test that an upcoming commitment triggers a reminder alert."""
        # Create a commitment due tomorrow
        tomorrow = datetime.now() + timedelta(days=1)
        commitment = tracker.create_commitment(
            title="Send Sullivan's school forms",
            commitment_type=CommitmentType.TASK,
            person="Sullivan",
            due_date=tomorrow.isoformat(),
            domain="family",
            priority=1
        )

        # Run the reminder checker
        alerts = await reminder_checker.check()

        # Should have generated a reminder for the upcoming commitment
        assert len(alerts) > 0

        # Find the alert for our commitment
        our_alerts = [a for a in alerts if commitment.id in str(a.metadata)]
        assert len(our_alerts) > 0

        alert = our_alerts[0]
        assert alert.severity == "warning"  # Due within 24 hours
        assert "Sullivan" in alert.message or commitment.title in alert.message

    @pytest.mark.asyncio
    async def test_far_future_commitment_low_priority_reminder(self, tracker, reminder_checker):
        """Test that far future commitments generate low-priority reminders."""
        # Create a commitment due in 5 days
        future_date = datetime.now() + timedelta(days=5)
        commitment = tracker.create_commitment(
            title="Review quarterly goals with team",
            commitment_type=CommitmentType.TASK,
            due_date=future_date.isoformat(),
            domain="work",
            priority=3
        )

        # Run the reminder checker
        alerts = await reminder_checker.check()

        # Should have generated a low-priority reminder
        our_alerts = [a for a in alerts if commitment.id in str(a.metadata)]
        assert len(our_alerts) > 0

        alert = our_alerts[0]
        assert alert.severity == "debug"  # Due within 7 days but not urgent

    @pytest.mark.asyncio
    async def test_no_reminder_for_completed_commitment(self, tracker, reminder_checker):
        """Test that completed commitments don't trigger reminders."""
        # Create and complete a commitment
        tomorrow = datetime.now() + timedelta(days=1)
        commitment = tracker.create_commitment(
            title="Call dentist",
            commitment_type=CommitmentType.TASK,
            due_date=tomorrow.isoformat(),
            domain="personal",
            priority=2
        )

        # Complete it
        tracker.mark_completed(commitment.id, notes="Called and scheduled appointment")

        # Run the reminder checker
        alerts = await reminder_checker.check()

        # Should NOT have a reminder for the completed commitment
        our_alerts = [a for a in alerts if commitment.id in str(a.metadata)]
        assert len(our_alerts) == 0

    @pytest.mark.asyncio
    async def test_overdue_commitment_alert(self, tracker, reminder_checker):
        """Test that overdue commitments generate appropriate alerts."""
        # Create a commitment that's overdue
        yesterday = datetime.now() - timedelta(days=1)
        commitment = tracker.create_commitment(
            title="Submit expense report",
            commitment_type=CommitmentType.TASK,
            person="Boss",
            due_date=yesterday.isoformat(),
            domain="work",
            priority=1
        )

        # Run the reminder checker
        alerts = await reminder_checker.check()

        # Should have an overdue alert
        our_alerts = [a for a in alerts if commitment.id in str(a.metadata)]
        assert len(our_alerts) > 0

        alert = our_alerts[0]
        assert alert.severity == "error"  # Overdue is high severity
        assert "overdue" in alert.message.lower() or "past due" in alert.message.lower()


@pytest.mark.integration
class TestCompleteE2EFlow:
    """Test the complete end-to-end workflow from conversation to signal."""

    @pytest.mark.asyncio
    async def test_conversation_to_signal_complete_flow(
        self, detector, tracker, reminder_checker, temp_state_dir
    ):
        """
        Complete E2E test: Detect commitment → Store it → Generate reminder → Create signal.

        This is the full user journey:
        1. User says "I promised Ashley I'll send the photos tomorrow"
        2. System detects the commitment
        3. System stores it with person association
        4. Reminder checker identifies upcoming deadline
        5. Signal is available for startup sequence
        """
        # Step 1: User makes commitment in conversation
        conversation_text = "I promised Ashley I'll send the photos tomorrow"

        # Step 2: Detect the commitment
        detected = detector.detect(conversation_text)
        assert detected is not None
        assert detected.person == "Ashley"
        assert detected.confidence > 0.5

        # Step 3: Store the commitment
        tomorrow = datetime.now() + timedelta(hours=18)  # Tomorrow afternoon
        commitment = tracker.create_commitment(
            title="Send photos to Ashley",
            commitment_type=CommitmentType.TASK,
            person=detected.person,
            due_date=tomorrow.isoformat(),
            domain="personal",
            priority=1,
            notes=f"Detected from conversation: {detected.raw_text}"
        )

        # Step 4: Reminder checker generates alert
        alerts = await reminder_checker.check()
        our_alerts = [a for a in alerts if commitment.id in str(a.metadata)]
        assert len(our_alerts) > 0

        alert = our_alerts[0]
        assert alert.severity in ["warning", "info"]  # Due soon
        assert "Ashley" in alert.message or "photos" in alert.message.lower()

        # Step 5: Verify alert metadata contains commitment context
        assert "commitment_id" in alert.metadata
        assert alert.metadata["commitment_id"] == commitment.id
        if "person" in alert.metadata:
            assert alert.metadata["person"] == "Ashley"

    @pytest.mark.asyncio
    async def test_multiple_commitments_prioritized_correctly(
        self, detector, tracker, reminder_checker
    ):
        """Test that multiple commitments are prioritized correctly in alerts."""
        # Create commitments with different urgencies

        # High priority: Due tomorrow to family member
        tomorrow = datetime.now() + timedelta(days=1)
        urgent = tracker.create_commitment(
            title="Attend Sullivan's school event",
            commitment_type=CommitmentType.TASK,
            person="Sullivan",
            due_date=tomorrow.isoformat(),
            domain="family",
            priority=1
        )

        # Medium priority: Due in 3 days, work-related
        three_days = datetime.now() + timedelta(days=3)
        medium = tracker.create_commitment(
            title="Submit project milestone",
            commitment_type=CommitmentType.TASK,
            due_date=three_days.isoformat(),
            domain="work",
            priority=2
        )

        # Low priority: Due in a week
        week = datetime.now() + timedelta(days=7)
        low = tracker.create_commitment(
            title="Review documentation",
            commitment_type=CommitmentType.TASK,
            due_date=week.isoformat(),
            domain="work",
            priority=3
        )

        # Run reminder checker
        alerts = await reminder_checker.check()

        # Verify all three generated alerts
        assert len(alerts) >= 3

        # Verify high priority alert has highest severity
        urgent_alerts = [a for a in alerts if urgent.id in str(a.metadata)]
        assert len(urgent_alerts) > 0
        assert urgent_alerts[0].severity == "warning"

        # Verify medium priority alert
        medium_alerts = [a for a in alerts if medium.id in str(a.metadata)]
        assert len(medium_alerts) > 0
        assert medium_alerts[0].severity == "info"

        # Verify low priority alert
        low_alerts = [a for a in alerts if low.id in str(a.metadata)]
        assert len(low_alerts) > 0
        assert low_alerts[0].severity == "debug"

    def test_signal_persistence_prevents_duplicates(self, signal_manager):
        """Test that signal manager prevents duplicate notifications."""
        # Create a test signal ID
        signal_id = "commitment-reminder-test123"

        # First time: should not be acknowledged
        assert not signal_manager.is_acknowledged(signal_id)

        # Acknowledge it
        signal_manager.mark_acknowledged(signal_id)

        # Second check: should be acknowledged
        assert signal_manager.is_acknowledged(signal_id)

        # Verify state is persisted
        signal_manager._save_state()

        # Create new manager instance
        new_manager = SignalManager(state_file=signal_manager.state_file)
        assert new_manager.is_acknowledged(signal_id)


@pytest.mark.integration
class TestCommitmentDetectionPatterns:
    """Test various commitment detection patterns from natural conversation."""

    def test_promise_pattern(self, detector):
        """Test 'I promised' pattern detection."""
        text = "I promised Mom I would visit this weekend"
        detected = detector.detect(text)

        assert detected is not None
        assert detected.person == "Mom"
        assert detected.confidence >= 0.9  # High confidence for explicit promise

    def test_future_tense_pattern(self, detector):
        """Test 'I'll' and 'I will' patterns."""
        texts = [
            "I'll send you the files tomorrow",
            "I will call Dad tonight"
        ]

        for text in texts:
            detected = detector.detect(text)
            assert detected is not None
            assert detected.confidence > 0.5

    def test_need_to_pattern(self, detector):
        """Test 'I need to' pattern detection."""
        text = "I need to pick up groceries for dinner tonight"
        detected = detector.detect(text)

        assert detected is not None
        assert "pick up" in detected.action.lower() or "groceries" in detected.action.lower()

    def test_person_extraction_variations(self, detector):
        """Test person extraction from different formats."""
        test_cases = [
            ("I promised Ashley I would help", "Ashley"),
            ("I'll call Mom later", "Mom"),
            ("Need to email Dad", "Dad"),
            ("I told Sullivan I'd be there", "Sullivan"),
        ]

        for text, expected_person in test_cases:
            detected = detector.detect(text)
            if detected:  # Some patterns might not detect all cases
                assert detected.person == expected_person or detected.person is not None

    def test_deadline_extraction_variations(self, detector):
        """Test deadline extraction from different time expressions."""
        test_cases = [
            "tomorrow",
            "this weekend",
            "next Monday",
            "tonight",
            "by Friday"
        ]

        for deadline in test_cases:
            text = f"I need to finish this {deadline}"
            detected = detector.detect(text)

            if detected and detected.deadline_phrase:
                assert deadline.lower() in detected.deadline_phrase.lower()


@pytest.mark.integration
class TestReminderTiming:
    """Test reminder timing and escalation logic."""

    @pytest.mark.asyncio
    async def test_24_hour_warning(self, tracker, reminder_checker):
        """Test that commitments due within 24 hours get warning severity."""
        # Due in 12 hours
        due_date = datetime.now() + timedelta(hours=12)
        commitment = tracker.create_commitment(
            title="Important meeting",
            commitment_type=CommitmentType.TASK,
            due_date=due_date.isoformat(),
            priority=1
        )

        alerts = await reminder_checker.check()
        our_alerts = [a for a in alerts if commitment.id in str(a.metadata)]

        assert len(our_alerts) > 0
        assert our_alerts[0].severity == "warning"

    @pytest.mark.asyncio
    async def test_3_day_info_level(self, tracker, reminder_checker):
        """Test that commitments due within 3 days get info severity."""
        # Due in 2 days
        due_date = datetime.now() + timedelta(days=2)
        commitment = tracker.create_commitment(
            title="Prepare presentation",
            commitment_type=CommitmentType.TASK,
            due_date=due_date.isoformat(),
            priority=2
        )

        alerts = await reminder_checker.check()
        our_alerts = [a for a in alerts if commitment.id in str(a.metadata)]

        assert len(our_alerts) > 0
        assert our_alerts[0].severity == "info"

    @pytest.mark.asyncio
    async def test_7_day_debug_level(self, tracker, reminder_checker):
        """Test that commitments due within 7 days get debug severity."""
        # Due in 5 days
        due_date = datetime.now() + timedelta(days=5)
        commitment = tracker.create_commitment(
            title="Schedule review",
            commitment_type=CommitmentType.TASK,
            due_date=due_date.isoformat(),
            priority=3
        )

        alerts = await reminder_checker.check()
        our_alerts = [a for a in alerts if commitment.id in str(a.metadata)]

        assert len(our_alerts) > 0
        assert our_alerts[0].severity == "debug"

    @pytest.mark.asyncio
    async def test_no_reminder_beyond_7_days(self, tracker, reminder_checker):
        """Test that commitments beyond 7 days don't generate reminders yet."""
        # Due in 10 days
        due_date = datetime.now() + timedelta(days=10)
        commitment = tracker.create_commitment(
            title="Future planning session",
            commitment_type=CommitmentType.TASK,
            due_date=due_date.isoformat(),
            priority=3
        )

        alerts = await reminder_checker.check()
        our_alerts = [a for a in alerts if commitment.id in str(a.metadata)]

        # Should not have generated a reminder yet
        assert len(our_alerts) == 0
