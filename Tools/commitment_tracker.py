#!/usr/bin/env python3
"""
Commitment Tracker - Enhanced commitment tracking with accountability features.

This module provides the core data model and management for commitments with
support for habits, goals, and tasks. Includes streak tracking, recurrence
patterns, and follow-up scheduling for ADHD-friendly accountability.

Usage:
    from Tools.commitment_tracker import CommitmentTracker, Commitment

    tracker = CommitmentTracker()
    commitment = tracker.create_commitment(
        title="Daily meditation",
        commitment_type="habit",
        recurrence_pattern="daily"
    )
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import uuid


class CommitmentType(str, Enum):
    """Types of commitments that can be tracked."""
    HABIT = "habit"
    GOAL = "goal"
    TASK = "task"


class CommitmentStatus(str, Enum):
    """Status states for a commitment."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MISSED = "missed"
    CANCELLED = "cancelled"


class RecurrencePattern(str, Enum):
    """Supported recurrence patterns for habits."""
    DAILY = "daily"
    WEEKLY = "weekly"
    WEEKDAYS = "weekdays"  # Monday-Friday
    WEEKENDS = "weekends"  # Saturday-Sunday
    CUSTOM = "custom"  # Custom days or interval
    NONE = "none"  # One-time commitment


@dataclass
class CompletionRecord:
    """Record of a single completion event."""
    timestamp: str
    status: str  # 'completed' or 'missed'
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "CompletionRecord":
        """Create from dictionary."""
        return cls(**data)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class FollowUpSchedule:
    """Follow-up scheduling configuration."""
    enabled: bool = True
    next_check: Optional[str] = None  # ISO timestamp
    frequency_hours: int = 24  # How often to check
    escalation_count: int = 0  # How many times we've escalated
    last_reminded: Optional[str] = None  # Last reminder timestamp

    @classmethod
    def from_dict(cls, data: Dict) -> "FollowUpSchedule":
        """Create from dictionary."""
        return cls(**data)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Commitment:
    """
    Core commitment data model.

    Supports habits (recurring), goals (milestone-based), and tasks (one-time).
    Includes streak tracking, completion history, and follow-up scheduling.
    """
    id: str
    title: str
    type: str  # CommitmentType
    status: str  # CommitmentStatus
    created_date: str  # ISO format
    due_date: Optional[str] = None  # ISO format
    recurrence_pattern: str = RecurrencePattern.NONE
    streak_count: int = 0
    longest_streak: int = 0
    completion_rate: float = 0.0  # Percentage (0-100)
    completion_history: List[CompletionRecord] = field(default_factory=list)
    follow_up_schedule: FollowUpSchedule = field(default_factory=FollowUpSchedule)
    notes: str = ""
    domain: str = "general"  # work, personal, health, learning
    priority: int = 3  # 1 (highest) to 5 (lowest)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and initialize after creation."""
        # Convert string enums to proper values if needed
        if isinstance(self.type, str):
            self.type = CommitmentType(self.type).value
        if isinstance(self.status, str):
            self.status = CommitmentStatus(self.status).value
        if isinstance(self.recurrence_pattern, str):
            self.recurrence_pattern = RecurrencePattern(self.recurrence_pattern).value

        # Convert dict to dataclass if needed
        if isinstance(self.follow_up_schedule, dict):
            self.follow_up_schedule = FollowUpSchedule.from_dict(self.follow_up_schedule)

        # Convert completion history dicts to objects if needed
        if self.completion_history and isinstance(self.completion_history[0], dict):
            self.completion_history = [
                CompletionRecord.from_dict(record)
                for record in self.completion_history
            ]

    @classmethod
    def from_dict(cls, data: Dict) -> "Commitment":
        """Create Commitment from dictionary."""
        # Handle nested objects
        if 'follow_up_schedule' in data and isinstance(data['follow_up_schedule'], dict):
            data['follow_up_schedule'] = FollowUpSchedule.from_dict(data['follow_up_schedule'])

        if 'completion_history' in data:
            data['completion_history'] = [
                CompletionRecord.from_dict(record) if isinstance(record, dict) else record
                for record in data['completion_history']
            ]

        return cls(**data)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert enums to strings
        data['type'] = str(self.type)
        data['status'] = str(self.status)
        data['recurrence_pattern'] = str(self.recurrence_pattern)
        return data

    def is_recurring(self) -> bool:
        """Check if this is a recurring commitment."""
        return self.recurrence_pattern != RecurrencePattern.NONE

    def is_due_today(self) -> bool:
        """Check if commitment is due today."""
        if not self.due_date:
            return False

        try:
            due = datetime.fromisoformat(self.due_date).date()
            today = datetime.now().date()
            return due == today
        except (ValueError, TypeError):
            return False

    def is_overdue(self) -> bool:
        """Check if commitment is overdue."""
        if not self.due_date:
            return False

        try:
            due = datetime.fromisoformat(self.due_date).date()
            today = datetime.now().date()
            return due < today and self.status not in [
                CommitmentStatus.COMPLETED,
                CommitmentStatus.CANCELLED
            ]
        except (ValueError, TypeError):
            return False

    def days_until_due(self) -> Optional[int]:
        """Calculate days until due date."""
        if not self.due_date:
            return None

        try:
            due = datetime.fromisoformat(self.due_date).date()
            today = datetime.now().date()
            delta = (due - today).days
            return delta
        except (ValueError, TypeError):
            return None


