#!/usr/bin/env python3
"""
Alert Checking System for Thanos.

Provides proactive monitoring and alerting for:
- Overdue commitments and tasks
- Health metric thresholds (Oura)
- Habit streaks at risk
- Focus area progress

Part of the Clarity pillar for the Thanos architecture.
"""

import os
import logging
from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

# Setup path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.journal import Journal, EventType, Severity
from Tools.state_store import get_db
from Tools.circuit_breaker import CircuitBreaker, CircuitState

logger = logging.getLogger('alert_checker')


class AlertPriority(Enum):
    """Priority levels for alerts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts."""
    # Commitment alerts
    COMMITMENT_OVERDUE = "commitment_overdue"
    COMMITMENT_DUE_SOON = "commitment_due_soon"

    # Task alerts
    TASK_OVERDUE = "task_overdue"
    TASK_DUE_TODAY = "task_due_today"
    TASK_BLOCKED = "task_blocked"

    # Health alerts
    HEALTH_LOW_SLEEP = "health_low_sleep"
    HEALTH_LOW_READINESS = "health_low_readiness"
    HEALTH_HIGH_STRESS = "health_high_stress"
    HEALTH_LOW_HRV = "health_low_hrv"

    # Habit alerts
    HABIT_STREAK_AT_RISK = "habit_streak_at_risk"
    HABIT_MISSED = "habit_missed"

    # Focus alerts
    FOCUS_STALLED = "focus_stalled"
    FOCUS_NO_PROGRESS = "focus_no_progress"

    # System alerts
    SYSTEM_SYNC_FAILED = "system_sync_failed"
    SYSTEM_ERROR = "system_error"


@dataclass
class Alert:
    """An alert raised by a checker."""
    id: str
    alert_type: AlertType
    priority: AlertPriority
    title: str
    message: str
    entity_type: Optional[str] = None  # 'commitment', 'task', 'health', etc.
    entity_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'id': self.id,
            'alert_type': self.alert_type.value,
            'priority': self.priority.value,
            'title': self.title,
            'message': self.message,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'created_at': self.created_at,
            'acknowledged': self.acknowledged,
            'acknowledged_at': self.acknowledged_at,
            'metadata': self.metadata,
        }


