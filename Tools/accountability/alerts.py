#!/usr/bin/env python3
"""
Accountability Alert Checkers.

New alert types for the Accountability Architecture:
- Brain dump queue alerts
- Impact-based priority alerts
- Planning enforcement alerts
- Work balance alerts
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.alert_checker import (
    AlertChecker,
    Alert,
    AlertType,
    AlertPriority,
)
from Tools.journal import Journal

# Handle both CLI and module imports
try:
    from .planning_enforcer import PlanningEnforcer
    from .work_prioritizer import WorkPrioritizer
    from .models import WorkPriorityMode
except ImportError:
    from planning_enforcer import PlanningEnforcer
    from work_prioritizer import WorkPrioritizer
    from models import WorkPriorityMode

logger = logging.getLogger('accountability_alerts')


# Extend AlertType enum with new types
# Note: In production, these would be added to the main AlertType enum
ACCOUNTABILITY_ALERT_TYPES = {
    'brain_dump_queue_full': 'brain_dump_queue_full',
    'brain_dump_unprocessed': 'brain_dump_unprocessed',
    'impact_high_priority': 'impact_high_priority',
    'impact_deadline_risk': 'impact_deadline_risk',
    'planning_reminder': 'planning_reminder',
    'planning_missed': 'planning_missed',
    'planning_streak_broken': 'planning_streak_broken',
    'work_client_neglected': 'work_client_neglected',
    'work_pile_growing': 'work_pile_growing',
}


class BrainDumpAlertChecker(AlertChecker):
    """
    Checks for brain dump processing alerts.

    - Queue getting full
    - Items unprocessed too long
    """

    QUEUE_FULL_THRESHOLD = 20
    UNPROCESSED_HOURS_THRESHOLD = 24

    @property
    def checker_name(self) -> str:
        return "brain_dump_checker"

    async def check(self) -> List[Alert]:
        """Check for brain dump related alerts."""
        alerts = []

        try:
            # Get brain dump queue from WorkOS
            # This would integrate with workos_get_brain_dump

            # For now, check local state
            from Tools.state_store import get_db
            db = get_db()

            # Check queue size
            try:
                result = db.execute_sql("""
                    SELECT COUNT(*) as count FROM brain_dumps
                    WHERE processed_at IS NULL
                """)
                if result and result[0].get('count', 0) >= self.QUEUE_FULL_THRESHOLD:
                    alerts.append(Alert(
                        id=self._generate_alert_id(AlertType.SYSTEM_ERROR, 'brain_dump_queue'),
                        alert_type=AlertType.SYSTEM_ERROR,
                        priority=AlertPriority.MEDIUM,
                        title="Brain Dump Queue Full",
                        message=f"You have {result[0]['count']} unprocessed brain dumps. "
                               f"Consider processing them to maintain clarity.",
                        entity_type='brain_dump',
                        metadata={
                            'queue_size': result[0]['count'],
                            'threshold': self.QUEUE_FULL_THRESHOLD,
                        }
                    ))
                    self._log_alert(alerts[-1])
            except Exception:
                pass  # Table might not exist

        except Exception as e:
            logger.error(f"Brain dump check failed: {e}")

        return alerts


class PlanningAlertChecker(AlertChecker):
    """
    Checks for daily planning alerts.

    - Reminder to plan tomorrow
    - Consequences for not planning
    - Planning streak status
    """

    @property
    def checker_name(self) -> str:
        return "planning_checker"

    async def check(self) -> List[Alert]:
        """Check for planning related alerts."""
        alerts = []

        try:
            enforcer = PlanningEnforcer()
            tomorrow = date.today() + timedelta(days=1)
            today = date.today()
            now = datetime.now()

            # Check if reminder should be sent
            reminder = enforcer.should_send_reminder(tomorrow)
            if reminder:
                priority_map = {
                    'gentle': AlertPriority.LOW,
                    'firm': AlertPriority.MEDIUM,
                    'urgent': AlertPriority.HIGH,
                    'final': AlertPriority.CRITICAL,
                }

                alert = Alert(
                    id=self._generate_alert_id(
                        AlertType.FOCUS_NO_PROGRESS,
                        f"planning_{tomorrow.isoformat()}_{reminder['urgency']}"
                    ),
                    alert_type=AlertType.FOCUS_NO_PROGRESS,  # Using existing type
                    priority=priority_map.get(reminder['urgency'], AlertPriority.MEDIUM),
                    title=f"Plan Tomorrow ({reminder['urgency'].title()})",
                    message=reminder['message'],
                    entity_type='planning',
                    entity_id=tomorrow.isoformat(),
                    metadata=reminder,
                )
                alerts.append(alert)
                self._log_alert(alert)

                # Record that reminder was sent
                enforcer.record_reminder(tomorrow)

            # Check morning consequences (7 AM - 12 PM)
            if 7 <= now.hour < 12:
                consequences = enforcer.get_consequences(today)
                if consequences.get('has_consequences'):
                    alert = Alert(
                        id=self._generate_alert_id(
                            AlertType.FOCUS_STALLED,
                            f"consequences_{today.isoformat()}"
                        ),
                        alert_type=AlertType.FOCUS_STALLED,  # Using existing type
                        priority=AlertPriority.HIGH,
                        title="Unplanned Day - Consequences Active",
                        message=consequences['message'],
                        entity_type='planning',
                        entity_id=today.isoformat(),
                        metadata=consequences,
                    )
                    alerts.append(alert)
                    self._log_alert(alert)

            # Check if planning streak is about to break
            current_streak = enforcer.get_planning_streak()
            if current_streak >= 7 and 18 <= now.hour <= 23:
                # Long streak at risk in evening
                status = enforcer.check_planning_status(tomorrow)
                if not status['was_planned']:
                    alert = Alert(
                        id=self._generate_alert_id(
                            AlertType.HABIT_STREAK_AT_RISK,
                            f"planning_streak_{current_streak}"
                        ),
                        alert_type=AlertType.HABIT_STREAK_AT_RISK,
                        priority=AlertPriority.HIGH,
                        title=f"Planning Streak at Risk: {current_streak} days!",
                        message=f"Your {current_streak}-day planning streak is at risk! "
                               f"Plan tomorrow now to maintain it.",
                        entity_type='planning',
                        metadata={
                            'current_streak': current_streak,
                            'tomorrow': tomorrow.isoformat(),
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)

        except Exception as e:
            logger.error(f"Planning check failed: {e}")

        return alerts


class WorkBalanceAlertChecker(AlertChecker):
    """
    Checks for work balance alerts.

    - Client being neglected
    - Task pile growing too large
    - Attention imbalance across clients
    """

    CLIENT_NEGLECT_DAYS = 14
    PILE_SIZE_THRESHOLD = 15

    @property
    def checker_name(self) -> str:
        return "work_balance_checker"

    async def check(self) -> List[Alert]:
        """Check for work balance alerts."""
        alerts = []

        try:
            prioritizer = WorkPrioritizer()
            workloads = await prioritizer.get_client_workloads()

            if not workloads:
                return alerts

            for workload in workloads:
                # Check for neglected client
                if workload.days_since_touch >= self.CLIENT_NEGLECT_DAYS:
                    alert = Alert(
                        id=self._generate_alert_id(
                            AlertType.FOCUS_STALLED,
                            f"neglected_{workload.client_id}"
                        ),
                        alert_type=AlertType.FOCUS_STALLED,
                        priority=AlertPriority.MEDIUM,
                        title=f"Client Neglected: {workload.client_name}",
                        message=f"Client '{workload.client_name}' hasn't been touched in "
                               f"{workload.days_since_touch} days. "
                               f"They have {workload.task_count} pending tasks.",
                        entity_type='client',
                        entity_id=str(workload.client_id),
                        metadata={
                            'days_since_touch': workload.days_since_touch,
                            'task_count': workload.task_count,
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)

                # Check for growing pile
                if workload.task_count >= self.PILE_SIZE_THRESHOLD:
                    priority = (
                        AlertPriority.HIGH if workload.task_count >= 25
                        else AlertPriority.MEDIUM
                    )
                    alert = Alert(
                        id=self._generate_alert_id(
                            AlertType.TASK_BLOCKED,
                            f"pile_{workload.client_id}"
                        ),
                        alert_type=AlertType.TASK_BLOCKED,
                        priority=priority,
                        title=f"Task Pile Growing: {workload.client_name}",
                        message=f"Client '{workload.client_name}' has {workload.task_count} tasks. "
                               f"Consider prioritizing or delegating.",
                        entity_type='client',
                        entity_id=str(workload.client_id),
                        metadata={
                            'task_count': workload.task_count,
                            'threshold': self.PILE_SIZE_THRESHOLD,
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)

            # Check overall balance
            if len(workloads) > 1:
                import statistics
                counts = [w.task_count for w in workloads]
                stddev = statistics.stdev(counts)
                mean = statistics.mean(counts)

                # High variance indicates imbalance
                if stddev > mean * 0.75 and mean > 5:
                    most_loaded = max(workloads, key=lambda w: w.task_count)
                    least_loaded = min(workloads, key=lambda w: w.task_count)

                    alert = Alert(
                        id=self._generate_alert_id(
                            AlertType.FOCUS_NO_PROGRESS,
                            "work_imbalance"
                        ),
                        alert_type=AlertType.FOCUS_NO_PROGRESS,
                        priority=AlertPriority.LOW,
                        title="Work Distribution Imbalanced",
                        message=f"'{most_loaded.client_name}' has {most_loaded.task_count} tasks while "
                               f"'{least_loaded.client_name}' has only {least_loaded.task_count}. "
                               f"Consider rebalancing attention.",
                        entity_type='work_balance',
                        metadata={
                            'most_loaded': most_loaded.client_name,
                            'most_count': most_loaded.task_count,
                            'least_loaded': least_loaded.client_name,
                            'least_count': least_loaded.task_count,
                            'stddev': stddev,
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)

        except Exception as e:
            logger.error(f"Work balance check failed: {e}")

        return alerts


# Function to get all accountability checkers
def get_accountability_checkers() -> List[AlertChecker]:
    """Get all accountability alert checkers."""
    return [
        BrainDumpAlertChecker(),
        PlanningAlertChecker(),
        WorkBalanceAlertChecker(),
    ]


# CLI interface
if __name__ == '__main__':
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description='Accountability Alert Checkers')
    parser.add_argument('--check', '-c', action='store_true', help='Run all checks')
    parser.add_argument('--planning', '-p', action='store_true', help='Check planning only')
    parser.add_argument('--work', '-w', action='store_true', help='Check work balance only')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    async def main():
        if args.planning:
            checker = PlanningAlertChecker()
            alerts = await checker.check()
        elif args.work:
            checker = WorkBalanceAlertChecker()
            alerts = await checker.check()
        else:
            checkers = get_accountability_checkers()
            alerts = []
            for checker in checkers:
                alerts.extend(await checker.check())

        print(f"\n=== {len(alerts)} Accountability Alert(s) ===\n")
        for alert in alerts:
            emoji = {
                AlertPriority.CRITICAL: '🚨',
                AlertPriority.HIGH: '⚠️',
                AlertPriority.MEDIUM: '📢',
                AlertPriority.LOW: 'ℹ️',
            }.get(alert.priority, '📝')
            print(f"{emoji} [{alert.priority.value.upper()}] {alert.title}")
            print(f"   {alert.message}")
            print()

    asyncio.run(main())
