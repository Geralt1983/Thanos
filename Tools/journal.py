#!/usr/bin/env python3
"""
Event Journal for Thanos.

Append-only event log capturing all significant actions for observability.
Provides single source of truth for "what happened" across all integrations.

Usage:
    from Tools.journal import Journal, EventType, get_journal

    journal = get_journal()
    journal.log(
        event_type=EventType.TASK_COMPLETED,
        source="workos",
        title="Completed: Review Q4 financials",
        data={"task_id": "abc123", "duration_hours": 2.5}
    )
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import contextmanager


class EventType(Enum):
    """Event types for journal entries."""

    # Tasks
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_CANCELLED = "task_cancelled"
    TASK_OVERDUE = "task_overdue"

    # Calendar
    EVENT_CREATED = "event_created"
    EVENT_UPCOMING = "event_upcoming"
    EVENT_STARTED = "event_started"
    EVENT_MISSED = "event_missed"

    # Health
    HEALTH_METRIC_LOGGED = "health_metric_logged"
    HEALTH_ALERT = "health_alert"
    HEALTH_SUMMARY = "health_summary"

    # Finance
    BALANCE_LOGGED = "balance_logged"
    BALANCE_WARNING = "balance_warning"
    BALANCE_CRITICAL = "balance_critical"
    LARGE_TRANSACTION = "large_transaction"
    PROJECTION_WARNING = "projection_warning"
    RECURRING_UPCOMING = "recurring_upcoming"

    # Brain Dumps
    BRAIN_DUMP_RECEIVED = "brain_dump_received"
    BRAIN_DUMP_PARSED = "brain_dump_parsed"
    BRAIN_DUMP_THINKING = "brain_dump_thinking"
    BRAIN_DUMP_VENTING = "brain_dump_venting"
    BRAIN_DUMP_OBSERVATION = "brain_dump_observation"
    NOTE_CAPTURED = "note_captured"
    IDEA_CAPTURED = "idea_captured"
    IDEA_PROMOTED = "idea_promoted"

    # System
    SYNC_STARTED = "sync_started"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"
    CIRCUIT_OPENED = "circuit_opened"
    CIRCUIT_CLOSED = "circuit_closed"
    CIRCUIT_HALF_OPEN = "circuit_half_open"
    DAEMON_STARTED = "daemon_started"
    DAEMON_STOPPED = "daemon_stopped"
    ERROR_OCCURRED = "error_occurred"

    # Commitments
    COMMITMENT_CREATED = "commitment_created"
    COMMITMENT_COMPLETED = "commitment_completed"
    COMMITMENT_DUE_SOON = "commitment_due_soon"
    COMMITMENT_OVERDUE = "commitment_overdue"

    # Session
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    COMMAND_EXECUTED = "command_executed"

    # Alerts
    ALERT_CREATED = "alert_created"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_RESOLVED = "alert_resolved"
    ALERT_RAISED = "alert_raised"
    ALERT_CHECK_COMPLETE = "alert_check_complete"


class Severity(Enum):
    """Severity levels for journal entries."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"


@dataclass
class JournalEntry:
    """A single journal entry."""
    id: int
    timestamp: str
    event_type: str
    source: str
    severity: str
    title: str
    data: Optional[Dict]
    session_id: Optional[str]
    agent: Optional[str]
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None


