#!/usr/bin/env python3
"""
WorkOS Alert Checker for Thanos.

Monitors task status, streaks, and productivity metrics.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base import AlertChecker, ThresholdChecker, Alert

import sys
sys.path.insert(0, str(__file__).rsplit('/Tools', 1)[0])

from Tools.journal import EventType


class WorkOSChecker(ThresholdChecker):
    """Check WorkOS for task and productivity alerts."""

    source = "workos"
    check_interval = 900  # 15 minutes

    def __init__(self, workos_client=None):
        """
        Initialize WorkOS checker.

        Args:
            workos_client: Optional WorkOS MCP client. If None, uses default.
        """
        super().__init__()
        self.workos_client = workos_client

    async def check(self) -> List[Alert]:
        """
        Run WorkOS checks and return alerts.

        Checks:
        - Overdue tasks
        - Tasks due today with no progress
        - Streak at risk
        - Low points pace
        - High-priority tasks pending
        """
        alerts = []

        try:
            # Get today's metrics
            metrics = await self._get_today_metrics()
            if metrics:
                alerts.extend(self._check_metrics(metrics))

            # Get active tasks
            tasks = await self._get_active_tasks()
            if tasks:
                alerts.extend(self._check_tasks(tasks))

            # Get streak info
            streak = await self._get_streak()
            if streak:
                alerts.extend(self._check_streak(streak))

        except Exception as e:
            # Return error as alert (base class handles this too)
            alerts.append(Alert(
                type=EventType.SYNC_FAILED,
                severity="warning",
                title=f"WorkOS check error: {str(e)[:50]}",
                data={'error': str(e), 'checker': self.source}
            ))

        return alerts

    async def _get_today_metrics(self) -> Optional[Dict[str, Any]]:
        """Get today's work metrics from WorkOS."""
        # This would call the WorkOS MCP tool
        # For now, return None to indicate no data
        # Real implementation would use:
        # return await self.workos_client.get_today_metrics()
        return None

    async def _get_active_tasks(self) -> Optional[List[Dict[str, Any]]]:
        """Get active tasks from WorkOS."""
        # Real implementation would use WorkOS MCP
        return None

    async def _get_streak(self) -> Optional[Dict[str, Any]]:
        """Get streak information from WorkOS."""
        # Real implementation would use WorkOS MCP
        return None

    def _check_metrics(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check today's metrics for alert conditions."""
        alerts = []

        # Check points pace
        points_earned = metrics.get('points_earned', 0)
        target_points = metrics.get('target_points', 18)
        hours_elapsed = datetime.now().hour + (datetime.now().minute / 60)

        if hours_elapsed >= 10:  # After 10am
            expected_pace = (hours_elapsed - 8) / 10 * target_points  # 8am-6pm workday
            if points_earned < expected_pace * 0.5:
                alerts.append(Alert(
                    type=EventType.HEALTH_ALERT,
                    severity="warning",
                    title=f"Behind on points: {points_earned}/{target_points} ({int(points_earned/target_points*100)}%)",
                    data={
                        'points_earned': points_earned,
                        'target': target_points,
                        'expected': expected_pace,
                        'metric': 'points_pace'
                    },
                    dedup_key="workos:points_pace:behind"
                ))

        # Check if no clients touched today
        clients_touched = metrics.get('clients_touched', 0)
        if hours_elapsed >= 12 and clients_touched == 0:
            alerts.append(Alert(
                type=EventType.HEALTH_ALERT,
                severity="info",
                title="No client work logged today",
                data={'clients_touched': 0, 'hour': int(hours_elapsed)},
                dedup_key="workos:no_clients"
            ))

        return alerts

    def _check_tasks(self, tasks: List[Dict[str, Any]]) -> List[Alert]:
        """Check tasks for alert conditions."""
        alerts = []
        now = datetime.now()

        overdue_count = 0
        high_priority_pending = 0

        for task in tasks:
            status = task.get('status', '')
            due_date_str = task.get('due_date')
            priority = task.get('priority', 'medium')
            value_tier = task.get('value_tier', 'checkbox')

            # Check for overdue
            if due_date_str:
                try:
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                    if due_date < now and status != 'done':
                        overdue_count += 1
                except (ValueError, TypeError):
                    pass

            # Count high-priority pending
            if status == 'active' and (priority == 'high' or value_tier in ['deliverable', 'milestone']):
                high_priority_pending += 1

        # Alert for overdue tasks
        if overdue_count > 0:
            severity = "critical" if overdue_count >= 3 else "warning"
            alerts.append(Alert(
                type=EventType.DEADLINE_APPROACHING,
                severity=severity,
                title=f"{overdue_count} overdue task(s)",
                data={'overdue_count': overdue_count},
                dedup_key=f"workos:overdue:{overdue_count}"
            ))

        # Alert for high-priority backlog
        if high_priority_pending > 5:
            alerts.append(Alert(
                type=EventType.HEALTH_ALERT,
                severity="info",
                title=f"{high_priority_pending} high-priority tasks pending",
                data={'high_priority_count': high_priority_pending},
                dedup_key="workos:high_priority_backlog"
            ))

        return alerts

    def _check_streak(self, streak: Dict[str, Any]) -> List[Alert]:
        """Check streak status for alerts."""
        alerts = []

        current_streak = streak.get('current_streak', 0)
        goal_met_today = streak.get('goal_met_today', False)
        hours_remaining = 24 - datetime.now().hour

        # Streak at risk (after 6pm, goal not met, has existing streak)
        if current_streak >= 3 and not goal_met_today and hours_remaining < 6:
            alerts.append(Alert(
                type=EventType.HEALTH_ALERT,
                severity="warning",
                title=f"Streak at risk! {current_streak}-day streak, {hours_remaining}h remaining",
                data={
                    'current_streak': current_streak,
                    'hours_remaining': hours_remaining,
                    'goal_met': goal_met_today
                },
                dedup_key="workos:streak_at_risk"
            ))

        # Celebrate milestone streaks
        if goal_met_today and current_streak in [7, 14, 30, 50, 100]:
            alerts.append(Alert(
                type=EventType.GOAL_MET,
                severity="info",
                title=f"🎉 {current_streak}-day streak milestone!",
                data={'milestone': current_streak},
                dedup_key=f"workos:streak_milestone:{current_streak}"
            ))

        return alerts
