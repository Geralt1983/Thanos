#!/usr/bin/env python3
"""
Commitment Scheduler - Determines when to prompt users about commitments.

This module provides scheduling logic for commitment follow-ups, calculating
when users should be reminded about due/overdue items based on their follow-up
schedules and respecting quiet hours configuration.

Usage:
    from Tools.commitment_scheduler import CommitmentScheduler

    scheduler = CommitmentScheduler()
    due_now = scheduler.get_commitments_needing_prompt()
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Dict, List, Optional, Any
import json


@dataclass
class ScheduledPrompt:
    """Represents a commitment that needs a prompt."""
    commitment_id: str
    commitment_title: str
    commitment_type: str
    reason: str  # 'due_today', 'overdue', 'scheduled_followup', 'habit_reminder'
    urgency: int  # 1 (highest) to 5 (lowest)
    next_check: Optional[str] = None  # ISO timestamp
    days_overdue: Optional[int] = None
    streak_count: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'commitment_id': self.commitment_id,
            'commitment_title': self.commitment_title,
            'commitment_type': self.commitment_type,
            'reason': self.reason,
            'urgency': self.urgency,
            'next_check': self.next_check,
            'days_overdue': self.days_overdue,
            'streak_count': self.streak_count
        }


class CommitmentScheduler:
    """
    Manages scheduling and timing of commitment prompts.

    Determines when to prompt users about commitments based on:
    - Due dates and overdue status
    - Follow-up schedules
    - Recurrence patterns for habits
    - Quiet hours configuration
    - Escalation logic for repeated misses
    """

    DEFAULT_QUIET_HOURS = {
        'enabled': False,
        'start_hour': 22,  # 10 PM
        'end_hour': 7      # 7 AM
    }

    def __init__(self, state_dir: Optional[Path] = None, quiet_hours: Optional[Dict] = None):
        """
        Initialize the commitment scheduler.

        Args:
            state_dir: Path to State directory (defaults to ../State)
            quiet_hours: Quiet hours configuration dict with 'enabled', 'start_hour', 'end_hour'
        """
        if state_dir is None:
            state_dir = Path(__file__).parent.parent / "State"

        self.state_dir = Path(state_dir)
        self.data_file = self.state_dir / "CommitmentData.json"
        self.quiet_hours = quiet_hours or self.DEFAULT_QUIET_HOURS.copy()

    def _load_commitment_data(self) -> Dict[str, Any]:
        """
        Load commitment data from JSON file.

        Returns:
            Dictionary containing commitment data
        """
        if not self.data_file.exists():
            return {'commitments': []}

        try:
            content = self.data_file.read_text()
            return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return {'commitments': []}

    def _save_commitment_data(self, data: Dict[str, Any]) -> bool:
        """
        Save commitment data to JSON file.

        Args:
            data: Commitment data to save

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)

            # Write atomically using temp file
            temp_file = self.data_file.with_suffix('.json.tmp')
            temp_file.write_text(json.dumps(data, indent=2))
            temp_file.replace(self.data_file)

            return True
        except Exception:
            return False

    def is_quiet_hours(self, check_time: Optional[datetime] = None) -> bool:
        """
        Check if current time is within quiet hours.

        Args:
            check_time: Time to check (defaults to now)

        Returns:
            True if within quiet hours, False otherwise
        """
        if not self.quiet_hours.get('enabled', False):
            return False

        if check_time is None:
            check_time = datetime.now()

        current_hour = check_time.hour
        start_hour = self.quiet_hours.get('start_hour', 22)
        end_hour = self.quiet_hours.get('end_hour', 7)

        # Handle overnight quiet hours (e.g., 22:00 to 7:00)
        if start_hour > end_hour:
            return current_hour >= start_hour or current_hour < end_hour
        # Handle same-day quiet hours (e.g., 14:00 to 16:00)
        else:
            return start_hour <= current_hour < end_hour

    def get_next_non_quiet_time(self, from_time: Optional[datetime] = None) -> datetime:
        """
        Get the next time outside of quiet hours.

        Args:
            from_time: Starting time (defaults to now)

        Returns:
            Next datetime outside quiet hours
        """
        if from_time is None:
            from_time = datetime.now()

        if not self.quiet_hours.get('enabled', False):
            return from_time

        if not self.is_quiet_hours(from_time):
            return from_time

        # Calculate when quiet hours end
        end_hour = self.quiet_hours.get('end_hour', 7)
        next_active = from_time.replace(hour=end_hour, minute=0, second=0, microsecond=0)

        # If end hour is earlier in the day, it's tomorrow
        start_hour = self.quiet_hours.get('start_hour', 22)
        if start_hour > end_hour and from_time.hour >= start_hour:
            next_active += timedelta(days=1)
        elif start_hour <= end_hour and from_time.hour >= end_hour:
            # Same-day quiet hours already passed
            next_active += timedelta(days=1)

        return next_active

    def calculate_next_check(
        self,
        commitment: Dict[str, Any],
        now: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Calculate the next time to check/prompt for a commitment.

        Args:
            commitment: Commitment dictionary
            now: Current time (defaults to now)

        Returns:
            Next check datetime, or None if no check needed
        """
        if now is None:
            now = datetime.now()

        status = commitment.get('status', '')

        # Don't schedule checks for completed or cancelled commitments
        if status in ['completed', 'cancelled']:
            return None

        # Get follow-up schedule
        follow_up = commitment.get('follow_up_schedule', {})
        if not follow_up.get('enabled', True):
            return None

        # Check if there's a due date
        due_date_str = commitment.get('due_date')
        if due_date_str:
            try:
                due_date = datetime.fromisoformat(due_date_str)

                # If due date is in the future, next check is the due date
                if due_date > now:
                    return due_date

                # If overdue, calculate escalating follow-up schedule
                frequency_hours = follow_up.get('frequency_hours', 24)
                escalation_count = follow_up.get('escalation_count', 0)

                # Escalation: more frequent checks as time passes
                # 0 escalations: check every frequency_hours
                # 1 escalation: check every frequency_hours / 2
                # 2+ escalations: check every frequency_hours / 4 (min 1 hour)
                if escalation_count >= 2:
                    check_interval = max(1, frequency_hours // 4)
                elif escalation_count >= 1:
                    check_interval = max(2, frequency_hours // 2)
                else:
                    check_interval = frequency_hours

                # Get last reminded time
                last_reminded_str = follow_up.get('last_reminded')
                if last_reminded_str:
                    try:
                        last_reminded = datetime.fromisoformat(last_reminded_str)
                        next_check = last_reminded + timedelta(hours=check_interval)
                    except (ValueError, TypeError):
                        next_check = now + timedelta(hours=check_interval)
                else:
                    # No previous reminder, check now
                    next_check = now

                return self.get_next_non_quiet_time(next_check)

            except (ValueError, TypeError):
                pass

        # For recurring commitments without a specific due date
        recurrence = commitment.get('recurrence_pattern', 'none')
        if recurrence != 'none':
            # Check daily for habits
            frequency_hours = follow_up.get('frequency_hours', 24)

            last_reminded_str = follow_up.get('last_reminded')
            if last_reminded_str:
                try:
                    last_reminded = datetime.fromisoformat(last_reminded_str)
                    next_check = last_reminded + timedelta(hours=frequency_hours)

                    # Only prompt if next check has passed
                    if next_check > now:
                        return next_check
                except (ValueError, TypeError):
                    pass

            # Check if completed today
            completion_history = commitment.get('completion_history', [])
            today = now.date()

            completed_today = any(
                datetime.fromisoformat(record.get('timestamp', '')).date() == today
                and record.get('status') == 'completed'
                for record in completion_history
                if record.get('timestamp')
            )

            if not completed_today:
                # Need to complete today, return next non-quiet time
                return self.get_next_non_quiet_time(now)

        return None

    def get_commitments_needing_prompt(
        self,
        now: Optional[datetime] = None,
        respect_quiet_hours: bool = True
    ) -> List[ScheduledPrompt]:
        """
        Get all commitments that need a prompt right now.

        Args:
            now: Current time (defaults to now)
            respect_quiet_hours: Whether to skip prompts during quiet hours

        Returns:
            List of ScheduledPrompt objects sorted by urgency
        """
        if now is None:
            now = datetime.now()

        # Check if we're in quiet hours
        if respect_quiet_hours and self.is_quiet_hours(now):
            return []

        data = self._load_commitment_data()
        commitments = data.get('commitments', [])

        prompts = []

        for commitment in commitments:
            status = commitment.get('status', '')

            # Skip completed or cancelled
            if status in ['completed', 'cancelled']:
                continue

            # Check if follow-up is enabled
            follow_up = commitment.get('follow_up_schedule', {})
            if not follow_up.get('enabled', True):
                continue

            # Determine if this commitment needs a prompt
            prompt = self._evaluate_commitment_for_prompt(commitment, now)
            if prompt:
                prompts.append(prompt)

        # Sort by urgency (1 is highest priority)
        prompts.sort(key=lambda p: (p.urgency, p.commitment_title))

        return prompts

    def _evaluate_commitment_for_prompt(
        self,
        commitment: Dict[str, Any],
        now: datetime
    ) -> Optional[ScheduledPrompt]:
        """
        Evaluate if a commitment needs a prompt.

        Args:
            commitment: Commitment dictionary
            now: Current time

        Returns:
            ScheduledPrompt if needed, None otherwise
        """
        commitment_id = commitment.get('id', '')
        title = commitment.get('title', 'Untitled')
        commitment_type = commitment.get('type', 'task')
        priority = commitment.get('priority', 3)

        # Check due date
        due_date_str = commitment.get('due_date')
        if due_date_str:
            try:
                due_date = datetime.fromisoformat(due_date_str)
                today = now.date()
                due_date_only = due_date.date()

                # Due today
                if due_date_only == today:
                    return ScheduledPrompt(
                        commitment_id=commitment_id,
                        commitment_title=title,
                        commitment_type=commitment_type,
                        reason='due_today',
                        urgency=min(priority, 2),  # Cap at urgency 2
                        next_check=due_date.isoformat()
                    )

                # Overdue
                if due_date_only < today:
                    days_overdue = (today - due_date_only).days

                    # Check if we should prompt based on last reminder
                    follow_up = commitment.get('follow_up_schedule', {})
                    last_reminded_str = follow_up.get('last_reminded')

                    should_prompt = True
                    if last_reminded_str:
                        try:
                            last_reminded = datetime.fromisoformat(last_reminded_str)
                            frequency_hours = follow_up.get('frequency_hours', 24)
                            escalation_count = follow_up.get('escalation_count', 0)

                            # Calculate interval with escalation
                            if escalation_count >= 2:
                                interval = max(1, frequency_hours // 4)
                            elif escalation_count >= 1:
                                interval = max(2, frequency_hours // 2)
                            else:
                                interval = frequency_hours

                            next_reminder = last_reminded + timedelta(hours=interval)
                            should_prompt = now >= next_reminder
                        except (ValueError, TypeError):
                            pass

                    if should_prompt:
                        # More overdue = higher urgency
                        urgency = 1 if days_overdue > 7 else (2 if days_overdue > 3 else 3)

                        return ScheduledPrompt(
                            commitment_id=commitment_id,
                            commitment_title=title,
                            commitment_type=commitment_type,
                            reason='overdue',
                            urgency=urgency,
                            days_overdue=days_overdue
                        )
            except (ValueError, TypeError):
                pass

        # Check recurring commitments (habits)
        recurrence = commitment.get('recurrence_pattern', 'none')
        if recurrence != 'none':
            # Check if completed today
            completion_history = commitment.get('completion_history', [])
            today = now.date()

            completed_today = any(
                datetime.fromisoformat(record.get('timestamp', '')).date() == today
                and record.get('status') == 'completed'
                for record in completion_history
                if record.get('timestamp')
            )

            if not completed_today:
                # Check if we should prompt based on last reminder
                follow_up = commitment.get('follow_up_schedule', {})
                last_reminded_str = follow_up.get('last_reminded')

                should_prompt = True
                if last_reminded_str:
                    try:
                        last_reminded = datetime.fromisoformat(last_reminded_str)
                        frequency_hours = follow_up.get('frequency_hours', 24)
                        next_reminder = last_reminded + timedelta(hours=frequency_hours)
                        should_prompt = now >= next_reminder
                    except (ValueError, TypeError):
                        pass

                if should_prompt:
                    streak_count = commitment.get('streak_count', 0)

                    return ScheduledPrompt(
                        commitment_id=commitment_id,
                        commitment_title=title,
                        commitment_type=commitment_type,
                        reason='habit_reminder',
                        urgency=priority,
                        streak_count=streak_count
                    )

        return None

    def mark_prompted(
        self,
        commitment_id: str,
        now: Optional[datetime] = None
    ) -> bool:
        """
        Mark a commitment as having been prompted.

        Updates the last_reminded timestamp and increments escalation_count
        for overdue items.

        Args:
            commitment_id: ID of the commitment
            now: Timestamp of the prompt (defaults to now)

        Returns:
            True if updated successfully, False otherwise
        """
        if now is None:
            now = datetime.now()

        data = self._load_commitment_data()
        commitments = data.get('commitments', [])

        updated = False
        for commitment in commitments:
            if commitment.get('id') == commitment_id:
                follow_up = commitment.get('follow_up_schedule', {})
                follow_up['last_reminded'] = now.isoformat()

                # Increment escalation count for overdue items
                due_date_str = commitment.get('due_date')
                if due_date_str:
                    try:
                        due_date = datetime.fromisoformat(due_date_str)
                        if due_date.date() < now.date():
                            follow_up['escalation_count'] = follow_up.get('escalation_count', 0) + 1
                    except (ValueError, TypeError):
                        pass

                commitment['follow_up_schedule'] = follow_up
                updated = True
                break

        if updated:
            data['updated_at'] = now.isoformat()
            return self._save_commitment_data(data)

        return False

    def reset_escalation(self, commitment_id: str) -> bool:
        """
        Reset escalation count for a commitment.

        Call this when a commitment is completed or updated.

        Args:
            commitment_id: ID of the commitment

        Returns:
            True if updated successfully, False otherwise
        """
        data = self._load_commitment_data()
        commitments = data.get('commitments', [])

        updated = False
        for commitment in commitments:
            if commitment.get('id') == commitment_id:
                follow_up = commitment.get('follow_up_schedule', {})
                follow_up['escalation_count'] = 0
                commitment['follow_up_schedule'] = follow_up
                updated = True
                break

        if updated:
            data['updated_at'] = datetime.now().isoformat()
            return self._save_commitment_data(data)

        return False

    def update_follow_up_schedule(
        self,
        commitment_id: str,
        frequency_hours: Optional[int] = None,
        enabled: Optional[bool] = None
    ) -> bool:
        """
        Update follow-up schedule for a commitment.

        Args:
            commitment_id: ID of the commitment
            frequency_hours: How often to check (in hours)
            enabled: Whether follow-ups are enabled

        Returns:
            True if updated successfully, False otherwise
        """
        data = self._load_commitment_data()
        commitments = data.get('commitments', [])

        updated = False
        for commitment in commitments:
            if commitment.get('id') == commitment_id:
                follow_up = commitment.get('follow_up_schedule', {})

                if frequency_hours is not None:
                    follow_up['frequency_hours'] = frequency_hours

                if enabled is not None:
                    follow_up['enabled'] = enabled

                commitment['follow_up_schedule'] = follow_up
                updated = True
                break

        if updated:
            data['updated_at'] = datetime.now().isoformat()
            return self._save_commitment_data(data)

        return False

    def get_schedule_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current schedule state.

        Returns:
            Dictionary with schedule statistics:
            - total_commitments: Total active commitments
            - prompts_needed_now: Count of commitments needing prompt
            - next_prompt_time: When the next prompt should happen
            - in_quiet_hours: Whether currently in quiet hours
            - by_reason: Count of prompts by reason
        """
        now = datetime.now()

        # Get prompts (ignore quiet hours for this summary)
        prompts = self.get_commitments_needing_prompt(now=now, respect_quiet_hours=False)

        # Count by reason
        by_reason = {}
        for prompt in prompts:
            reason = prompt.reason
            by_reason[reason] = by_reason.get(reason, 0) + 1

        # Calculate next prompt time
        data = self._load_commitment_data()
        commitments = data.get('commitments', [])

        next_times = []
        for commitment in commitments:
            next_check = self.calculate_next_check(commitment, now)
            if next_check:
                next_times.append(next_check)

        next_prompt = min(next_times) if next_times else None

        return {
            'total_active_commitments': len([
                c for c in commitments
                if c.get('status') not in ['completed', 'cancelled']
            ]),
            'prompts_needed_now': len(prompts),
            'next_prompt_time': next_prompt.isoformat() if next_prompt else None,
            'in_quiet_hours': self.is_quiet_hours(now),
            'by_reason': by_reason,
            'quiet_hours_enabled': self.quiet_hours.get('enabled', False)
        }


def main():
    """Test the commitment scheduler."""
    scheduler = CommitmentScheduler()

    print("Commitment Scheduler Test")
    print("=" * 60)

    # Get schedule summary
    summary = scheduler.get_schedule_summary()
    print("\nSchedule Summary:")
    print(f"Total active commitments: {summary['total_active_commitments']}")
    print(f"Prompts needed now: {summary['prompts_needed_now']}")
    print(f"In quiet hours: {summary['in_quiet_hours']}")
    print(f"Quiet hours enabled: {summary['quiet_hours_enabled']}")
    print(f"Next prompt time: {summary['next_prompt_time']}")
    print(f"By reason: {summary['by_reason']}")

    # Get commitments needing prompt
    prompts = scheduler.get_commitments_needing_prompt()
    print(f"\nCommitments needing prompt: {len(prompts)}")

    for prompt in prompts:
        print(f"\n  [{prompt.urgency}] {prompt.commitment_title}")
        print(f"      Type: {prompt.commitment_type}")
        print(f"      Reason: {prompt.reason}")
        if prompt.days_overdue:
            print(f"      Days overdue: {prompt.days_overdue}")
        if prompt.streak_count is not None:
            print(f"      Streak: {prompt.streak_count}")

    # Test quiet hours
    print("\n\nQuiet Hours Test:")
    print("-" * 60)
    print(f"Current time: {datetime.now().strftime('%H:%M')}")
    print(f"Is quiet hours: {scheduler.is_quiet_hours()}")

    # Test with enabled quiet hours
    scheduler_with_quiet = CommitmentScheduler(
        quiet_hours={'enabled': True, 'start_hour': 22, 'end_hour': 7}
    )
    print(f"\nWith quiet hours enabled (22:00-07:00):")
    print(f"Is quiet hours: {scheduler_with_quiet.is_quiet_hours()}")

    test_time = datetime.now().replace(hour=23, minute=30)
    print(f"\nAt 23:30: {scheduler_with_quiet.is_quiet_hours(test_time)}")
    next_active = scheduler_with_quiet.get_next_non_quiet_time(test_time)
    print(f"Next active time: {next_active.strftime('%H:%M')}")

    test_time = datetime.now().replace(hour=10, minute=0)
    print(f"\nAt 10:00: {scheduler_with_quiet.is_quiet_hours(test_time)}")

    print("\n" + "=" * 60)
    print("Test completed successfully!")


if __name__ == "__main__":
    main()
