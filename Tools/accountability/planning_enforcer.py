#!/usr/bin/env python3
"""
Daily Planning Enforcer.

Ensures daily planning happens the night before with:
- Escalating reminders (8 PM, 9 PM, 10 PM, 11 PM)
- Consequence tracking when planning is skipped
- Planning streak maintenance
"""

import os
import json
import logging
from datetime import datetime, date, timedelta, time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

# Handle both CLI and module imports
try:
    from .models import PlanningRecord, PlanningStatus
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from models import PlanningRecord, PlanningStatus

logger = logging.getLogger('planning_enforcer')


class PlanningEnforcer:
    """
    Enforces daily planning with reminders and consequences.

    Planning should happen between 8 PM and 11 PM the night before.
    Missing planning results in tracked consequences.
    """

    # Reminder schedule (hour of day)
    REMINDER_HOURS = [20, 21, 22, 23]  # 8 PM, 9 PM, 10 PM, 11 PM

    # Planning criteria
    MIN_TASKS_PLANNED = 3
    MIN_GOAL_POINTS = 10

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize the planning enforcer.

        Args:
            state_dir: Directory for state files. Defaults to State/.
        """
        self.state_dir = state_dir or Path(__file__).parent.parent.parent / 'State'
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.planning_file = self.state_dir / 'planning_records.json'
        self.records: Dict[str, PlanningRecord] = {}

        self._load_records()

    def _load_records(self):
        """Load planning records from file."""
        try:
            if self.planning_file.exists():
                with open(self.planning_file) as f:
                    data = json.load(f)
                    for date_str, record_dict in data.items():
                        self.records[date_str] = PlanningRecord(
                            date=date.fromisoformat(date_str),
                            planned_at=datetime.fromisoformat(record_dict['planned_at'])
                                if record_dict.get('planned_at') else None,
                            tasks_planned=record_dict.get('tasks_planned', 0),
                            goal_set=record_dict.get('goal_set', 0),
                            was_planned=record_dict.get('was_planned', False),
                            reminder_count=record_dict.get('reminder_count', 0),
                            reminders_sent=record_dict.get('reminders_sent', []),
                            tasks_completed=record_dict.get('tasks_completed', 0),
                            goal_achieved=record_dict.get('goal_achieved', False),
                            actual_points=record_dict.get('actual_points', 0),
                            notes=record_dict.get('notes', ''),
                        )
        except Exception as e:
            logger.error(f"Failed to load planning records: {e}")

    def _save_records(self):
        """Save planning records to file."""
        try:
            data = {}
            for date_str, record in self.records.items():
                data[date_str] = record.to_dict()
            with open(self.planning_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save planning records: {e}")

    def get_record(self, target_date: date) -> PlanningRecord:
        """
        Get or create planning record for a date.

        Args:
            target_date: The date to get record for.

        Returns:
            PlanningRecord for that date.
        """
        date_str = target_date.isoformat()
        if date_str not in self.records:
            self.records[date_str] = PlanningRecord(date=target_date)
        return self.records[date_str]

    def check_planning_status(self, for_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Check if planning has been done for a date.

        Args:
            for_date: Date to check. Defaults to tomorrow.

        Returns:
            Status dict with planning info.
        """
        if for_date is None:
            for_date = date.today() + timedelta(days=1)

        record = self.get_record(for_date)

        return {
            'date': for_date.isoformat(),
            'was_planned': record.was_planned,
            'tasks_planned': record.tasks_planned,
            'goal_set': record.goal_set,
            'reminder_count': record.reminder_count,
            'needs_planning': not record.was_planned,
            'criteria_met': (
                record.tasks_planned >= self.MIN_TASKS_PLANNED and
                record.goal_set >= self.MIN_GOAL_POINTS
            ),
        }

    def mark_planned(
        self,
        for_date: date,
        tasks_planned: int,
        goal_set: int
    ) -> PlanningRecord:
        """
        Mark a day as planned.

        Args:
            for_date: The date being planned.
            tasks_planned: Number of tasks set for the day.
            goal_set: Daily point goal.

        Returns:
            Updated PlanningRecord.
        """
        record = self.get_record(for_date)

        if tasks_planned >= self.MIN_TASKS_PLANNED and goal_set >= self.MIN_GOAL_POINTS:
            record.was_planned = True
            record.planned_at = datetime.now()
            record.tasks_planned = tasks_planned
            record.goal_set = goal_set
            logger.info(f"Planning complete for {for_date}: {tasks_planned} tasks, {goal_set} points")
        else:
            logger.warning(
                f"Planning criteria not met for {for_date}: "
                f"{tasks_planned} tasks (need {self.MIN_TASKS_PLANNED}), "
                f"{goal_set} points (need {self.MIN_GOAL_POINTS})"
            )

        self._save_records()
        return record

    def record_reminder(self, for_date: date) -> int:
        """
        Record that a reminder was sent.

        Args:
            for_date: The date the reminder is for.

        Returns:
            New reminder count.
        """
        record = self.get_record(for_date)
        record.reminder_count += 1
        record.reminders_sent.append(datetime.now().isoformat())
        self._save_records()
        return record.reminder_count

    def should_send_reminder(self, for_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """
        Check if a reminder should be sent now.

        Args:
            for_date: Date to check. Defaults to tomorrow.

        Returns:
            Reminder info dict if should send, None otherwise.
        """
        if for_date is None:
            for_date = date.today() + timedelta(days=1)

        now = datetime.now()
        current_hour = now.hour

        # Only send reminders between 8 PM and 11 PM
        if current_hour not in self.REMINDER_HOURS:
            return None

        record = self.get_record(for_date)

        # Already planned
        if record.was_planned:
            return None

        # Check if we already sent a reminder this hour
        for sent_time in record.reminders_sent:
            sent_dt = datetime.fromisoformat(sent_time)
            if sent_dt.hour == current_hour and sent_dt.date() == now.date():
                return None

        # Determine urgency level
        urgency_map = {
            20: 'gentle',
            21: 'firm',
            22: 'urgent',
            23: 'final'
        }
        urgency = urgency_map.get(current_hour, 'gentle')

        return {
            'for_date': for_date.isoformat(),
            'urgency': urgency,
            'reminder_number': record.reminder_count + 1,
            'message': self._generate_reminder_message(for_date, urgency, record.reminder_count)
        }

    def _generate_reminder_message(
        self,
        for_date: date,
        urgency: str,
        reminder_count: int
    ) -> str:
        """Generate reminder message based on urgency."""
        messages = {
            'gentle': (
                f"The universe awaits balance. Tomorrow ({for_date.strftime('%A')}) "
                f"remains unplanned. What sacrifices will you make?"
            ),
            'firm': (
                f"Reality is often disappointing. But it doesn't have to be. "
                f"Plan tomorrow now, or face chaos in the morning."
            ),
            'urgent': (
                f"The hardest choices require the strongest wills. "
                f"Only 1 hour remains to plan tomorrow. Do it now."
            ),
            'final': (
                f"You could not live with your own failure. "
                f"Last chance to plan tomorrow. After this, consequences are inevitable."
            ),
        }
        return messages.get(urgency, messages['gentle'])

    def get_consequences(self, for_date: date) -> Dict[str, Any]:
        """
        Get consequences for not planning a day.

        Args:
            for_date: The unplanned date.

        Returns:
            Consequences dict.
        """
        record = self.get_record(for_date)

        if record.was_planned:
            return {'has_consequences': False}

        return {
            'has_consequences': True,
            'date': for_date.isoformat(),
            'consequences': [
                "Morning starts in reactive mode - no clear priorities",
                "Daily point target reduced by 25% (can't achieve 'perfect balance')",
                "Planning streak broken",
            ],
            'reduced_target': int(18 * 0.75),  # 25% reduction from standard 18
            'streak_broken': True,
            'reminder_count': record.reminder_count,
            'message': (
                "You could not live with your own failure. "
                "And where did that bring you? Back to chaos. "
                "Today starts without a plan. The consequences are upon you."
            ),
        }

    def get_planning_streak(self) -> int:
        """
        Calculate current planning streak.

        Returns:
            Number of consecutive planned days.
        """
        streak = 0
        check_date = date.today()

        while True:
            date_str = check_date.isoformat()
            if date_str not in self.records:
                break
            if not self.records[date_str].was_planned:
                break
            streak += 1
            check_date -= timedelta(days=1)

        return streak

    def get_planning_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get planning statistics.

        Args:
            days: Number of days to analyze.

        Returns:
            Stats dict.
        """
        today = date.today()
        planned_count = 0
        total_count = 0
        total_reminders = 0

        for i in range(days):
            check_date = today - timedelta(days=i)
            date_str = check_date.isoformat()
            if date_str in self.records:
                total_count += 1
                record = self.records[date_str]
                if record.was_planned:
                    planned_count += 1
                total_reminders += record.reminder_count

        return {
            'period_days': days,
            'days_tracked': total_count,
            'days_planned': planned_count,
            'compliance_rate': (planned_count / total_count * 100) if total_count > 0 else 0,
            'current_streak': self.get_planning_streak(),
            'total_reminders': total_reminders,
            'avg_reminders_per_day': total_reminders / total_count if total_count > 0 else 0,
        }

    def record_outcome(
        self,
        for_date: date,
        tasks_completed: int,
        actual_points: int,
        notes: str = ""
    ):
        """
        Record the outcome of a planned (or unplanned) day.

        Args:
            for_date: The date to record outcome for.
            tasks_completed: Number of tasks completed.
            actual_points: Points actually earned.
            notes: Optional notes about the day.
        """
        record = self.get_record(for_date)
        record.tasks_completed = tasks_completed
        record.actual_points = actual_points
        record.goal_achieved = actual_points >= record.goal_set if record.goal_set > 0 else False
        record.notes = notes
        self._save_records()


# Alert integration
class PlanningAlertChecker:
    """Alert checker for planning enforcement."""

    def __init__(self):
        self.enforcer = PlanningEnforcer()
        self.checker_name = "planning_checker"

    async def check(self) -> List[Dict[str, Any]]:
        """Check for planning-related alerts."""
        from Tools.alert_checker import Alert, AlertType, AlertPriority

        alerts = []
        tomorrow = date.today() + timedelta(days=1)

        # Check if reminder should be sent
        reminder = self.enforcer.should_send_reminder(tomorrow)
        if reminder:
            priority_map = {
                'gentle': AlertPriority.LOW,
                'firm': AlertPriority.MEDIUM,
                'urgent': AlertPriority.HIGH,
                'final': AlertPriority.CRITICAL,
            }

            alerts.append(Alert(
                id=f"planning_reminder_{tomorrow.isoformat()}_{reminder['urgency']}",
                alert_type=AlertType.PLANNING_REMINDER,
                priority=priority_map.get(reminder['urgency'], AlertPriority.MEDIUM),
                title=f"Plan Tomorrow ({reminder['urgency'].title()})",
                message=reminder['message'],
                entity_type='planning',
                entity_id=tomorrow.isoformat(),
                metadata=reminder,
            ))

            # Record that reminder was checked
            self.enforcer.record_reminder(tomorrow)

        # Check morning consequences
        today = date.today()
        now = datetime.now()
        if now.hour < 12:  # Only morning
            consequences = self.enforcer.get_consequences(today)
            if consequences.get('has_consequences'):
                alerts.append(Alert(
                    id=f"planning_consequences_{today.isoformat()}",
                    alert_type=AlertType.PLANNING_MISSED,
                    priority=AlertPriority.HIGH,
                    title="Unplanned Day - Consequences Active",
                    message=consequences['message'],
                    entity_type='planning',
                    entity_id=today.isoformat(),
                    metadata=consequences,
                ))

        return alerts


# CLI interface
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Planning Enforcer')
    parser.add_argument('--status', action='store_true', help='Check planning status')
    parser.add_argument('--plan', action='store_true', help='Mark tomorrow as planned')
    parser.add_argument('--tasks', type=int, default=3, help='Tasks planned')
    parser.add_argument('--goal', type=int, default=18, help='Point goal')
    parser.add_argument('--stats', action='store_true', help='Show planning stats')
    parser.add_argument('--streak', action='store_true', help='Show current streak')
    args = parser.parse_args()

    enforcer = PlanningEnforcer()

    if args.status:
        tomorrow = date.today() + timedelta(days=1)
        status = enforcer.check_planning_status(tomorrow)
        print(f"\n=== Planning Status for {tomorrow} ===")
        print(f"Planned: {'Yes' if status['was_planned'] else 'No'}")
        print(f"Tasks: {status['tasks_planned']}")
        print(f"Goal: {status['goal_set']}")
        print(f"Reminders sent: {status['reminder_count']}")

    elif args.plan:
        tomorrow = date.today() + timedelta(days=1)
        record = enforcer.mark_planned(tomorrow, args.tasks, args.goal)
        print(f"\n=== Planning Recorded ===")
        print(f"Date: {tomorrow}")
        print(f"Tasks: {args.tasks}")
        print(f"Goal: {args.goal}")
        print(f"Status: {'Complete' if record.was_planned else 'Incomplete'}")

    elif args.stats:
        stats = enforcer.get_planning_stats()
        print(f"\n=== Planning Stats (30 days) ===")
        print(f"Compliance: {stats['compliance_rate']:.1f}%")
        print(f"Current Streak: {stats['current_streak']} days")
        print(f"Avg Reminders/Day: {stats['avg_reminders_per_day']:.1f}")

    elif args.streak:
        streak = enforcer.get_planning_streak()
        print(f"Current planning streak: {streak} days")

    else:
        # Check if reminder should be sent now
        reminder = enforcer.should_send_reminder()
        if reminder:
            print(f"\n=== Reminder Due ===")
            print(f"Urgency: {reminder['urgency'].title()}")
            print(f"Message: {reminder['message']}")
        else:
            print("No reminder due at this time.")
