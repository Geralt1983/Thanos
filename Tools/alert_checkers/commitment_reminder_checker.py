#!/usr/bin/env python3
"""
Commitment Reminder Alert Checker for Thanos.

Monitors commitments for upcoming deadlines and generates low-pressure reminders.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import sys
sys.path.insert(0, str(__file__).rsplit('/Tools', 1)[0])

try:
    from .base import AlertChecker, Alert
except ImportError:
    # When run directly, use absolute imports
    from Tools.alert_checkers.base import AlertChecker, Alert

from Tools.journal import EventType
from Tools.commitment_tracker import CommitmentTracker, CommitmentStatus


class CommitmentReminderChecker(AlertChecker):
    """Check commitments for upcoming deadlines and generate reminders."""

    source = "commitment_reminder"
    check_interval = 3600  # 1 hour

    def __init__(self, commitment_tracker=None):
        """
        Initialize commitment reminder checker.

        Args:
            commitment_tracker: Optional CommitmentTracker instance. If None, creates new one.
        """
        super().__init__()
        self.tracker = commitment_tracker or CommitmentTracker()

    async def check(self) -> List[Alert]:
        """
        Check commitments for upcoming deadlines.

        Generates reminders for:
        - Commitments due within 1 day (high priority)
        - Commitments due within 3 days (medium priority)
        - Commitments due within 7 days (low priority)

        Uses low-pressure messaging to avoid nagging.

        Returns:
            List of Alert objects for upcoming commitments
        """
        alerts = []
        now = datetime.now()

        try:
            # Get all pending and in-progress commitments
            active_commitments = self.tracker.get_all_commitments(
                status=CommitmentStatus.PENDING
            )
            active_commitments.extend(
                self.tracker.get_all_commitments(status=CommitmentStatus.IN_PROGRESS)
            )

            for commitment in active_commitments:
                # Skip if no due date
                if not commitment.due_date:
                    continue

                try:
                    due_date = datetime.fromisoformat(commitment.due_date.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    continue

                # Calculate days until due
                days_until = (due_date - now).days
                hours_until = (due_date - now).total_seconds() / 3600

                # Check for overdue (shouldn't happen, but handle it)
                if hours_until < 0:
                    alerts.append(self._create_overdue_alert(commitment, abs(days_until)))
                    continue

                # Check for different reminder thresholds
                # Due within 1 day (24 hours) - high priority
                if hours_until <= 24:
                    alerts.append(self._create_reminder_alert(
                        commitment, hours_until, days_until, severity="warning"
                    ))
                # Due within 3 days - medium priority
                elif days_until <= 3:
                    alerts.append(self._create_reminder_alert(
                        commitment, hours_until, days_until, severity="info"
                    ))
                # Due within 7 days - low priority
                elif days_until <= 7:
                    alerts.append(self._create_reminder_alert(
                        commitment, hours_until, days_until, severity="debug"
                    ))

        except Exception as e:
            # Return error as alert
            alerts.append(Alert(
                type=EventType.SYNC_FAILED,
                severity="warning",
                title=f"Commitment check error: {str(e)[:50]}",
                data={'error': str(e), 'checker': self.source}
            ))

        return alerts

    def _create_reminder_alert(
        self,
        commitment,
        hours_until: float,
        days_until: int,
        severity: str
    ) -> Alert:
        """
        Create a low-pressure reminder alert for an upcoming commitment.

        Args:
            commitment: Commitment object
            hours_until: Hours until due
            days_until: Days until due
            severity: Alert severity level

        Returns:
            Alert object with reminder
        """
        # Build low-pressure message
        if hours_until < 1:
            time_phrase = "less than an hour"
        elif hours_until < 24:
            time_phrase = f"{int(hours_until)} hours"
        elif days_until == 1:
            time_phrase = "tomorrow"
        elif days_until == 2:
            time_phrase = "in 2 days"
        else:
            time_phrase = f"in {days_until} days"

        # Add person context if available
        person_context = f" to {commitment.person}" if commitment.person else ""

        # Low-pressure messaging
        if severity == "warning":
            title = f"Gentle reminder: '{commitment.title}'{person_context} due {time_phrase}"
        elif severity == "info":
            title = f"Upcoming: '{commitment.title}'{person_context} due {time_phrase}"
        else:
            title = f"On the horizon: '{commitment.title}'{person_context} due {time_phrase}"

        return Alert(
            type=EventType.COMMITMENT_DUE_SOON,
            severity=severity,
            title=title,
            data={
                'commitment_id': commitment.id,
                'title': commitment.title,
                'person': commitment.person,
                'due_date': commitment.due_date,
                'days_until': days_until,
                'hours_until': int(hours_until),
                'domain': commitment.domain,
                'priority': commitment.priority,
                'type': commitment.type
            },
            dedup_key=f"commitment_reminder:{commitment.id}:{days_until}"
        )

    def _create_overdue_alert(self, commitment, days_overdue: int) -> Alert:
        """
        Create alert for overdue commitment.

        Args:
            commitment: Commitment object
            days_overdue: Days past due date

        Returns:
            Alert object for overdue commitment
        """
        person_context = f" to {commitment.person}" if commitment.person else ""

        if days_overdue == 0:
            time_phrase = "today"
        elif days_overdue == 1:
            time_phrase = "yesterday"
        else:
            time_phrase = f"{days_overdue} days ago"

        title = f"Overdue: '{commitment.title}'{person_context} was due {time_phrase}"

        return Alert(
            type=EventType.COMMITMENT_OVERDUE,
            severity="critical",
            title=title,
            data={
                'commitment_id': commitment.id,
                'title': commitment.title,
                'person': commitment.person,
                'due_date': commitment.due_date,
                'days_overdue': days_overdue,
                'domain': commitment.domain,
                'priority': commitment.priority,
                'type': commitment.type
            },
            dedup_key=f"commitment_overdue:{commitment.id}"
        )


# For backwards compatibility and testing
def main():
    """Test the commitment reminder checker."""
    import asyncio
    from datetime import datetime, timedelta

    async def test():
        print("Commitment Reminder Checker Test")
        print("=" * 80)

        # Create tracker with test data
        tracker = CommitmentTracker()

        # Create test commitments with different deadlines
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
        three_days = (datetime.now() + timedelta(days=3)).isoformat()
        one_week = (datetime.now() + timedelta(days=7)).isoformat()

        tracker.create_commitment(
            title="Call Mom",
            due_date=tomorrow,
            domain="personal",
            priority=1,
            person="Mom"
        )

        tracker.create_commitment(
            title="Submit project proposal",
            due_date=three_days,
            domain="work",
            priority=2
        )

        tracker.create_commitment(
            title="Schedule dentist appointment",
            due_date=one_week,
            domain="personal",
            priority=3
        )

        # Create checker and run
        checker = CommitmentReminderChecker(tracker)
        alerts = await checker.check()

        print(f"\nFound {len(alerts)} alerts:\n")

        for alert in alerts:
            print(f"[{alert.severity.upper()}] {alert.title}")
            print(f"  Type: {alert.type.value}")
            if alert.data.get('person'):
                print(f"  Person: {alert.data['person']}")
            if 'days_until' in alert.data:
                print(f"  Days until: {alert.data['days_until']}")
            print()

        # Check status
        status = checker.get_status()
        print(f"Checker Status:")
        print(f"  Source: {status['source']}")
        print(f"  Check interval: {status['check_interval']}s")
        print(f"  Last check: {status['last_check']}")
        print(f"  Error count: {status['error_count']}")

        print("\n" + "=" * 80)
        print("Test completed successfully!")

    asyncio.run(test())


if __name__ == "__main__":
    main()