class Journal:
    """Append-only event journal for observability."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize journal.

        Args:
            db_path: Path to SQLite database. Defaults to State/thanos.db
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "State" / "thanos.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper handling."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Initialize journal schema."""
        with self._get_connection() as conn:
            conn.executescript('''
                -- Journal table (append-only)
                CREATE TABLE IF NOT EXISTS journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    severity TEXT DEFAULT 'info',
                    title TEXT NOT NULL,
                    data JSON,
                    session_id TEXT,
                    agent TEXT,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    acknowledged_at TIMESTAMP
                );

                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_journal_timestamp ON journal(timestamp);
                CREATE INDEX IF NOT EXISTS idx_journal_event_type ON journal(event_type);
                CREATE INDEX IF NOT EXISTS idx_journal_severity ON journal(severity);
                CREATE INDEX IF NOT EXISTS idx_journal_source ON journal(source);
                CREATE INDEX IF NOT EXISTS idx_journal_acknowledged ON journal(acknowledged);
            ''')

    def log(
        self,
        event_type: EventType,
        source: str,
        title: str,
        content: Optional[str] = None,
        data: Optional[Dict] = None,
        severity: str = "info",
        session_id: Optional[str] = None,
        agent: Optional[str] = None
    ) -> int:
        """Append event to journal.

        Args:
            event_type: Type of event
            source: Source system (workos, oura, monarch, brain_dump, manual, system)
            title: Human-readable summary
            content: Human-readable content body (e.g., brain dump text)
            data: Full event payload (structured metadata)
            severity: debug, info, warning, alert, critical
            session_id: Associated session ID
            agent: Agent that triggered the event

        Returns:
            Event ID
        """
        # Merge content into data if provided
        merged_data = data.copy() if data else {}
        if content:
            merged_data['content'] = content

        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO journal (event_type, source, severity, title, data, session_id, agent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_type.value if isinstance(event_type, EventType) else event_type,
                source,
                severity,
                title,
                json.dumps(merged_data) if merged_data else None,
                session_id,
                agent
            ))
            return cursor.lastrowid

    def query(
        self,
        event_types: Optional[List[EventType]] = None,
        sources: Optional[List[str]] = None,
        severity_min: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[JournalEntry]:
        """Query journal with filters.

        Args:
            event_types: Filter by event types
            sources: Filter by sources
            severity_min: Minimum severity level
            since: Events after this time
            until: Events before this time
            acknowledged: Filter by acknowledgement status
            limit: Maximum results
            offset: Skip first N results

        Returns:
            List of matching journal entries
        """
        conditions = []
        params = []

        if event_types:
            placeholders = ','.join('?' * len(event_types))
            conditions.append(f'event_type IN ({placeholders})')
            params.extend(e.value if isinstance(e, EventType) else e for e in event_types)

        if sources:
            placeholders = ','.join('?' * len(sources))
            conditions.append(f'source IN ({placeholders})')
            params.extend(sources)

        if severity_min:
            severity_order = ['debug', 'info', 'warning', 'alert', 'critical']
            min_index = severity_order.index(severity_min)
            valid_severities = severity_order[min_index:]
            placeholders = ','.join('?' * len(valid_severities))
            conditions.append(f'severity IN ({placeholders})')
            params.extend(valid_severities)

        if since:
            conditions.append('timestamp >= ?')
            params.append(since.isoformat())

        if until:
            conditions.append('timestamp <= ?')
            params.append(until.isoformat())

        if acknowledged is not None:
            conditions.append('acknowledged = ?')
            params.append(acknowledged)

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        with self._get_connection() as conn:
            rows = conn.execute(f'''
                SELECT * FROM journal
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            ''', params + [limit, offset]).fetchall()

            return [self._row_to_entry(row) for row in rows]

    def get_alerts(
        self,
        since: Optional[datetime] = None,
        unacknowledged_only: bool = True,
        limit: int = 50
    ) -> List[JournalEntry]:
        """Get alerts (warning severity and above).

        Args:
            since: Alerts after this time
            unacknowledged_only: Only return unacknowledged alerts
            limit: Maximum number of alerts to return

        Returns:
            List of alert entries
        """
        return self.query(
            severity_min="warning",
            since=since,
            acknowledged=False if unacknowledged_only else None,
            limit=limit
        )

    def get_thinking_entries(
        self,
        since: Optional[datetime] = None
    ) -> List[JournalEntry]:
        """Get brain dump thinking entries for reflection.

        Args:
            since: Entries after this time

        Returns:
            List of thinking-type brain dump entries
        """
        thinking_types = [
            EventType.BRAIN_DUMP_THINKING,
            EventType.BRAIN_DUMP_VENTING,
            EventType.BRAIN_DUMP_OBSERVATION
        ]
        return self.query(
            event_types=thinking_types,
            since=since,
            limit=100
        )

    def get_today(self, source: Optional[str] = None) -> List[JournalEntry]:
        """Get all events from today.

        Args:
            source: Optional source filter

        Returns:
            List of today's entries
        """
        today_start = datetime.combine(date.today(), datetime.min.time())

        return self.query(
            since=today_start,
            sources=[source] if source else None,
            limit=1000
        )

    def get_recent_alerts(self, limit: int = 5) -> List[JournalEntry]:
        """Get recent alerts for display."""
        return self.query(
            severity_min="warning",
            limit=limit
        )

    def count_alerts(self, acknowledged: Optional[bool] = None) -> int:
        """Count alerts by acknowledgement status.

        Args:
            acknowledged: Filter by acknowledgement status.
                          None = count all alerts
                          True = count only acknowledged alerts
                          False = count only unacknowledged alerts

        Returns:
            Number of alerts matching the filter
        """
        with self._get_connection() as conn:
            if acknowledged is None:
                # Count all alerts
                row = conn.execute('''
                    SELECT COUNT(*) FROM journal
                    WHERE severity IN ('warning', 'alert', 'critical')
                ''').fetchone()
            else:
                row = conn.execute('''
                    SELECT COUNT(*) FROM journal
                    WHERE severity IN ('warning', 'alert', 'critical')
                    AND acknowledged = ?
                ''', (acknowledged,)).fetchone()
            return row[0]

    def count_unacknowledged_alerts(self) -> int:
        """Count unacknowledged alerts.

        Deprecated: Use count_alerts(acknowledged=False) instead.
        """
        return self.count_alerts(acknowledged=False)

    def acknowledge_alert(self, entry_id: int) -> bool:
        """Acknowledge an alert.

        Args:
            entry_id: Journal entry ID

        Returns:
            True if acknowledged
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute('''
                UPDATE journal
                SET acknowledged = TRUE, acknowledged_at = ?
                WHERE id = ?
            ''', (now, entry_id))
            return cursor.rowcount > 0

    def acknowledge_all_alerts(self) -> int:
        """Acknowledge all unacknowledged alerts.

        Returns:
            Number of alerts acknowledged
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute('''
                UPDATE journal
                SET acknowledged = TRUE, acknowledged_at = ?
                WHERE severity IN ('warning', 'alert', 'critical')
                AND acknowledged = FALSE
            ''', (now,))
            return cursor.rowcount

    def get_entry(self, entry_id: int) -> Optional[JournalEntry]:
        """Get a specific entry by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM journal WHERE id = ?', (entry_id,)
            ).fetchone()

            if row:
                return self._row_to_entry(row)
        return None

    def get_stats(
        self,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get journal statistics.

        Args:
            since: Calculate stats from this time

        Returns:
            Dictionary of statistics
        """
        if since is None:
            since = datetime.now() - timedelta(hours=24)

        with self._get_connection() as conn:
            # Total events
            total = conn.execute(
                'SELECT COUNT(*) FROM journal WHERE timestamp >= ?',
                (since.isoformat(),)
            ).fetchone()[0]

            # By severity
            severity_rows = conn.execute('''
                SELECT severity, COUNT(*) as count
                FROM journal WHERE timestamp >= ?
                GROUP BY severity
            ''', (since.isoformat(),)).fetchall()
            by_severity = {row['severity']: row['count'] for row in severity_rows}

            # By source
            source_rows = conn.execute('''
                SELECT source, COUNT(*) as count
                FROM journal WHERE timestamp >= ?
                GROUP BY source
            ''', (since.isoformat(),)).fetchall()
            by_source = {row['source']: row['count'] for row in source_rows}

            # By event type
            type_rows = conn.execute('''
                SELECT event_type, COUNT(*) as count
                FROM journal WHERE timestamp >= ?
                GROUP BY event_type
                ORDER BY count DESC
                LIMIT 10
            ''', (since.isoformat(),)).fetchall()
            top_types = {row['event_type']: row['count'] for row in type_rows}

            # Unacknowledged alerts
            unacknowledged = conn.execute('''
                SELECT COUNT(*) FROM journal
                WHERE severity IN ('warning', 'alert', 'critical')
                AND acknowledged = FALSE
            ''').fetchone()[0]

            return {
                'total_events': total,
                'by_severity': by_severity,
                'by_source': by_source,
                'top_event_types': top_types,
                'unacknowledged_alerts': unacknowledged,
                'period_start': since.isoformat()
            }

    def _row_to_entry(self, row: sqlite3.Row) -> JournalEntry:
        """Convert database row to JournalEntry object."""
        return JournalEntry(
            id=row['id'],
            timestamp=row['timestamp'],
            event_type=row['event_type'],
            source=row['source'],
            severity=row['severity'],
            title=row['title'],
            data=json.loads(row['data']) if row['data'] else None,
            session_id=row['session_id'],
            agent=row['agent'],
            acknowledged=bool(row['acknowledged']),
            acknowledged_at=row['acknowledged_at']
        )

    def format_entry(self, entry: JournalEntry) -> str:
        """Format entry for display."""
        severity_icons = {
            'debug': '🔍',
            'info': 'ℹ️',
            'warning': '⚠️',
            'alert': '🔔',
            'critical': '🚨'
        }

        icon = severity_icons.get(entry.severity, '•')
        timestamp = datetime.fromisoformat(entry.timestamp).strftime("%H:%M")

        return f"{icon} [{timestamp}] {entry.title} ({entry.source})"

    def format_today_summary(self) -> str:
        """Format today's events as summary."""
        events = self.get_today()
        stats = self.get_stats(since=datetime.combine(date.today(), datetime.min.time()))

        lines = [
            f"📊 Today's Activity ({stats['total_events']} events)",
            ""
        ]

        # Show alerts first
        alerts = [e for e in events if e.severity in ('warning', 'alert', 'critical')]
        if alerts:
            lines.append("🚨 Alerts:")
            for alert in alerts[:5]:
                lines.append(f"   {self.format_entry(alert)}")
            lines.append("")

        # Show recent activity
        lines.append("📋 Recent Activity:")
        for event in events[:10]:
            if event not in alerts:
                lines.append(f"   {self.format_entry(event)}")

        return "\n".join(lines)


# Singleton instance
_journal: Optional[Journal] = None


def get_journal(db_path: Optional[Path] = None) -> Journal:
    """Get or create singleton Journal instance."""
    global _journal

    if _journal is None or db_path is not None:
        _journal = Journal(db_path)

    return _journal


# Convenience functions for common logging patterns
def log_task_event(
    event_type: EventType,
    task_id: str,
    title: str,
    **kwargs
) -> int:
    """Log a task-related event."""
    journal = get_journal()
    data = {'task_id': task_id, **kwargs}
    return journal.log(
        event_type=event_type,
        source="workos",
        title=title,
        data=data
    )


def log_health_alert(
    title: str,
    metrics: Dict[str, float],
    recommendations: Optional[List[str]] = None
) -> int:
    """Log a health alert."""
    journal = get_journal()
    return journal.log(
        event_type=EventType.HEALTH_ALERT,
        source="oura",
        title=title,
        data={
            'metrics': metrics,
            'recommendations': recommendations or []
        },
        severity="warning"
    )


def log_finance_warning(
    title: str,
    account: str,
    balance: float,
    threshold: float
) -> int:
    """Log a finance warning."""
    journal = get_journal()
    severity = "critical" if balance < threshold * 0.5 else "warning"
    return journal.log(
        event_type=EventType.BALANCE_WARNING,
        source="monarch",
        title=title,
        data={
            'account': account,
            'balance': balance,
            'threshold': threshold
        },
        severity=severity
    )


def log_sync_event(
    source: str,
    success: bool,
    message: str,
    details: Optional[Dict] = None
) -> int:
    """Log a sync event."""
    journal = get_journal()
    event_type = EventType.SYNC_COMPLETED if success else EventType.SYNC_FAILED
    severity = "info" if success else "warning"

    return journal.log(
        event_type=event_type,
        source=source,
        title=message,
        data=details,
        severity=severity
    )


def log_circuit_event(
    source: str,
    state: str,
    reason: Optional[str] = None
) -> int:
    """Log a circuit breaker state change."""
    journal = get_journal()

    event_types = {
        'open': EventType.CIRCUIT_OPENED,
        'closed': EventType.CIRCUIT_CLOSED,
        'half_open': EventType.CIRCUIT_HALF_OPEN
    }

    severity = "warning" if state == 'open' else "info"

    return journal.log(
        event_type=event_types.get(state, EventType.CIRCUIT_OPENED),
        source=source,
        title=f"Circuit {state}: {source}",
        data={'reason': reason} if reason else None,
        severity=severity
    )


if __name__ == "__main__":
    # Test the journal
    journal = get_journal()

    print("Journal Test")
    print("=" * 60)

    # Log some test events
    event_id = journal.log(
        event_type=EventType.TASK_COMPLETED,
        source="workos",
        title="Test task completed",
        data={"task_id": "test123", "duration": 30}
    )
    print(f"Logged event: {event_id}")

    # Log an alert
    alert_id = journal.log(
        event_type=EventType.HEALTH_ALERT,
        source="oura",
        title="Low sleep score: 62",
        data={"sleep_score": 62},
        severity="warning"
    )
    print(f"Logged alert: {alert_id}")

    # Query today's events
    events = journal.get_today()
    print(f"\nToday's events: {len(events)}")

    # Get stats
    stats = journal.get_stats()
    print(f"\nStats: {stats}")

    # Format summary
    print("\n" + journal.format_today_summary())
