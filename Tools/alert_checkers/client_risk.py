#!/usr/bin/env python3
"""
Client Risk Alert Checker for Thanos.

Monitors client risk levels from WorkOS and alerts when high-risk
clients are being neglected. Integrates with the Thanos vigilance system.

Alert levels:
- CRITICAL: Risk level 'critical' with no active tasks
- HIGH: Risk level 'high' with high avoidance score (>5)
- MEDIUM: Risk level 'elevated' with work debt
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncio

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.alert_checker import (
    AlertChecker,
    Alert,
    AlertPriority,
    AlertType,
)
from Tools.journal import Journal, EventType

logger = logging.getLogger('client_risk_checker')


# Define new alert types for client risk
class ClientRiskAlertType:
    """Client risk alert types (extend AlertType)."""
    CLIENT_CRITICAL_NEGLECTED = "client_critical_neglected"
    CLIENT_HIGH_RISK_STALE = "client_high_risk_stale"
    CLIENT_ELEVATED_NO_PROGRESS = "client_elevated_no_progress"
    CLIENT_AVOIDANCE_DETECTED = "client_avoidance_detected"


class ClientRiskAlertChecker(AlertChecker):
    """
    Checks for client risk-related alerts.

    Queries WorkOS database for:
    - Clients with critical/high/elevated risk levels
    - Active task counts per client
    - Avoidance patterns (high avoidance score, no recent activity)

    Generates alerts when:
    - Critical risk clients have no active work
    - High risk clients have been stale for >3 days
    - Elevated risk clients show avoidance patterns
    """

    # Thresholds
    STALE_DAYS_THRESHOLD = 3  # Days without activity to consider stale
    HIGH_AVOIDANCE_THRESHOLD = 5  # Avoidance score considered high
    CRITICAL_AVOIDANCE_THRESHOLD = 7  # Avoidance score considered critical

    def __init__(
        self,
        state_store=None,
        journal: Optional[Journal] = None,
        neon_url: Optional[str] = None
    ):
        """
        Initialize the client risk checker.

        Args:
            state_store: State store instance (not used for this checker).
            journal: Journal instance for logging.
            neon_url: Neon database URL. Defaults to WORKOS_DATABASE_URL env var.
        """
        # Don't call super().__init__() since we don't use state_store
        self.journal = journal or Journal()
        self.neon_url = neon_url or os.getenv('WORKOS_DATABASE_URL')

        if not self.neon_url:
            logger.warning("WORKOS_DATABASE_URL not set - client risk checker disabled")

    @property
    def checker_name(self) -> str:
        return "client_risk_checker"

    async def check(self) -> List[Alert]:
        """Check for client risk alerts."""
        alerts = []

        if not self.neon_url:
            return alerts

        try:
            # Query Neon for client risk data
            risk_data = await self._get_client_risk_data()

            for client in risk_data:
                client_alerts = self._evaluate_client_risk(client)
                alerts.extend(client_alerts)

        except Exception as e:
            logger.error(f"Client risk check failed: {e}")
            # Create system alert for the failure
            alerts.append(Alert(
                id=self._generate_alert_id(AlertType.SYSTEM_ERROR),
                alert_type=AlertType.SYSTEM_ERROR,
                priority=AlertPriority.LOW,
                title="Client risk checker failed",
                message=f"Could not check client risk levels: {str(e)[:100]}",
                entity_type='system',
                metadata={'error': str(e)}
            ))

        return alerts

    async def _get_client_risk_data(self) -> List[Dict[str, Any]]:
        """
        Query Neon for client risk data.

        Returns client_memory records with risk_level != 'normal',
        along with counts of active/recent tasks.
        """
        try:
            import httpx
            from urllib.parse import urlparse

            # Parse connection string
            parsed = urlparse(self.neon_url)

            # Use psycopg2 or neon serverless
            # For simplicity, use a subprocess to run a quick query
            import subprocess
            import json

            query = """
            SELECT
                cm.client_name,
                cm.risk_level,
                cm.work_debt,
                cm.importance,
                cm.avoidance_score,
                cm.notes,
                cm.stale_days,
                cm.last_task_at,
                c.id as client_id,
                (SELECT COUNT(*) FROM tasks t
                 WHERE t.client_id = c.id
                 AND t.status = 'active') as active_task_count,
                (SELECT COUNT(*) FROM tasks t
                 WHERE t.client_id = c.id
                 AND t.status IN ('active', 'queued')) as pending_task_count,
                (SELECT MAX(completed_at) FROM tasks t
                 WHERE t.client_id = c.id
                 AND t.status = 'done') as last_completed_at
            FROM client_memory cm
            LEFT JOIN clients c ON LOWER(c.name) = LOWER(cm.client_name)
            WHERE cm.risk_level IN ('critical', 'high', 'elevated')
            ORDER BY
                CASE cm.risk_level
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'elevated' THEN 3
                END,
                cm.avoidance_score DESC
            """

            # Run query using bun and neon serverless
            script = f"""
            import {{ neon }} from "@neondatabase/serverless";
            const sql = neon(process.env.WORKOS_DATABASE_URL);
            const result = await sql`{query}`;
            console.log(JSON.stringify(result));
            """

            result = subprocess.run(
                ['bun', '-e', script],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ}
            )

            if result.returncode != 0:
                logger.error(f"Query failed: {result.stderr}")
                return []

            return json.loads(result.stdout)

        except Exception as e:
            logger.error(f"Failed to query client risk data: {e}")
            return []

    def _evaluate_client_risk(self, client: Dict[str, Any]) -> List[Alert]:
        """
        Evaluate a single client's risk and generate appropriate alerts.

        Args:
            client: Client risk data from database query.

        Returns:
            List of alerts for this client.
        """
        alerts = []
        client_name = client.get('client_name', 'Unknown')
        risk_level = client.get('risk_level', 'normal')
        work_debt = client.get('work_debt')
        avoidance_score = client.get('avoidance_score', 0) or 0
        active_tasks = client.get('active_task_count', 0) or 0
        pending_tasks = client.get('pending_task_count', 0) or 0
        notes = client.get('notes', '')

        # Critical risk with no active work
        if risk_level == 'critical' and active_tasks == 0:
            alert = Alert(
                id=self._generate_alert_id(AlertType.TASK_BLOCKED, f"client_{client_name}"),
                alert_type=AlertType.TASK_BLOCKED,
                priority=AlertPriority.CRITICAL,
                title=f"🚨 CRITICAL: {client_name} needs immediate attention",
                message=f"Client has critical risk level but no active tasks. Work debt: {work_debt or 'None specified'}",
                entity_type='client',
                entity_id=client_name,
                metadata={
                    'risk_level': risk_level,
                    'work_debt': work_debt,
                    'avoidance_score': avoidance_score,
                    'active_tasks': active_tasks,
                    'pending_tasks': pending_tasks,
                    'notes': notes,
                }
            )
            alerts.append(alert)
            self._log_alert(alert)

        # High risk with high avoidance
        elif risk_level == 'high' and avoidance_score >= self.HIGH_AVOIDANCE_THRESHOLD:
            priority = AlertPriority.HIGH if avoidance_score >= self.CRITICAL_AVOIDANCE_THRESHOLD else AlertPriority.MEDIUM

            alert = Alert(
                id=self._generate_alert_id(AlertType.TASK_BLOCKED, f"avoidance_{client_name}"),
                alert_type=AlertType.TASK_BLOCKED,
                priority=priority,
                title=f"⚠️ HIGH RISK: {client_name} showing avoidance pattern",
                message=f"High risk client with avoidance score {avoidance_score}. Work debt: {work_debt or 'None specified'}",
                entity_type='client',
                entity_id=client_name,
                metadata={
                    'risk_level': risk_level,
                    'work_debt': work_debt,
                    'avoidance_score': avoidance_score,
                    'active_tasks': active_tasks,
                    'pending_tasks': pending_tasks,
                }
            )
            alerts.append(alert)
            self._log_alert(alert)

        # High risk with no pending work
        elif risk_level == 'high' and pending_tasks == 0:
            alert = Alert(
                id=self._generate_alert_id(AlertType.TASK_BLOCKED, f"high_{client_name}"),
                alert_type=AlertType.TASK_BLOCKED,
                priority=AlertPriority.HIGH,
                title=f"⚠️ HIGH RISK: {client_name} has no pending work",
                message=f"High risk client with no active or queued tasks. Consider creating tasks to address work debt.",
                entity_type='client',
                entity_id=client_name,
                metadata={
                    'risk_level': risk_level,
                    'work_debt': work_debt,
                    'avoidance_score': avoidance_score,
                }
            )
            alerts.append(alert)
            self._log_alert(alert)

        # Elevated risk with work debt but no active work
        elif risk_level == 'elevated' and work_debt and active_tasks == 0:
            alert = Alert(
                id=self._generate_alert_id(AlertType.FOCUS_NO_PROGRESS, f"elevated_{client_name}"),
                alert_type=AlertType.FOCUS_NO_PROGRESS,
                priority=AlertPriority.MEDIUM,
                title=f"📢 ELEVATED: {client_name} work debt unaddressed",
                message=f"Client has documented work debt but no active tasks: {work_debt[:100] if work_debt else 'None'}",
                entity_type='client',
                entity_id=client_name,
                metadata={
                    'risk_level': risk_level,
                    'work_debt': work_debt,
                    'pending_tasks': pending_tasks,
                }
            )
            alerts.append(alert)
            self._log_alert(alert)

        return alerts

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

    def _generate_alert_id(self, alert_type: AlertType, entity_id: Optional[str] = None) -> str:
        """Generate a unique alert ID."""
        import uuid
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        suffix = uuid.uuid4().hex[:6]
        type_str = alert_type.value if hasattr(alert_type, 'value') else str(alert_type)
        if entity_id:
            return f"alert_{type_str}_{entity_id}_{suffix}"
        return f"alert_{type_str}_{timestamp}_{suffix}"


# CLI for testing
if __name__ == '__main__':
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def main():
        checker = ClientRiskAlertChecker()
        print(f"Running {checker.checker_name}...")
        alerts = await checker.check()

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

    asyncio.run(main())
