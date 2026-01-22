#!/usr/bin/env python3
"""
Task Monitor - Thanos Operator Daemon

Monitors WorkOS tasks for deadlines, overdue items, and milestone tracking.

Architecture:
    - Queries WorkOS MCP server for active tasks
    - Checks deadlines and commitment tracking
    - Graceful error handling (returns empty alert list on failure)

Alert Triggers:
    - Overdue tasks: High priority
    - Due today: Medium priority (morning/afternoon)
    - Due tomorrow: Low priority (evening reminder)
    - Milestone overdue: Critical priority
    - Task pile-up (10+ active): Medium priority

Integration:
    - Uses WorkOS MCP server (mcp-servers/workos-mcp)
    - Database: PostgreSQL via Supabase
    - Fallback: Local cache if MCP unavailable
"""

import asyncio
import logging
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Import circuit breaker for MCP resilience
from Tools.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Alert data structure for Operator daemon."""
    type: str  # 'health', 'task', 'pattern'
    severity: str  # 'info', 'warning', 'critical'
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: str
    dedup_key: Optional[str] = None
    priority: Optional[str] = None  # For alerter routing

    def __post_init__(self):
        """Map severity to priority for backward compatibility."""
        if not self.priority:
            self.priority = self.severity


class TaskMonitor:
    """
    Monitor WorkOS tasks for deadlines and commitments.

    Data Flow:
        1. Query WorkOS MCP for active tasks
        2. Check deadlines (overdue, today, tomorrow)
        3. Check for milestone violations
        4. Check for task pile-up (too many active)
        5. Generate prioritized alerts

    Thresholds:
        - Overdue: High priority
        - Due today: Medium priority
        - Due tomorrow: Low priority
        - Milestone overdue: Critical priority
        - Task pile-up: 10+ active tasks
    """

    def __init__(
        self,
        circuit: CircuitBreaker,
        mcp_server_path: Optional[Path] = None,
        thresholds: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Task Monitor.

        Args:
            circuit: Circuit breaker for MCP protection
            mcp_server_path: Path to WorkOS MCP server (for direct calls)
            thresholds: Custom thresholds (overrides defaults)
        """
        self.circuit = circuit

        # MCP server path (fallback for direct calls)
        if mcp_server_path is None:
            thanos_root = Path(__file__).parent.parent.parent
            mcp_server_path = thanos_root / "mcp-servers" / "workos-mcp"
        self.mcp_server_path = mcp_server_path

        # Default thresholds
        self.thresholds = {
            'task_pileup_threshold': 10,  # Number of active tasks
            'deadline_warning_hours': 24,  # Hours before deadline
        }

        if thresholds:
            self.thresholds.update(thresholds)

        logger.info(
            f"TaskMonitor initialized: mcp_path={self.mcp_server_path}, "
            f"thresholds={self.thresholds}"
        )

    async def check(self) -> List[Alert]:
        """
        Run task checks and generate alerts.

        Returns:
            List of Alert objects (empty on errors - graceful degradation)
        """
        try:
            logger.debug("Running task checks")

            # Get active tasks from WorkOS
            tasks = await self._get_active_tasks()

            if tasks is None:
                logger.warning("Could not fetch tasks - skipping task checks")
                return []

            alerts = []

            # Check for overdue tasks
            overdue_alerts = self._check_overdue_tasks(tasks)
            alerts.extend(overdue_alerts)

            # Check for tasks due today
            due_today_alerts = self._check_due_today(tasks)
            alerts.extend(due_today_alerts)

            # Check for tasks due tomorrow (evening reminder)
            due_tomorrow_alerts = self._check_due_tomorrow(tasks)
            alerts.extend(due_tomorrow_alerts)

            # Check for milestone violations
            milestone_alerts = self._check_milestone_violations(tasks)
            alerts.extend(milestone_alerts)

            # Check for task pile-up
            pileup_alert = self._check_task_pileup(tasks)
            if pileup_alert:
                alerts.append(pileup_alert)

            # Check daily progress/pace (if during work hours)
            progress_alert = await self._check_daily_progress()
            if progress_alert:
                alerts.append(progress_alert)

            logger.info(f"Task checks complete: {len(alerts)} alerts generated")
            return alerts

        except Exception as e:
            logger.error(f"Task monitor check failed: {e}", exc_info=True)
            return []  # Graceful degradation

    async def _get_active_tasks(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get active tasks from WorkOS MCP server.

        Uses circuit breaker for resilient MCP calls. Falls back to
        cached data if MCP unavailable.

        Returns:
            List of task dictionaries or None on complete failure
        """
        try:
            # Import MCP client (lazy import to avoid circular dependencies)
            from Operator.mcp_client import OperatorMCPClient

            # Create and connect MCP client
            mcp_client = OperatorMCPClient(self.circuit)

            try:
                tasks = await mcp_client.get_active_tasks()
                return tasks if tasks else []
            finally:
                await mcp_client.close()

        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}")
            return None

    def _check_overdue_tasks(self, tasks: List[Dict[str, Any]]) -> List[Alert]:
        """
        Check for overdue tasks and generate alerts.

        Args:
            tasks: List of task dictionaries from WorkOS

        Returns:
            List of Alert objects for overdue tasks
        """
        alerts = []
        now = datetime.now()
        overdue_tasks = []

        for task in tasks:
            # Skip tasks without deadlines
            deadline = task.get('deadline')
            if not deadline:
                continue

            # Parse deadline
            try:
                deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                if deadline_dt < now:
                    overdue_tasks.append(task)
            except (ValueError, AttributeError):
                logger.warning(f"Could not parse deadline for task {task.get('id')}: {deadline}")

        if overdue_tasks:
            # Group by client if available
            task_titles = [t.get('title', 'Untitled') for t in overdue_tasks]

            alert = Alert(
                type='task',
                severity='high',
                title=f'{len(overdue_tasks)} Overdue Tasks',
                message=(
                    f"You have {len(overdue_tasks)} overdue task(s): "
                    f"{', '.join(task_titles[:3])}"
                    f"{' and more...' if len(overdue_tasks) > 3 else ''}"
                ),
                data={
                    'count': len(overdue_tasks),
                    'tasks': overdue_tasks,
                    'metric': 'overdue'
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"task:overdue:{datetime.now().strftime('%Y-%m-%d')}"
            )
            alerts.append(alert)

        return alerts

    def _check_due_today(self, tasks: List[Dict[str, Any]]) -> List[Alert]:
        """
        Check for tasks due today.

        Args:
            tasks: List of task dictionaries from WorkOS

        Returns:
            List of Alert objects for tasks due today
        """
        alerts = []
        today = datetime.now().date()
        due_today_tasks = []

        for task in tasks:
            deadline = task.get('deadline')
            if not deadline:
                continue

            try:
                deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                if deadline_dt.date() == today:
                    due_today_tasks.append(task)
            except (ValueError, AttributeError):
                pass

        if due_today_tasks:
            task_titles = [t.get('title', 'Untitled') for t in due_today_tasks]

            # Only alert during working hours (9am, 2pm)
            current_hour = datetime.now().hour
            if current_hour in [9, 14]:
                alert = Alert(
                    type='task',
                    severity='medium',
                    title=f'{len(due_today_tasks)} Tasks Due Today',
                    message=(
                        f"Due today: {', '.join(task_titles[:3])}"
                        f"{' and more...' if len(due_today_tasks) > 3 else ''}"
                    ),
                    data={
                        'count': len(due_today_tasks),
                        'tasks': due_today_tasks,
                        'metric': 'due_today'
                    },
                    timestamp=datetime.now().isoformat(),
                    dedup_key=f"task:due_today:{today.isoformat()}:{current_hour}"
                )
                alerts.append(alert)

        return alerts

    def _check_due_tomorrow(self, tasks: List[Dict[str, Any]]) -> List[Alert]:
        """
        Check for tasks due tomorrow (evening reminder).

        Args:
            tasks: List of task dictionaries from WorkOS

        Returns:
            List of Alert objects for tasks due tomorrow
        """
        alerts = []
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        due_tomorrow_tasks = []

        for task in tasks:
            deadline = task.get('deadline')
            if not deadline:
                continue

            try:
                deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                if deadline_dt.date() == tomorrow:
                    due_tomorrow_tasks.append(task)
            except (ValueError, AttributeError):
                pass

        if due_tomorrow_tasks:
            task_titles = [t.get('title', 'Untitled') for t in due_tomorrow_tasks]

            # Only alert in evening (6pm)
            current_hour = datetime.now().hour
            if current_hour == 18:
                alert = Alert(
                    type='task',
                    severity='low',
                    title=f'{len(due_tomorrow_tasks)} Tasks Due Tomorrow',
                    message=(
                        f"Due tomorrow: {', '.join(task_titles[:3])}"
                        f"{' and more...' if len(due_tomorrow_tasks) > 3 else ''}"
                    ),
                    data={
                        'count': len(due_tomorrow_tasks),
                        'tasks': due_tomorrow_tasks,
                        'metric': 'due_tomorrow'
                    },
                    timestamp=datetime.now().isoformat(),
                    dedup_key=f"task:due_tomorrow:{tomorrow.isoformat()}"
                )
                alerts.append(alert)

        return alerts

    def _check_milestone_violations(self, tasks: List[Dict[str, Any]]) -> List[Alert]:
        """
        Check for overdue milestones (critical priority).

        Milestones are tasks with valueTier = "milestone" that are past due.

        Args:
            tasks: List of task dictionaries from WorkOS

        Returns:
            List of Alert objects for milestone violations
        """
        alerts = []
        now = datetime.now()
        overdue_milestones = []

        for task in tasks:
            # Check if milestone
            if task.get('valueTier') != 'milestone':
                continue

            # Check if overdue
            deadline = task.get('deadline')
            if not deadline:
                continue

            try:
                deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                if deadline_dt < now:
                    overdue_milestones.append(task)
            except (ValueError, AttributeError):
                pass

        if overdue_milestones:
            for milestone in overdue_milestones:
                alert = Alert(
                    type='task',
                    severity='critical',
                    title='Milestone Overdue',
                    message=(
                        f"Critical: Milestone '{milestone.get('title', 'Untitled')}' "
                        f"is overdue. This was a committed deliverable."
                    ),
                    data={
                        'task': milestone,
                        'metric': 'milestone_violation'
                    },
                    timestamp=datetime.now().isoformat(),
                    dedup_key=f"task:milestone:{milestone.get('id')}"
                )
                alerts.append(alert)

        return alerts

    def _check_task_pileup(self, tasks: List[Dict[str, Any]]) -> Optional[Alert]:
        """
        Check for too many active tasks (overcommitment indicator).

        Args:
            tasks: List of task dictionaries from WorkOS

        Returns:
            Alert if task count exceeds threshold, None otherwise
        """
        active_count = len(tasks)
        threshold = self.thresholds['task_pileup_threshold']

        if active_count >= threshold:
            return Alert(
                type='task',
                severity='medium',
                title='Task Pile-Up Detected',
                message=(
                    f"You have {active_count} active tasks (threshold: {threshold}). "
                    f"Consider completing or deferring some tasks."
                ),
                data={
                    'count': active_count,
                    'threshold': threshold,
                    'metric': 'task_pileup'
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"task:pileup:{datetime.now().strftime('%Y-%m-%d')}"
            )

        return None

    async def _check_daily_progress(self) -> Optional[Alert]:
        """
        Check daily progress and pace toward point goal.

        Only alerts during work hours (9am-6pm) if significantly behind pace.
        Alerts at:
        - 12pm if 0 points earned
        - 3pm if < 50% of target
        - 5pm if < 75% of target

        Returns:
            Alert if behind pace during work hours, None otherwise
        """
        try:
            now = datetime.now()
            hour = now.hour

            # Only check during work hours
            if hour < 9 or hour > 18:
                return None

            # Get today's metrics
            from Operator.mcp_client import OperatorMCPClient
            mcp_client = OperatorMCPClient(self.circuit)

            try:
                metrics = await mcp_client.get_today_metrics()
            finally:
                await mcp_client.close()

            if not metrics:
                logger.debug("No metrics available for progress check")
                return None

            earned = metrics.get('earnedPoints', 0)
            target = metrics.get('targetPoints', 18)
            percent = metrics.get('percentOfTarget', 0)
            pace_status = metrics.get('paceStatus', 'unknown')

            # Alert thresholds based on time of day
            should_alert = False
            severity = 'low'
            message_suffix = ""

            if hour >= 17 and percent < 75:  # 5pm: < 75%
                should_alert = True
                severity = 'high'
                message_suffix = "End of day approaching. Push for completion."
            elif hour >= 15 and percent < 50:  # 3pm: < 50%
                should_alert = True
                severity = 'medium'
                message_suffix = "Afternoon checkpoint: significantly behind."
            elif hour >= 12 and earned == 0:  # 12pm: 0 points
                should_alert = True
                severity = 'medium'
                message_suffix = "Midday checkpoint: no progress yet."

            if should_alert:
                return Alert(
                    type='task',
                    severity=severity,
                    title='Behind Daily Goal',
                    message=(
                        f"Progress: {earned}/{target} points ({percent}%). "
                        f"Status: {pace_status}. {message_suffix}"
                    ),
                    data={
                        'earned_points': earned,
                        'target_points': target,
                        'percent': percent,
                        'pace_status': pace_status,
                        'hour': hour,
                        'metric': 'daily_progress'
                    },
                    timestamp=now.isoformat(),
                    dedup_key=f"task:progress:{now.strftime('%Y-%m-%d-%H')}"
                )

            return None

        except Exception as e:
            logger.error(f"Failed to check daily progress: {e}", exc_info=True)
            return None
