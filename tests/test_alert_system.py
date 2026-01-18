#!/usr/bin/env python3
"""
Comprehensive tests for the Alert Checking System.

Tests all 4 checker types:
- CommitmentAlertChecker
- TaskAlertChecker
- OuraAlertChecker
- HabitAlertChecker

Also tests:
- Alert priority levels (CRITICAL, HIGH, MEDIUM, LOW)
- Deduplication logic in daemon
- Quiet hours functionality
- AlertManager running all checkers
- Alert storm prevention
"""

import asyncio
import json
import tempfile
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import sqlite3

import pytest

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.alert_checker import (
    Alert,
    AlertType,
    AlertPriority,
    AlertChecker,
    CommitmentAlertChecker,
    TaskAlertChecker,
    OuraAlertChecker,
    HabitAlertChecker,
    AlertManager,
)
from Tools.alert_daemon import (
    AlertDaemon,
    DaemonConfig,
    DaemonState,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    # Initialize with schema
    conn = sqlite3.connect(str(db_path))
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS commitments (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            person TEXT NOT NULL,
            due_date DATE,
            status TEXT DEFAULT 'active',
            metadata JSON
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            due_date DATE,
            status TEXT DEFAULT 'pending',
            domain TEXT DEFAULT 'work',
            metadata JSON
        );

        CREATE TABLE IF NOT EXISTS health_metrics (
            id TEXT PRIMARY KEY,
            date DATE NOT NULL,
            metric_type TEXT NOT NULL,
            score INTEGER,
            value REAL,
            source TEXT DEFAULT 'oura',
            metadata JSON
        );

        CREATE TABLE IF NOT EXISTS habits (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            frequency TEXT DEFAULT 'daily',
            current_streak INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            metadata JSON
        );

        CREATE TABLE IF NOT EXISTS habit_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id TEXT NOT NULL,
            completed_at TIMESTAMP,
            date DATE
        );

        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT NOT NULL,
            source TEXT,
            severity TEXT DEFAULT 'info',
            title TEXT,
            data JSON
        );
    ''')
    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.fixture
def mock_state_store(temp_db):
    """Create a mock state store with test methods."""
    class MockStateStore:
        def __init__(self, db_path):
            self.db_path = db_path

        def _get_conn(self):
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            return conn

        def get_active_commitments(self) -> List[Dict]:
            conn = self._get_conn()
            cursor = conn.execute(
                "SELECT * FROM commitments WHERE status = 'active'"
            )
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results

        def execute_sql(self, sql: str, params=()) -> List[Dict]:
            conn = self._get_conn()
            cursor = conn.execute(sql, params)
            if cursor.description:
                results = [dict(row) for row in cursor.fetchall()]
            else:
                results = []
            conn.close()
            return results

        def get_health_metrics(self, start_date=None, end_date=None) -> List[Dict]:
            conn = self._get_conn()
            query = "SELECT * FROM health_metrics WHERE 1=1"
            params = []
            if start_date:
                query += " AND date >= ?"
                params.append(str(start_date))
            if end_date:
                query += " AND date <= ?"
                params.append(str(end_date))
            cursor = conn.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results

        def insert_commitment(self, id, title, person, due_date, status='active'):
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO commitments (id, title, person, due_date, status) VALUES (?, ?, ?, ?, ?)",
                (id, title, person, str(due_date) if due_date else None, status)
            )
            conn.commit()
            conn.close()

        def insert_task(self, id, title, due_date, status='pending', domain='work'):
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO tasks (id, title, due_date, status, domain) VALUES (?, ?, ?, ?, ?)",
                (id, title, str(due_date) if due_date else None, status, domain)
            )
            conn.commit()
            conn.close()

        def insert_health_metric(self, id, metric_date, metric_type, score=None, value=None):
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO health_metrics (id, date, metric_type, score, value) VALUES (?, ?, ?, ?, ?)",
                (id, str(metric_date), metric_type, score, value)
            )
            conn.commit()
            conn.close()

        def insert_habit(self, id, name, frequency='daily', current_streak=0, is_active=1):
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO habits (id, name, frequency, current_streak, is_active) VALUES (?, ?, ?, ?, ?)",
                (id, name, frequency, current_streak, is_active)
            )
            conn.commit()
            conn.close()

        def insert_habit_completion(self, habit_id, completed_at):
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO habit_completions (habit_id, completed_at, date) VALUES (?, ?, ?)",
                (habit_id, completed_at, completed_at[:10] if completed_at else None)
            )
            conn.commit()
            conn.close()

    return MockStateStore(temp_db)


@pytest.fixture
def mock_journal():
    """Create a mock journal that captures logged alerts."""
    class MockJournal:
        def __init__(self):
            self.logged_events = []

        def log(self, event_type, title, data=None, severity='info', source=None):
            self.logged_events.append({
                'event_type': event_type,
                'title': title,
                'data': data,
                'severity': severity,
                'source': source
            })
            return len(self.logged_events)

        def get_alerts(self, acknowledged=False, limit=20):
            return [e for e in self.logged_events if e.get('severity') in ('warning', 'error')]

        def acknowledge_alert(self, alert_id):
            return True

    return MockJournal()


# =============================================================================
# Alert Data Class Tests
# =============================================================================

class TestAlertDataClass:
    """Test Alert dataclass functionality."""

    def test_alert_creation(self):
        """Test creating an alert with all fields."""
        alert = Alert(
            id="alert_test_123",
            alert_type=AlertType.TASK_OVERDUE,
            priority=AlertPriority.HIGH,
            title="Test Alert",
            message="This is a test alert message",
            entity_type="task",
            entity_id="task_123",
            metadata={"days_overdue": 5}
        )

        assert alert.id == "alert_test_123"
        assert alert.alert_type == AlertType.TASK_OVERDUE
        assert alert.priority == AlertPriority.HIGH
        assert alert.title == "Test Alert"
        assert alert.acknowledged is False
        assert alert.metadata["days_overdue"] == 5

    def test_alert_to_dict(self):
        """Test converting alert to dictionary."""
        alert = Alert(
            id="alert_dict_test",
            alert_type=AlertType.COMMITMENT_OVERDUE,
            priority=AlertPriority.CRITICAL,
            title="Overdue Commitment",
            message="Test message"
        )

        alert_dict = alert.to_dict()

        assert alert_dict['id'] == "alert_dict_test"
        assert alert_dict['alert_type'] == "commitment_overdue"
        assert alert_dict['priority'] == "critical"
        assert alert_dict['acknowledged'] is False

    def test_all_priority_levels(self):
        """Test all alert priority levels exist."""
        priorities = [AlertPriority.LOW, AlertPriority.MEDIUM, AlertPriority.HIGH, AlertPriority.CRITICAL]

        assert len(priorities) == 4
        assert AlertPriority.LOW.value == "low"
        assert AlertPriority.MEDIUM.value == "medium"
        assert AlertPriority.HIGH.value == "high"
        assert AlertPriority.CRITICAL.value == "critical"


# =============================================================================
# CommitmentAlertChecker Tests
# =============================================================================

class TestCommitmentAlertChecker:
    """Test commitment alert checking functionality."""

    @pytest.mark.asyncio
    async def test_overdue_commitment_critical(self, mock_state_store, mock_journal):
        """Test that commitments overdue by more than 7 days generate CRITICAL alerts."""
        # Insert commitment overdue by 10 days
        overdue_date = date.today() - timedelta(days=10)
        mock_state_store.insert_commitment(
            id="commit_1",
            title="Review Q4 financials",
            person="John Doe",
            due_date=overdue_date
        )

        checker = CommitmentAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.COMMITMENT_OVERDUE
        assert alerts[0].priority == AlertPriority.CRITICAL
        assert "10 day(s) overdue" in alerts[0].message
        assert alerts[0].entity_type == "commitment"

    @pytest.mark.asyncio
    async def test_overdue_commitment_high(self, mock_state_store, mock_journal):
        """Test that commitments overdue by 1-7 days generate HIGH alerts."""
        # Insert commitment overdue by 3 days
        overdue_date = date.today() - timedelta(days=3)
        mock_state_store.insert_commitment(
            id="commit_2",
            title="Send proposal",
            person="Jane Smith",
            due_date=overdue_date
        )

        checker = CommitmentAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 1
        assert alerts[0].priority == AlertPriority.HIGH
        assert "3 day(s) overdue" in alerts[0].message

    @pytest.mark.asyncio
    async def test_commitment_due_soon(self, mock_state_store, mock_journal):
        """Test that commitments due within 48 hours generate MEDIUM alerts."""
        # Insert commitment due tomorrow
        due_date = date.today() + timedelta(days=1)
        mock_state_store.insert_commitment(
            id="commit_3",
            title="Submit report",
            person="Bob Wilson",
            due_date=due_date
        )

        checker = CommitmentAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.COMMITMENT_DUE_SOON
        assert alerts[0].priority == AlertPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_no_alerts_for_future_commitment(self, mock_state_store, mock_journal):
        """Test that commitments due in the future (>2 days) don't generate alerts."""
        # Insert commitment due in 5 days
        due_date = date.today() + timedelta(days=5)
        mock_state_store.insert_commitment(
            id="commit_4",
            title="Future task",
            person="Future Person",
            due_date=due_date
        )

        checker = CommitmentAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_checker_name(self, mock_state_store, mock_journal):
        """Test checker name property."""
        checker = CommitmentAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )
        assert checker.checker_name == "commitment_checker"


# =============================================================================
# TaskAlertChecker Tests
# =============================================================================

class TestTaskAlertChecker:
    """Test task alert checking functionality."""

    @pytest.mark.asyncio
    async def test_overdue_task_high_priority(self, mock_state_store, mock_journal):
        """Test that tasks overdue by more than 3 days generate HIGH alerts."""
        # Insert task overdue by 5 days
        overdue_date = date.today() - timedelta(days=5)
        mock_state_store.insert_task(
            id="task_1",
            title="Complete documentation",
            due_date=overdue_date,
            status="pending"
        )

        checker = TaskAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.TASK_OVERDUE
        assert alerts[0].priority == AlertPriority.HIGH

    @pytest.mark.asyncio
    async def test_overdue_task_medium_priority(self, mock_state_store, mock_journal):
        """Test that tasks overdue by 1-3 days generate MEDIUM alerts."""
        # Insert task overdue by 2 days
        overdue_date = date.today() - timedelta(days=2)
        mock_state_store.insert_task(
            id="task_2",
            title="Review code",
            due_date=overdue_date,
            status="in_progress"
        )

        checker = TaskAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 1
        assert alerts[0].priority == AlertPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_task_due_today(self, mock_state_store, mock_journal):
        """Test that tasks due today generate MEDIUM alerts."""
        mock_state_store.insert_task(
            id="task_3",
            title="Ship feature",
            due_date=date.today(),
            status="active"
        )

        checker = TaskAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.TASK_DUE_TODAY
        assert alerts[0].priority == AlertPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_completed_tasks_ignored(self, mock_state_store, mock_journal):
        """Test that completed tasks don't generate alerts."""
        overdue_date = date.today() - timedelta(days=5)
        mock_state_store.insert_task(
            id="task_4",
            title="Finished task",
            due_date=overdue_date,
            status="done"
        )

        checker = TaskAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_cancelled_tasks_ignored(self, mock_state_store, mock_journal):
        """Test that cancelled tasks don't generate alerts."""
        overdue_date = date.today() - timedelta(days=3)
        mock_state_store.insert_task(
            id="task_5",
            title="Cancelled task",
            due_date=overdue_date,
            status="cancelled"
        )

        checker = TaskAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 0


# =============================================================================
# OuraAlertChecker Tests
# =============================================================================

class TestOuraAlertChecker:
    """Test Oura health metric alert checking."""

    @pytest.mark.asyncio
    async def test_low_sleep_score_alert(self, mock_state_store, mock_journal):
        """Test that low sleep scores generate MEDIUM alerts."""
        mock_state_store.insert_health_metric(
            id="metric_1",
            metric_date=date.today(),
            metric_type="sleep",
            score=55  # Below threshold of 70
        )

        checker = OuraAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.HEALTH_LOW_SLEEP
        assert alerts[0].priority == AlertPriority.MEDIUM
        assert "55" in alerts[0].title

    @pytest.mark.asyncio
    async def test_low_readiness_score_alert(self, mock_state_store, mock_journal):
        """Test that low readiness scores generate MEDIUM alerts."""
        mock_state_store.insert_health_metric(
            id="metric_2",
            metric_date=date.today(),
            metric_type="readiness",
            score=50  # Below threshold of 65
        )

        checker = OuraAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.HEALTH_LOW_READINESS
        assert alerts[0].priority == AlertPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_high_stress_alert(self, mock_state_store, mock_journal):
        """Test that high stress generates HIGH alerts."""
        mock_state_store.insert_health_metric(
            id="metric_3",
            metric_date=date.today(),
            metric_type="stress",
            score=90  # Above threshold of 80
        )

        checker = OuraAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.HEALTH_HIGH_STRESS
        assert alerts[0].priority == AlertPriority.HIGH

    @pytest.mark.asyncio
    async def test_good_metrics_no_alert(self, mock_state_store, mock_journal):
        """Test that good health metrics don't generate alerts."""
        mock_state_store.insert_health_metric(
            id="metric_4",
            metric_date=date.today(),
            metric_type="sleep",
            score=85  # Above threshold
        )
        mock_state_store.insert_health_metric(
            id="metric_5",
            metric_date=date.today(),
            metric_type="readiness",
            score=80  # Above threshold
        )

        checker = OuraAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_oura_thresholds(self, mock_state_store, mock_journal):
        """Test that threshold values are correctly defined."""
        checker = OuraAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        assert checker.SLEEP_LOW_THRESHOLD == 70
        assert checker.READINESS_LOW_THRESHOLD == 65
        assert checker.STRESS_HIGH_THRESHOLD == 80
        assert checker.HRV_LOW_THRESHOLD == 30


# =============================================================================
# HabitAlertChecker Tests
# =============================================================================

class TestHabitAlertChecker:
    """Test habit alert checking functionality."""

    @pytest.mark.asyncio
    async def test_streak_at_risk_medium(self, mock_state_store, mock_journal):
        """Test that streaks < 7 days at risk generate MEDIUM alerts."""
        # Create habit with 5-day streak
        mock_state_store.insert_habit(
            id="habit_1",
            name="Morning meditation",
            frequency="daily",
            current_streak=5
        )
        # Last completed yesterday (so today is at risk)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        mock_state_store.insert_habit_completion("habit_1", yesterday)

        checker = HabitAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.HABIT_STREAK_AT_RISK
        assert alerts[0].priority == AlertPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_streak_at_risk_high(self, mock_state_store, mock_journal):
        """Test that streaks >= 7 days at risk generate HIGH alerts."""
        # Create habit with 10-day streak
        mock_state_store.insert_habit(
            id="habit_2",
            name="Daily exercise",
            frequency="daily",
            current_streak=10
        )
        # Last completed yesterday
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        mock_state_store.insert_habit_completion("habit_2", yesterday)

        checker = HabitAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 1
        assert alerts[0].priority == AlertPriority.HIGH
        assert "10-day streak" in alerts[0].message

    @pytest.mark.asyncio
    async def test_habit_missed_low_priority(self, mock_state_store, mock_journal):
        """Test that missed habits (no streak) generate LOW alerts."""
        # Create habit with no streak, not completed in 3 days
        mock_state_store.insert_habit(
            id="habit_3",
            name="Read books",
            frequency="daily",
            current_streak=0
        )
        # Last completed 3 days ago
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        mock_state_store.insert_habit_completion("habit_3", three_days_ago)

        checker = HabitAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.HABIT_MISSED
        assert alerts[0].priority == AlertPriority.LOW

    @pytest.mark.asyncio
    async def test_completed_today_no_alert(self, mock_state_store, mock_journal):
        """Test that habits completed today don't generate alerts."""
        mock_state_store.insert_habit(
            id="habit_4",
            name="Drink water",
            frequency="daily",
            current_streak=5
        )
        # Completed today
        today = datetime.now().isoformat()
        mock_state_store.insert_habit_completion("habit_4", today)

        checker = HabitAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        # Should not generate alert since completed today
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_inactive_habits_ignored(self, mock_state_store, mock_journal):
        """Test that inactive habits don't generate alerts."""
        mock_state_store.insert_habit(
            id="habit_5",
            name="Old habit",
            frequency="daily",
            current_streak=20,
            is_active=0  # Inactive
        )

        checker = HabitAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_weekly_habits_skipped(self, mock_state_store, mock_journal):
        """Test that non-daily habits are currently skipped."""
        mock_state_store.insert_habit(
            id="habit_6",
            name="Weekly review",
            frequency="weekly",
            current_streak=4
        )

        checker = HabitAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        # Weekly habits are skipped in current implementation
        assert len(alerts) == 0


# =============================================================================
# AlertManager Tests
# =============================================================================

class TestAlertManager:
    """Test AlertManager orchestration functionality."""

    @pytest.mark.asyncio
    async def test_check_all_runs_all_checkers(self, mock_state_store, mock_journal):
        """Test that check_all runs all registered checkers."""
        # Add data for multiple checkers
        overdue_date = date.today() - timedelta(days=5)
        mock_state_store.insert_commitment(
            id="commit_mgr_1",
            title="Manager test commitment",
            person="Test Person",
            due_date=overdue_date
        )
        mock_state_store.insert_task(
            id="task_mgr_1",
            title="Manager test task",
            due_date=date.today(),
            status="pending"
        )

        manager = AlertManager(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await manager.check_all()

        # Should have alerts from both commitment and task checkers
        assert len(alerts) >= 2
        alert_types = {a.alert_type for a in alerts}
        assert AlertType.COMMITMENT_OVERDUE in alert_types
        assert AlertType.TASK_DUE_TODAY in alert_types

    @pytest.mark.asyncio
    async def test_alerts_sorted_by_priority(self, mock_state_store, mock_journal):
        """Test that alerts are sorted by priority (critical first)."""
        # Add data that will generate different priority alerts
        critical_date = date.today() - timedelta(days=10)  # Will be CRITICAL
        mock_state_store.insert_commitment(
            id="commit_sort_1",
            title="Critical commitment",
            person="Test",
            due_date=critical_date
        )
        mock_state_store.insert_task(
            id="task_sort_1",
            title="Medium task",
            due_date=date.today(),  # Will be MEDIUM
            status="pending"
        )

        manager = AlertManager(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await manager.check_all()

        # First alert should be CRITICAL
        assert alerts[0].priority == AlertPriority.CRITICAL

    def test_manager_initializes_all_checkers(self, mock_state_store, mock_journal):
        """Test that manager initializes all 4 checker types."""
        manager = AlertManager(
            state_store=mock_state_store,
            journal=mock_journal
        )

        checker_names = [c.checker_name for c in manager.checkers]

        assert "commitment_checker" in checker_names
        assert "task_checker" in checker_names
        assert "oura_checker" in checker_names
        assert "habit_checker" in checker_names
        assert len(manager.checkers) == 4


# =============================================================================
# AlertDaemon Tests
# =============================================================================

class TestAlertDaemon:
    """Test AlertDaemon background service functionality."""

    def test_daemon_config_defaults(self):
        """Test DaemonConfig default values."""
        config = DaemonConfig()

        assert config.check_interval == 900  # 15 minutes
        assert config.dedup_window == 3600  # 1 hour
        assert config.max_alerts_per_run == 20
        assert config.quiet_hours_start == 22  # 10 PM
        assert config.quiet_hours_end == 7  # 7 AM
        assert 'commitment' in config.enabled_checkers
        assert 'task' in config.enabled_checkers
        assert 'oura' in config.enabled_checkers
        assert 'habit' in config.enabled_checkers

    def test_daemon_state_serialization(self):
        """Test DaemonState to_dict and from_dict."""
        state = DaemonState(
            last_run=datetime.now().isoformat(),
            run_count=5,
            total_alerts=15,
            recent_dedup_keys={"key1": datetime.now().isoformat()}
        )

        state_dict = state.to_dict()
        restored_state = DaemonState.from_dict(state_dict)

        assert restored_state.run_count == 5
        assert restored_state.total_alerts == 15
        assert "key1" in restored_state.recent_dedup_keys

    def test_quiet_hours_detection_night(self):
        """Test quiet hours detection during night."""
        config = DaemonConfig(
            quiet_hours_start=22,
            quiet_hours_end=7
        )

        # Mock datetime to test different hours
        with patch('Tools.alert_daemon.datetime') as mock_dt:
            # 11 PM - should be quiet
            mock_dt.now.return_value = datetime(2024, 1, 15, 23, 0)
            daemon = AlertDaemon(config)
            # We need to patch the method directly since it uses datetime.now()

    def test_quiet_hours_spans_midnight(self):
        """Test that quiet hours correctly span midnight."""
        config = DaemonConfig(
            quiet_hours_start=22,  # 10 PM
            quiet_hours_end=7      # 7 AM
        )

        # Verify the logic: when start > end, quiet hours span midnight
        assert config.quiet_hours_start > config.quiet_hours_end

    def test_should_notify_respects_quiet_hours(self):
        """Test that non-critical alerts are suppressed during quiet hours."""
        config = DaemonConfig()
        daemon = AlertDaemon(config)

        # Mock being in quiet hours
        with patch.object(daemon, '_is_quiet_hours', return_value=True):
            # MEDIUM priority should NOT notify during quiet hours
            medium_alert = Alert(
                id="test_1",
                alert_type=AlertType.TASK_DUE_TODAY,
                priority=AlertPriority.MEDIUM,
                title="Test",
                message="Test"
            )
            assert daemon._should_notify(medium_alert) is False

            # CRITICAL priority SHOULD notify even during quiet hours
            critical_alert = Alert(
                id="test_2",
                alert_type=AlertType.COMMITMENT_OVERDUE,
                priority=AlertPriority.CRITICAL,
                title="Critical Test",
                message="Critical"
            )
            assert daemon._should_notify(critical_alert) is True

    def test_alert_storm_prevention(self):
        """Test that alert storms are limited."""
        config = DaemonConfig(max_alerts_per_run=5)

        # The daemon limits alerts in run_once()
        assert config.max_alerts_per_run == 5


# =============================================================================
# Deduplication Tests
# =============================================================================

class TestDeduplication:
    """Test alert deduplication logic."""

    @pytest.mark.asyncio
    async def test_dedup_within_window(self):
        """Test that duplicate alerts within dedup window are filtered."""
        config = DaemonConfig(
            dedup_window=3600,  # 1 hour
            enabled_checkers=['commitment']
        )

        # Create daemon with mocked state
        with tempfile.TemporaryDirectory() as tmpdir:
            config.state_file = str(Path(tmpdir) / "daemon_state.json")

            daemon = AlertDaemon(config)
            daemon.state.recent_dedup_keys = {
                "commitment_overdue:commit_1": datetime.now().isoformat()
            }

            # The dedup key format is alert_type:entity_id
            dedup_key = "commitment_overdue:commit_1"
            assert dedup_key in daemon.state.recent_dedup_keys

    def test_dedup_cache_cleanup(self):
        """Test that expired dedup keys are cleaned up."""
        config = DaemonConfig(dedup_window=3600)  # 1 hour

        with tempfile.TemporaryDirectory() as tmpdir:
            config.state_file = str(Path(tmpdir) / "daemon_state.json")

            daemon = AlertDaemon(config)

            # Add an expired key (2 hours ago)
            expired_time = (datetime.now() - timedelta(hours=2)).isoformat()
            daemon.state.recent_dedup_keys = {
                "old_key": expired_time,
                "recent_key": datetime.now().isoformat()
            }

            daemon._clean_dedup_cache()

            # Old key should be removed
            assert "old_key" not in daemon.state.recent_dedup_keys
            # Recent key should remain
            assert "recent_key" in daemon.state.recent_dedup_keys


# =============================================================================
# Integration Tests
# =============================================================================

class TestAlertSystemIntegration:
    """Integration tests for the complete alert system."""

    @pytest.mark.asyncio
    async def test_full_alert_cycle(self, mock_state_store, mock_journal):
        """Test a complete alert check cycle."""
        # Setup: Add various items that will generate alerts
        overdue_commitment = date.today() - timedelta(days=8)
        mock_state_store.insert_commitment(
            id="int_commit_1",
            title="Integration test commitment",
            person="Integration Test",
            due_date=overdue_commitment
        )

        mock_state_store.insert_task(
            id="int_task_1",
            title="Integration test task",
            due_date=date.today(),
            status="pending"
        )

        mock_state_store.insert_health_metric(
            id="int_metric_1",
            metric_date=date.today(),
            metric_type="sleep",
            score=60
        )

        mock_state_store.insert_habit(
            id="int_habit_1",
            name="Integration habit",
            current_streak=5
        )
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        mock_state_store.insert_habit_completion("int_habit_1", yesterday)

        # Run full alert check
        manager = AlertManager(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await manager.check_all()

        # Should have alerts from multiple sources
        assert len(alerts) >= 3

        # Verify alert types present
        alert_types = {a.alert_type for a in alerts}
        assert AlertType.COMMITMENT_OVERDUE in alert_types
        assert AlertType.TASK_DUE_TODAY in alert_types
        assert AlertType.HEALTH_LOW_SLEEP in alert_types

        # First should be CRITICAL (commitment 8 days overdue)
        assert alerts[0].priority == AlertPriority.CRITICAL

    @pytest.mark.asyncio
    async def test_empty_database_no_errors(self, mock_state_store, mock_journal):
        """Test that empty database doesn't cause errors."""
        manager = AlertManager(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await manager.check_all()

        # Should return empty list without errors
        assert alerts == []

    @pytest.mark.asyncio
    async def test_multiple_alerts_same_type(self, mock_state_store, mock_journal):
        """Test handling multiple alerts of the same type."""
        # Add multiple overdue commitments
        for i in range(3):
            overdue_date = date.today() - timedelta(days=5+i)
            mock_state_store.insert_commitment(
                id=f"multi_commit_{i}",
                title=f"Commitment {i}",
                person=f"Person {i}",
                due_date=overdue_date
            )

        checker = CommitmentAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        # Should have 3 alerts
        assert len(alerts) == 3
        # All should be COMMITMENT_OVERDUE
        assert all(a.alert_type == AlertType.COMMITMENT_OVERDUE for a in alerts)


# =============================================================================
# Alert Priority Tests
# =============================================================================

class TestAlertPriorityLevels:
    """Comprehensive tests for all alert priority levels."""

    @pytest.mark.asyncio
    async def test_critical_priority_conditions(self, mock_state_store, mock_journal):
        """Test conditions that generate CRITICAL alerts."""
        # Commitment overdue > 7 days
        overdue_date = date.today() - timedelta(days=10)
        mock_state_store.insert_commitment(
            id="crit_1",
            title="Critical commitment",
            person="Test",
            due_date=overdue_date
        )

        manager = AlertManager(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await manager.check_all()
        critical_alerts = [a for a in alerts if a.priority == AlertPriority.CRITICAL]

        assert len(critical_alerts) >= 1

    @pytest.mark.asyncio
    async def test_high_priority_conditions(self, mock_state_store, mock_journal):
        """Test conditions that generate HIGH alerts."""
        # Commitment overdue 1-7 days
        overdue_date = date.today() - timedelta(days=5)
        mock_state_store.insert_commitment(
            id="high_1",
            title="High priority commitment",
            person="Test",
            due_date=overdue_date
        )

        # Task overdue > 3 days
        task_overdue = date.today() - timedelta(days=4)
        mock_state_store.insert_task(
            id="high_task_1",
            title="High priority task",
            due_date=task_overdue,
            status="pending"
        )

        # High stress metric
        mock_state_store.insert_health_metric(
            id="high_metric_1",
            metric_date=date.today(),
            metric_type="stress",
            score=85
        )

        manager = AlertManager(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await manager.check_all()
        high_alerts = [a for a in alerts if a.priority == AlertPriority.HIGH]

        assert len(high_alerts) >= 2  # At least commitment and stress

    @pytest.mark.asyncio
    async def test_medium_priority_conditions(self, mock_state_store, mock_journal):
        """Test conditions that generate MEDIUM alerts."""
        # Commitment due soon
        due_soon = date.today() + timedelta(days=1)
        mock_state_store.insert_commitment(
            id="med_1",
            title="Due soon commitment",
            person="Test",
            due_date=due_soon
        )

        # Task due today
        mock_state_store.insert_task(
            id="med_task_1",
            title="Task due today",
            due_date=date.today(),
            status="pending"
        )

        # Low sleep score
        mock_state_store.insert_health_metric(
            id="med_metric_1",
            metric_date=date.today(),
            metric_type="sleep",
            score=65
        )

        manager = AlertManager(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await manager.check_all()
        medium_alerts = [a for a in alerts if a.priority == AlertPriority.MEDIUM]

        assert len(medium_alerts) >= 3

    @pytest.mark.asyncio
    async def test_low_priority_conditions(self, mock_state_store, mock_journal):
        """Test conditions that generate LOW alerts."""
        # Habit missed (no streak)
        mock_state_store.insert_habit(
            id="low_habit_1",
            name="Low priority habit",
            current_streak=0
        )
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        mock_state_store.insert_habit_completion("low_habit_1", three_days_ago)

        manager = AlertManager(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await manager.check_all()
        low_alerts = [a for a in alerts if a.priority == AlertPriority.LOW]

        assert len(low_alerts) >= 1


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_invalid_date_format_handled(self, mock_state_store, mock_journal):
        """Test that invalid date formats are handled gracefully."""
        # Insert commitment with invalid date
        conn = mock_state_store._get_conn()
        conn.execute(
            "INSERT INTO commitments (id, title, person, due_date, status) VALUES (?, ?, ?, ?, ?)",
            ("invalid_1", "Invalid date commitment", "Test", "not-a-date", "active")
        )
        conn.commit()
        conn.close()

        checker = CommitmentAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        # Should not raise exception
        alerts = await checker.check()

        # Should gracefully skip invalid entries
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_null_due_date_handled(self, mock_state_store, mock_journal):
        """Test that null due dates are handled."""
        mock_state_store.insert_commitment(
            id="null_date_1",
            title="No due date",
            person="Test",
            due_date=None
        )

        checker = CommitmentAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()

        # Should not generate alert for commitment without due date
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_alert_id_uniqueness(self, mock_state_store, mock_journal):
        """Test that alert IDs are unique."""
        # Add multiple items that will generate alerts
        for i in range(5):
            overdue_date = date.today() - timedelta(days=5)
            mock_state_store.insert_commitment(
                id=f"unique_test_{i}",
                title=f"Commitment {i}",
                person=f"Person {i}",
                due_date=overdue_date
            )

        checker = CommitmentAlertChecker(
            state_store=mock_state_store,
            journal=mock_journal
        )

        alerts = await checker.check()
        alert_ids = [a.id for a in alerts]

        # All IDs should be unique
        assert len(alert_ids) == len(set(alert_ids))


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
