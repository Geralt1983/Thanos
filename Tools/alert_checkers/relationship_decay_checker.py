#!/usr/bin/env python3
"""
Relationship Decay Alert Checker for Thanos.

Monitors when important people haven't been mentioned in conversation recently.
Generates gentle, low-pressure reminders to prevent relationship neglect.

Designed specifically for ADHD users who may inadvertently neglect important
relationships while hyperfocused on tasks.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base import AlertChecker, Alert

import sys
sys.path.insert(0, str(__file__).rsplit('/Tools', 1)[0])

from Tools.journal import EventType
from Tools.relationship_tracker import RelationshipMentionTracker, ImportanceLevel


class RelationshipDecayChecker(AlertChecker):
    """Check for people who haven't been mentioned recently."""

    source = "relationship_decay"
    check_interval = 3600  # 1 hour (balance between attentiveness and noise)

    # Threshold days for each importance level
    THRESHOLDS = {
        ImportanceLevel.CRITICAL: 5,   # Ashley, Sullivan, Mom, Dad
        ImportanceLevel.HIGH: 7,       # Close friends, siblings
        ImportanceLevel.MEDIUM: 14,    # Colleagues, extended family
        ImportanceLevel.LOW: 30,       # Acquaintances
    }

    # Severity mapping for alerts
    SEVERITY_MAP = {
        ImportanceLevel.CRITICAL: "critical",
        ImportanceLevel.HIGH: "warning",
        ImportanceLevel.MEDIUM: "info",
        ImportanceLevel.LOW: "debug",
    }

    def __init__(self, tracker: Optional[RelationshipMentionTracker] = None):
        """
        Initialize Relationship Decay checker.

        Args:
            tracker: Optional RelationshipMentionTracker instance. If None, creates default.
        """
        super().__init__()
        self.tracker = tracker or RelationshipMentionTracker()

    async def check(self) -> List[Alert]:
        """
        Run relationship decay checks and return alerts.

        Checks each importance level for people who haven't been mentioned
        within their threshold period. Generates gentle, non-nagging reminders.

        Returns:
            List of Alert objects for stale relationships
        """
        alerts = []

        try:
            # Check each importance level with its threshold
            for importance_level, threshold_days in self.THRESHOLDS.items():
                stale = self.tracker.get_stale_relationships(
                    threshold_days=threshold_days,
                    importance=importance_level.value
                )

                for person_mention in stale:
                    # Calculate days since last mention
                    last_mentioned = datetime.fromisoformat(person_mention.last_mentioned_at)
                    days_ago = (datetime.now() - last_mentioned).days

                    # Generate alert
                    alert = self._create_decay_alert(
                        person_name=person_mention.person_name,
                        days_since_mention=days_ago,
                        importance_level=importance_level,
                        mention_count=person_mention.mention_count
                    )
                    alerts.append(alert)

        except Exception as e:
            # Return error alert if check fails
            alerts.append(Alert(
                type=EventType.SYNC_FAILED,
                severity="warning",
                title=f"Relationship check error: {str(e)[:50]}",
                data={'error': str(e), 'checker': self.source}
            ))

        return alerts

    def _create_decay_alert(
        self,
        person_name: str,
        days_since_mention: int,
        importance_level: ImportanceLevel,
        mention_count: int
    ) -> Alert:
        """
        Create a relationship decay alert.

        Uses low-pressure, gentle messaging to avoid guilt while still
        surfacing the information.

        Args:
            person_name: Name of the person
            days_since_mention: Days since last mention
            importance_level: Importance level of the person
            mention_count: Total number of times mentioned

        Returns:
            Alert object
        """
        severity = self.SEVERITY_MAP[importance_level]

        # Craft gentle, contextual messages based on importance and time
        if importance_level == ImportanceLevel.CRITICAL:
            # Family members - warm but direct
            title = f"💙 {person_name} hasn't come up in {days_since_mention} days"
            message = f"You haven't mentioned {person_name} in {days_since_mention} days. Might be a good time to check in."
        elif importance_level == ImportanceLevel.HIGH:
            # Close relationships - friendly reminder
            title = f"👋 {person_name} - {days_since_mention} days"
            message = f"{person_name} hasn't been mentioned in about {days_since_mention} days."
        elif importance_level == ImportanceLevel.MEDIUM:
            # Regular contacts - very light touch
            title = f"💬 {person_name} ({days_since_mention} days)"
            message = f"It's been {days_since_mention} days since {person_name} was mentioned."
        else:
            # Low priority - informational only
            title = f"📋 {person_name} - {days_since_mention} days"
            message = f"{person_name} last mentioned {days_since_mention} days ago."

        return Alert(
            type=EventType.ALERT_RAISED,
            severity=severity,
            title=title,
            data={
                'person_name': person_name,
                'days_since_mention': days_since_mention,
                'importance_level': importance_level.value,
                'mention_count': mention_count,
                'threshold_days': self.THRESHOLDS[importance_level],
                'message': message,
                'alert_type': 'relationship_decay'
            },
            dedup_key=f"relationship_decay:{person_name}:{days_since_mention//7}"  # Weekly dedup
        )

    def get_status(self) -> Dict[str, Any]:
        """Get checker status including relationship stats."""
        base_status = super().get_status()

        # Add relationship-specific stats
        try:
            all_people = self.tracker.get_all_people()
            critical_stale = self.tracker.get_stale_relationships(
                threshold_days=self.THRESHOLDS[ImportanceLevel.CRITICAL],
                importance=ImportanceLevel.CRITICAL.value
            )

            base_status.update({
                'total_people_tracked': len(all_people),
                'critical_people_stale': len(critical_stale),
                'thresholds': {level.value: days for level, days in self.THRESHOLDS.items()}
            })
        except Exception as e:
            base_status['stats_error'] = str(e)

        return base_status


if __name__ == "__main__":
    """Basic smoke test."""
    import asyncio

    async def test():
        checker = RelationshipDecayChecker()
        alerts = await checker.check()
        print(f"✓ RelationshipDecayChecker initialized")
        print(f"  Found {len(alerts)} alerts")

        status = checker.get_status()
        print(f"  Status: {status}")

        if alerts:
            print("\nSample alerts:")
            for alert in alerts[:3]:  # Show first 3
                print(f"  - [{alert.severity}] {alert.title}")

        print("\n✓ Smoke test passed")

    asyncio.run(test())