class AlertChecker(ABC):
    """
    Base class for alert checkers.

    Subclasses implement specific checking logic for different domains.
    """

    def __init__(
        self,
        state_store=None,
        journal: Optional[Journal] = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """
        Initialize the alert checker.

        Args:
            state_store: State store instance (defaults to get_db()).
            journal: Journal instance for logging.
            circuit_breaker: Circuit breaker for resilience.
        """
        self.state = state_store or get_db()
        self.journal = journal or Journal()
        self.circuit_breaker = circuit_breaker

    @property
    @abstractmethod
    def checker_name(self) -> str:
        """Name of this checker."""
        pass

    @abstractmethod
    async def check(self) -> List[Alert]:
        """
        Run the alert check and return any alerts.

        Returns:
            List of Alert objects.
        """
        pass

    def _generate_alert_id(self, alert_type: AlertType, entity_id: Optional[str] = None) -> str:
        """Generate a unique alert ID."""
        import uuid
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        suffix = uuid.uuid4().hex[:6]
        if entity_id:
            return f"alert_{alert_type.value}_{entity_id}_{suffix}"
        return f"alert_{alert_type.value}_{timestamp}_{suffix}"

    def _log_alert(self, alert: Alert) -> None:
        """Log alert to journal."""
        severity_map = {
            AlertPriority.LOW: 'info',
            AlertPriority.MEDIUM: 'warning',
            AlertPriority.HIGH: 'warning',
            AlertPriority.CRITICAL: 'error',
        }

        self.journal.log(
            event_type=EventType.ALERT_RAISED,
            title=alert.title,
            data=alert.to_dict(),
            severity=severity_map.get(alert.priority, 'info'),
            source=self.checker_name
        )


class CommitmentAlertChecker(AlertChecker):
    """
    Checks for commitment-related alerts.

    - Overdue commitments
    - Commitments due within 48 hours
    """

    @property
    def checker_name(self) -> str:
        return "commitment_checker"

    async def check(self) -> List[Alert]:
        """Check for commitment alerts."""
        alerts = []
        today = date.today()

        try:
            # Get active commitments from state store
            commitments = self.state.get_active_commitments()

            for commitment in commitments:
                due_date_str = commitment.get('due_date')
                if not due_date_str:
                    continue

                try:
                    due_date = date.fromisoformat(due_date_str[:10])
                except (ValueError, TypeError):
                    continue

                days_until_due = (due_date - today).days
                commit_id = commitment.get('id')
                title = commitment.get('title', 'Unknown commitment')
                person = commitment.get('person', 'Unknown')

                if days_until_due < 0:
                    # Overdue
                    days_overdue = abs(days_until_due)
                    priority = AlertPriority.CRITICAL if days_overdue > 7 else AlertPriority.HIGH

                    alert = Alert(
                        id=self._generate_alert_id(AlertType.COMMITMENT_OVERDUE, commit_id),
                        alert_type=AlertType.COMMITMENT_OVERDUE,
                        priority=priority,
                        title=f"Commitment overdue: {title}",
                        message=f"Commitment to {person} is {days_overdue} day(s) overdue.",
                        entity_type='commitment',
                        entity_id=commit_id,
                        metadata={
                            'days_overdue': days_overdue,
                            'person': person,
                            'due_date': due_date_str,
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)

                elif days_until_due <= 2:
                    # Due soon (within 48 hours)
                    alert = Alert(
                        id=self._generate_alert_id(AlertType.COMMITMENT_DUE_SOON, commit_id),
                        alert_type=AlertType.COMMITMENT_DUE_SOON,
                        priority=AlertPriority.MEDIUM,
                        title=f"Commitment due soon: {title}",
                        message=f"Commitment to {person} is due in {days_until_due} day(s).",
                        entity_type='commitment',
                        entity_id=commit_id,
                        metadata={
                            'days_until_due': days_until_due,
                            'person': person,
                            'due_date': due_date_str,
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)

        except Exception as e:
            logger.error(f"Commitment check failed: {e}")

        return alerts


class TaskAlertChecker(AlertChecker):
    """
    Checks for task-related alerts.

    - Overdue tasks
    - Tasks due today
    """

    @property
    def checker_name(self) -> str:
        return "task_checker"

    async def check(self) -> List[Alert]:
        """Check for task alerts."""
        alerts = []
        today = date.today()

        try:
            # Get tasks from state store
            # Only check tasks that are not completed
            all_tasks = self.state.execute_sql("""
                SELECT * FROM tasks
                WHERE status NOT IN ('done', 'completed', 'cancelled')
                AND due_date IS NOT NULL
            """)

            for task in all_tasks:
                due_date_str = task.get('due_date')
                if not due_date_str:
                    continue

                try:
                    due_date = date.fromisoformat(due_date_str[:10])
                except (ValueError, TypeError):
                    continue

                days_until_due = (due_date - today).days
                task_id = task.get('id')
                title = task.get('title', 'Unknown task')
                domain = task.get('domain', 'personal')

                if days_until_due < 0:
                    # Overdue
                    days_overdue = abs(days_until_due)
                    priority = AlertPriority.HIGH if days_overdue > 3 else AlertPriority.MEDIUM

                    alert = Alert(
                        id=self._generate_alert_id(AlertType.TASK_OVERDUE, task_id),
                        alert_type=AlertType.TASK_OVERDUE,
                        priority=priority,
                        title=f"Task overdue: {title}",
                        message=f"Task is {days_overdue} day(s) overdue.",
                        entity_type='task',
                        entity_id=task_id,
                        metadata={
                            'days_overdue': days_overdue,
                            'domain': domain,
                            'due_date': due_date_str,
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)

                elif days_until_due == 0:
                    # Due today
                    alert = Alert(
                        id=self._generate_alert_id(AlertType.TASK_DUE_TODAY, task_id),
                        alert_type=AlertType.TASK_DUE_TODAY,
                        priority=AlertPriority.MEDIUM,
                        title=f"Task due today: {title}",
                        message=f"Task is due today.",
                        entity_type='task',
                        entity_id=task_id,
                        metadata={
                            'domain': domain,
                            'due_date': due_date_str,
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)

        except Exception as e:
            logger.error(f"Task check failed: {e}")

        return alerts


class OuraAlertChecker(AlertChecker):
    """
    Checks for health metric alerts from Oura data.

    - Low sleep score
    - Low readiness score
    - High stress
    - Low HRV trend
    """

    # Thresholds
    SLEEP_LOW_THRESHOLD = 70
    READINESS_LOW_THRESHOLD = 65
    STRESS_HIGH_THRESHOLD = 80  # Higher is more stressed
    HRV_LOW_THRESHOLD = 30  # ms

    @property
    def checker_name(self) -> str:
        return "oura_checker"

    async def check(self) -> List[Alert]:
        """Check for health metric alerts."""
        alerts = []
        today = date.today()
        yesterday = today - timedelta(days=1)

        try:
            # Get recent health metrics
            metrics = self.state.get_health_metrics(
                start_date=yesterday,
                end_date=today
            )

            # Group by metric type
            by_type: Dict[str, List[Dict]] = {}
            for m in metrics:
                mt = m.get('metric_type', 'unknown')
                if mt not in by_type:
                    by_type[mt] = []
                by_type[mt].append(m)

            # Check sleep score
            sleep_metrics = by_type.get('sleep', []) + by_type.get('daily_sleep', [])
            for m in sleep_metrics:
                score = m.get('score')
                if score and score < self.SLEEP_LOW_THRESHOLD:
                    alert = Alert(
                        id=self._generate_alert_id(AlertType.HEALTH_LOW_SLEEP),
                        alert_type=AlertType.HEALTH_LOW_SLEEP,
                        priority=AlertPriority.MEDIUM,
                        title=f"Low sleep score: {score}",
                        message=f"Sleep score of {score} is below threshold of {self.SLEEP_LOW_THRESHOLD}. Consider lighter cognitive load today.",
                        entity_type='health',
                        metadata={
                            'score': score,
                            'threshold': self.SLEEP_LOW_THRESHOLD,
                            'date': m.get('date'),
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)
                    break  # Only one sleep alert per check

            # Check readiness score
            readiness_metrics = by_type.get('readiness', []) + by_type.get('daily_readiness', [])
            for m in readiness_metrics:
                score = m.get('score')
                if score and score < self.READINESS_LOW_THRESHOLD:
                    alert = Alert(
                        id=self._generate_alert_id(AlertType.HEALTH_LOW_READINESS),
                        alert_type=AlertType.HEALTH_LOW_READINESS,
                        priority=AlertPriority.MEDIUM,
                        title=f"Low readiness score: {score}",
                        message=f"Readiness score of {score} suggests taking it easy today.",
                        entity_type='health',
                        metadata={
                            'score': score,
                            'threshold': self.READINESS_LOW_THRESHOLD,
                            'date': m.get('date'),
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)
                    break

            # Check stress (if available)
            stress_metrics = by_type.get('stress', []) + by_type.get('daily_stress', [])
            for m in stress_metrics:
                score = m.get('score') or m.get('value')
                if score and score > self.STRESS_HIGH_THRESHOLD:
                    alert = Alert(
                        id=self._generate_alert_id(AlertType.HEALTH_HIGH_STRESS),
                        alert_type=AlertType.HEALTH_HIGH_STRESS,
                        priority=AlertPriority.HIGH,
                        title=f"High stress detected: {score}",
                        message="High stress levels detected. Consider a break or stress-reduction activity.",
                        entity_type='health',
                        metadata={
                            'score': score,
                            'threshold': self.STRESS_HIGH_THRESHOLD,
                            'date': m.get('date'),
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)
                    break

        except Exception as e:
            logger.error(f"Oura check failed: {e}")

        return alerts


class HabitAlertChecker(AlertChecker):
    """
    Checks for habit-related alerts.

    - Streaks at risk (not completed today for daily habits)
    - Missed habits
    """

    @property
    def checker_name(self) -> str:
        return "habit_checker"

    async def check(self) -> List[Alert]:
        """Check for habit alerts."""
        alerts = []
        today = date.today()
        yesterday = today - timedelta(days=1)

        try:
            # Check if habits table exists
            habits = self.state.execute_sql("""
                SELECT h.*,
                       (SELECT MAX(completed_at) FROM habit_completions
                        WHERE habit_id = h.id) as last_completed
                FROM habits h
                WHERE h.is_active = 1 OR h.is_active IS NULL
            """)

            for habit in habits:
                habit_id = habit.get('id')
                name = habit.get('name', 'Unknown habit')
                frequency = habit.get('frequency', 'daily')
                current_streak = habit.get('current_streak', 0)
                last_completed = habit.get('last_completed')

                # Only check daily habits for now
                if frequency != 'daily':
                    continue

                # Check if completed today
                if last_completed:
                    try:
                        last_date = date.fromisoformat(last_completed[:10])
                        days_since = (today - last_date).days
                    except (ValueError, TypeError):
                        days_since = 999
                else:
                    days_since = 999

                if days_since >= 1 and current_streak >= 3:
                    # Streak at risk
                    alert = Alert(
                        id=self._generate_alert_id(AlertType.HABIT_STREAK_AT_RISK, habit_id),
                        alert_type=AlertType.HABIT_STREAK_AT_RISK,
                        priority=AlertPriority.MEDIUM if current_streak < 7 else AlertPriority.HIGH,
                        title=f"Habit streak at risk: {name}",
                        message=f"{current_streak}-day streak for '{name}' is at risk! Complete today to maintain it.",
                        entity_type='habit',
                        entity_id=habit_id,
                        metadata={
                            'current_streak': current_streak,
                            'days_since_completed': days_since,
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)

                elif days_since >= 2:
                    # Habit missed (streak already broken)
                    alert = Alert(
                        id=self._generate_alert_id(AlertType.HABIT_MISSED, habit_id),
                        alert_type=AlertType.HABIT_MISSED,
                        priority=AlertPriority.LOW,
                        title=f"Habit missed: {name}",
                        message=f"'{name}' hasn't been completed in {days_since} days.",
                        entity_type='habit',
                        entity_id=habit_id,
                        metadata={
                            'days_since_completed': days_since,
                        }
                    )
                    alerts.append(alert)
                    self._log_alert(alert)

        except Exception as e:
            logger.error(f"Habit check failed: {e}")

        return alerts


class AlertManager:
    """
    Manages all alert checkers and aggregates results.
    """

    def __init__(
        self,
        state_store=None,
        journal: Optional[Journal] = None
    ):
        """
        Initialize the alert manager.

        Args:
            state_store: State store instance.
            journal: Journal instance.
        """
        self.state = state_store or get_db()
        self.journal = journal or Journal()

        # Initialize all checkers
        self.checkers: List[AlertChecker] = [
            CommitmentAlertChecker(state_store=self.state, journal=self.journal),
            TaskAlertChecker(state_store=self.state, journal=self.journal),
            OuraAlertChecker(state_store=self.state, journal=self.journal),
            HabitAlertChecker(state_store=self.state, journal=self.journal),
        ]

    async def check_all(self) -> List[Alert]:
        """
        Run all alert checkers.

        Returns:
            Combined list of alerts from all checkers.
        """
        all_alerts: List[Alert] = []

        for checker in self.checkers:
            try:
                alerts = await checker.check()
                all_alerts.extend(alerts)
                logger.info(f"{checker.checker_name}: {len(alerts)} alert(s)")
            except Exception as e:
                logger.error(f"Checker {checker.checker_name} failed: {e}")

        # Sort by priority (critical first)
        priority_order = {
            AlertPriority.CRITICAL: 0,
            AlertPriority.HIGH: 1,
            AlertPriority.MEDIUM: 2,
            AlertPriority.LOW: 3,
        }
        all_alerts.sort(key=lambda a: priority_order.get(a.priority, 99))

        # Log summary
        self.journal.log(
            event_type=EventType.ALERT_CHECK_COMPLETE,
            title=f"Alert check complete: {len(all_alerts)} alert(s)",
            data={
                'total_alerts': len(all_alerts),
                'by_priority': {
                    p.value: len([a for a in all_alerts if a.priority == p])
                    for p in AlertPriority
                }
            },
            severity='info',
            source='alert_manager'
        )

        return all_alerts

    def get_active_alerts(self, limit: int = 20) -> List[Dict]:
        """
        Get active (unacknowledged) alerts from journal.

        Args:
            limit: Maximum number of alerts to return.

        Returns:
            List of alert dictionaries.
        """
        return self.journal.get_alerts(
            acknowledged=False,
            limit=limit
        )

    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: ID of the alert to acknowledge.

        Returns:
            True if acknowledged, False otherwise.
        """
        return self.journal.acknowledge_alert(alert_id)


# Convenience functions
async def run_alert_check() -> List[Alert]:
    """Run all alert checks and return results."""
    manager = AlertManager()
    return await manager.check_all()


def get_active_alerts(limit: int = 20) -> List[Dict]:
    """Get active alerts."""
    manager = AlertManager()
    return manager.get_active_alerts(limit)


# CLI interface
if __name__ == '__main__':
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description='Thanos Alert Checker')
    parser.add_argument('--check', action='store_true', help='Run alert check')
    parser.add_argument('--list', action='store_true', help='List active alerts')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.check:
        alerts = asyncio.run(run_alert_check())
        print(f"\n=== {len(alerts)} Alert(s) ===\n")
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

    elif args.list:
        alerts = get_active_alerts()
        if args.json:
            import json
            print(json.dumps(alerts, indent=2))
        else:
            print(f"\n=== {len(alerts)} Active Alert(s) ===\n")
            for alert in alerts:
                print(f"• {alert.get('title', 'Unknown')}")
                print(f"  {alert.get('message', '')}")
                print()

    else:
        parser.print_help()