class CommitmentTracker:
    """
    Manages commitments with persistence and tracking capabilities.

    Provides methods for creating, updating, retrieving, and analyzing
    commitments. Handles JSON persistence and state management.
    """

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize the commitment tracker.

        Args:
            state_dir: Path to State directory (defaults to ../State)
        """
        if state_dir is None:
            state_dir = Path(__file__).parent.parent / "State"

        self.state_dir = Path(state_dir)
        self.data_file = self.state_dir / "CommitmentData.json"
        self.commitments: Dict[str, Commitment] = {}

        # Load existing commitments
        self._load()

    def _load(self) -> None:
        """Load commitments from JSON file."""
        if not self.data_file.exists():
            return

        try:
            content = self.data_file.read_text()
            data = json.loads(content)

            # Load commitments
            for commitment_data in data.get("commitments", []):
                commitment = Commitment.from_dict(commitment_data)
                self.commitments[commitment.id] = commitment

        except (json.JSONDecodeError, OSError, ValueError) as e:
            # If file is corrupted, log but don't crash
            print(f"[CommitmentTracker] Error loading data: {e}")

    def _save(self) -> bool:
        """
        Save commitments to JSON file atomically.

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            # Ensure directory exists
            self.state_dir.mkdir(parents=True, exist_ok=True)

            # Prepare data
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "commitments": [c.to_dict() for c in self.commitments.values()]
            }

            # Write atomically using a temp file
            temp_file = self.data_file.with_suffix('.json.tmp')
            temp_file.write_text(json.dumps(data, indent=2))

            # Atomic rename
            temp_file.replace(self.data_file)

            return True
        except Exception as e:
            print(f"[CommitmentTracker] Error saving data: {e}")
            return False

    def create_commitment(
        self,
        title: str,
        commitment_type: str = CommitmentType.TASK,
        status: str = CommitmentStatus.PENDING,
        due_date: Optional[str] = None,
        recurrence_pattern: str = RecurrencePattern.NONE,
        notes: str = "",
        domain: str = "general",
        priority: int = 3,
        tags: Optional[List[str]] = None,
        **metadata
    ) -> Commitment:
        """
        Create a new commitment.

        Args:
            title: Commitment title
            commitment_type: Type (habit, goal, or task)
            status: Initial status
            due_date: Due date in ISO format
            recurrence_pattern: Recurrence pattern for habits
            notes: Additional notes
            domain: Domain category
            priority: Priority level (1-5)
            tags: List of tags
            **metadata: Additional metadata

        Returns:
            Created Commitment object
        """
        # Generate unique ID
        commitment_id = str(uuid.uuid4())

        # Create commitment
        commitment = Commitment(
            id=commitment_id,
            title=title,
            type=commitment_type,
            status=status,
            created_date=datetime.now().isoformat(),
            due_date=due_date,
            recurrence_pattern=recurrence_pattern,
            notes=notes,
            domain=domain,
            priority=priority,
            tags=tags or [],
            metadata=metadata
        )

        # Set up follow-up schedule
        if due_date:
            commitment.follow_up_schedule.next_check = due_date

        # Store and save
        self.commitments[commitment_id] = commitment
        self._save()

        return commitment

    def get_commitment(self, commitment_id: str) -> Optional[Commitment]:
        """
        Get a commitment by ID.

        Args:
            commitment_id: Commitment ID

        Returns:
            Commitment if found, None otherwise
        """
        return self.commitments.get(commitment_id)

    def update_commitment(
        self,
        commitment_id: str,
        **updates
    ) -> Optional[Commitment]:
        """
        Update a commitment's fields.

        Args:
            commitment_id: Commitment ID
            **updates: Fields to update

        Returns:
            Updated Commitment if found, None otherwise
        """
        commitment = self.commitments.get(commitment_id)
        if not commitment:
            return None

        # Update allowed fields
        for key, value in updates.items():
            if hasattr(commitment, key):
                setattr(commitment, key, value)

        self._save()
        return commitment

    def mark_completed(
        self,
        commitment_id: str,
        notes: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> Optional[Commitment]:
        """
        Mark a commitment as completed.

        Args:
            commitment_id: Commitment ID
            notes: Optional completion notes
            timestamp: Completion timestamp (defaults to now)

        Returns:
            Updated Commitment if found, None otherwise
        """
        commitment = self.commitments.get(commitment_id)
        if not commitment:
            return None

        # Create completion record
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        record = CompletionRecord(
            timestamp=timestamp,
            status="completed",
            notes=notes
        )

        commitment.completion_history.append(record)
        commitment.status = CommitmentStatus.COMPLETED

        # Update streak and completion rate
        self._update_streak(commitment)

        self._save()
        return commitment

    def mark_missed(
        self,
        commitment_id: str,
        notes: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> Optional[Commitment]:
        """
        Mark a commitment as missed.

        Args:
            commitment_id: Commitment ID
            notes: Optional notes about why it was missed
            timestamp: Miss timestamp (defaults to now)

        Returns:
            Updated Commitment if found, None otherwise
        """
        commitment = self.commitments.get(commitment_id)
        if not commitment:
            return None

        # Create miss record
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        record = CompletionRecord(
            timestamp=timestamp,
            status="missed",
            notes=notes
        )

        commitment.completion_history.append(record)
        commitment.status = CommitmentStatus.MISSED

        # Update streak (will reset to 0 for recurring, update rate for all)
        if commitment.is_recurring():
            commitment.streak_count = 0
        self._update_streak(commitment)

        self._save()
        return commitment

    def _get_expected_dates(
        self,
        commitment: Commitment,
        start_date: datetime,
        end_date: datetime
    ) -> List[datetime]:
        """
        Get list of expected completion dates based on recurrence pattern.

        Args:
            commitment: Commitment with recurrence pattern
            start_date: Start date for calculation
            end_date: End date for calculation

        Returns:
            List of expected dates
        """
        expected_dates = []
        current_date = start_date.date()
        end = end_date.date()

        while current_date <= end:
            should_include = False

            if commitment.recurrence_pattern == RecurrencePattern.DAILY:
                should_include = True
            elif commitment.recurrence_pattern == RecurrencePattern.WEEKLY:
                # Weekly on the same day as start date
                if current_date.weekday() == start_date.date().weekday():
                    should_include = True
            elif commitment.recurrence_pattern == RecurrencePattern.WEEKDAYS:
                # Monday (0) to Friday (4)
                if current_date.weekday() < 5:
                    should_include = True
            elif commitment.recurrence_pattern == RecurrencePattern.WEEKENDS:
                # Saturday (5) and Sunday (6)
                if current_date.weekday() >= 5:
                    should_include = True

            if should_include:
                expected_dates.append(datetime.combine(current_date, datetime.min.time()))

            current_date += timedelta(days=1)

        return expected_dates

    def _calculate_current_streak(self, commitment: Commitment) -> int:
        """
        Calculate current streak based on consecutive completions.

        For recurring commitments, checks if expected dates were completed
        consecutively up to today.

        Args:
            commitment: Commitment to calculate streak for

        Returns:
            Current streak count
        """
        if not commitment.completion_history:
            return 0

        # Get completion dates (only successful completions)
        completion_dates = []
        for record in commitment.completion_history:
            if record.status == "completed":
                try:
                    dt = datetime.fromisoformat(record.timestamp).date()
                    completion_dates.append(dt)
                except (ValueError, TypeError):
                    continue

        if not completion_dates:
            return 0

        # Sort dates (most recent first)
        completion_dates.sort(reverse=True)

        # Get expected dates from created date to today
        try:
            created = datetime.fromisoformat(commitment.created_date)
        except (ValueError, TypeError):
            return 0

        today = datetime.now()
        expected_dates = self._get_expected_dates(commitment, created, today)

        if not expected_dates:
            return 0

        # Count consecutive completions from most recent expected date backwards
        streak = 0
        completion_set = set(completion_dates)
        today_date = today.date()

        # Start from most recent expected date and work backwards
        for expected_date in reversed(expected_dates):
            expected_date_only = expected_date.date()
            if expected_date_only in completion_set:
                streak += 1
            else:
                # Check if this date is in the future (skip it)
                if expected_date_only > today_date:
                    continue
                # Give grace period for today - don't break streak if today not completed yet
                if expected_date_only == today_date and streak == 0:
                    # Today not completed yet, but check if we have previous completions
                    continue
                # Streak is broken
                break

        return streak

    def _calculate_longest_streak(self, commitment: Commitment) -> int:
        """
        Calculate longest streak from entire completion history.

        Args:
            commitment: Commitment to calculate streak for

        Returns:
            Longest streak achieved
        """
        if not commitment.completion_history:
            return 0

        # Get completion dates (only successful completions)
        completion_dates = []
        for record in commitment.completion_history:
            if record.status == "completed":
                try:
                    dt = datetime.fromisoformat(record.timestamp).date()
                    completion_dates.append(dt)
                except (ValueError, TypeError):
                    continue

        if not completion_dates:
            return 0

        # Sort dates chronologically
        completion_dates.sort()

        # Get expected dates from created date to today
        try:
            created = datetime.fromisoformat(commitment.created_date)
        except (ValueError, TypeError):
            return 0

        today = datetime.now()
        expected_dates = self._get_expected_dates(commitment, created, today)

        if not expected_dates:
            return 0

        # Find longest consecutive streak
        completion_set = set(completion_dates)
        max_streak = 0
        current_streak = 0

        for expected_date in expected_dates:
            expected_date_only = expected_date.date()
            if expected_date_only in completion_set:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak

    def _calculate_completion_rate(self, commitment: Commitment) -> float:
        """
        Calculate completion rate as percentage of expected completions.

        For recurring commitments, calculates based on expected occurrences
        since creation date. For non-recurring, returns 100% if completed,
        0% otherwise.

        Args:
            commitment: Commitment to calculate rate for

        Returns:
            Completion rate as percentage (0-100)
        """
        if not commitment.is_recurring():
            # For non-recurring commitments
            return 100.0 if commitment.status == CommitmentStatus.COMPLETED else 0.0

        # Get expected dates from created date to today
        try:
            created = datetime.fromisoformat(commitment.created_date)
        except (ValueError, TypeError):
            return 0.0

        today = datetime.now()
        expected_dates = self._get_expected_dates(commitment, created, today)

        if not expected_dates:
            return 0.0

        # Count actual completions
        completion_dates = set()
        for record in commitment.completion_history:
            if record.status == "completed":
                try:
                    dt = datetime.fromisoformat(record.timestamp).date()
                    completion_dates.add(dt)
                except (ValueError, TypeError):
                    continue

        # Count how many expected dates were completed
        completed_count = 0
        for expected_date in expected_dates:
            expected_date_only = expected_date.date()
            # Only count dates up to today (don't penalize for future dates)
            if expected_date_only > today.date():
                continue
            if expected_date_only in completion_dates:
                completed_count += 1

        # Calculate rate based on expected dates up to today
        expected_count = sum(1 for d in expected_dates if d.date() <= today.date())
        if expected_count == 0:
            return 0.0

        return (completed_count / expected_count) * 100.0

    def _update_streak(self, commitment: Commitment) -> None:
        """
        Update streak count for a recurring commitment.

        This method recalculates:
        - Current streak (consecutive recent completions)
        - Longest streak (best streak achieved)
        - Completion rate (percentage of expected completions)

        Args:
            commitment: Commitment to update
        """
        if not commitment.is_recurring():
            # For non-recurring commitments, just update completion rate
            commitment.completion_rate = self._calculate_completion_rate(commitment)
            return

        # Calculate current streak
        commitment.streak_count = self._calculate_current_streak(commitment)

        # Calculate longest streak
        longest = self._calculate_longest_streak(commitment)
        commitment.longest_streak = max(commitment.longest_streak, longest)

        # Calculate completion rate
        commitment.completion_rate = self._calculate_completion_rate(commitment)

    def get_all_commitments(
        self,
        commitment_type: Optional[str] = None,
        status: Optional[str] = None,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Commitment]:
        """
        Get all commitments with optional filtering.

        Args:
            commitment_type: Filter by type
            status: Filter by status
            domain: Filter by domain
            tags: Filter by tags (commitment must have all specified tags)

        Returns:
            List of matching commitments
        """
        results = list(self.commitments.values())

        if commitment_type:
            results = [c for c in results if c.type == commitment_type]

        if status:
            results = [c for c in results if c.status == status]

        if domain:
            results = [c for c in results if c.domain == domain]

        if tags:
            results = [c for c in results if all(tag in c.tags for tag in tags)]

        return results

    def get_due_today(self) -> List[Commitment]:
        """Get all commitments due today."""
        return [c for c in self.commitments.values() if c.is_due_today()]

    def get_overdue(self) -> List[Commitment]:
        """Get all overdue commitments."""
        return [c for c in self.commitments.values() if c.is_overdue()]

    def get_active_streaks(self) -> List[Commitment]:
        """Get all commitments with active streaks."""
        return [
            c for c in self.commitments.values()
            if c.is_recurring() and c.streak_count > 0
        ]

    def recalculate_streak(self, commitment_id: str) -> Optional[Commitment]:
        """
        Recalculate streak data for a specific commitment.

        Useful for fixing streak data or updating after manual history edits.

        Args:
            commitment_id: Commitment ID

        Returns:
            Updated Commitment if found, None otherwise
        """
        commitment = self.commitments.get(commitment_id)
        if not commitment:
            return None

        self._update_streak(commitment)
        self._save()
        return commitment

    def recalculate_all_streaks(self) -> int:
        """
        Recalculate streak data for all recurring commitments.

        Useful for maintenance or after algorithm updates.

        Returns:
            Number of commitments updated
        """
        count = 0
        for commitment in self.commitments.values():
            if commitment.is_recurring():
                self._update_streak(commitment)
                count += 1

        if count > 0:
            self._save()

        return count

    def delete_commitment(self, commitment_id: str) -> bool:
        """
        Delete a commitment.

        Args:
            commitment_id: Commitment ID

        Returns:
            True if deleted, False if not found
        """
        if commitment_id in self.commitments:
            del self.commitments[commitment_id]
            self._save()
            return True
        return False

    def export_to_json(self, filepath: Optional[Path] = None) -> str:
        """
        Export all commitments to JSON.

        Args:
            filepath: Optional file path to save to

        Returns:
            JSON string of all commitments
        """
        data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "count": len(self.commitments),
            "commitments": [c.to_dict() for c in self.commitments.values()]
        }

        json_str = json.dumps(data, indent=2)

        if filepath:
            Path(filepath).write_text(json_str)

        return json_str

    def import_from_json(self, json_str: str) -> int:
        """
        Import commitments from JSON string.

        Args:
            json_str: JSON string to import

        Returns:
            Number of commitments imported
        """
        try:
            data = json.loads(json_str)
            count = 0

            for commitment_data in data.get("commitments", []):
                commitment = Commitment.from_dict(commitment_data)
                self.commitments[commitment.id] = commitment
                count += 1

            self._save()
            return count
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[CommitmentTracker] Import error: {e}")
            return 0


def main():
    """Test the commitment tracker."""
    tracker = CommitmentTracker()

    print("Commitment Tracker Test")
    print("=" * 60)

    # Create test commitment
    commitment = tracker.create_commitment(
        title="Daily meditation",
        commitment_type=CommitmentType.HABIT,
        recurrence_pattern=RecurrencePattern.DAILY,
        domain="health",
        priority=1,
        tags=["mindfulness", "morning"]
    )

    print(f"\nCreated commitment: {commitment.id}")
    print(f"Title: {commitment.title}")
    print(f"Type: {commitment.type}")
    print(f"Recurrence: {commitment.recurrence_pattern}")

    # Mark as completed
    tracker.mark_completed(commitment.id, notes="Completed 10-minute session")
    print(f"\nMarked as completed. Streak: {commitment.streak_count}")

    # Get all habits
    habits = tracker.get_all_commitments(commitment_type=CommitmentType.HABIT)
    print(f"\nTotal habits: {len(habits)}")

    # Export
    json_output = tracker.export_to_json()
    print(f"\nExported {len(tracker.commitments)} commitments")

    print("\n" + "=" * 60)
    print("Test completed successfully!")


if __name__ == "__main__":
    main()
