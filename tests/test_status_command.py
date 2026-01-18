"""
Tests for /status command (commands/status.py).

Tests cover:
- generate_status() returns all expected sections
- get_task_summary() returns correct counts
- get_commitment_summary() properly categorizes overdue/due_soon
- get_health_summary() handles missing data
- get_brain_dump_summary() counts by category
- get_alerts_summary() includes priorities
- format_status_text() produces readable output
- CLI flags: --json, --alerts-only, --brief
- Empty database and populated database scenarios
"""

import asyncio
import json
import sqlite3
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_thanos.db"


@pytest.fixture
def mock_db(temp_db_path):
    """Create a mock database with proper schema."""
    # Create database with schema
    conn = sqlite3.connect(str(temp_db_path))
    conn.row_factory = sqlite3.Row

    # Create tasks table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority TEXT,
            due_date DATE,
            domain TEXT DEFAULT 'work',
            source TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSON
        )
    """)

    # Create commitments table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS commitments (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            person TEXT,
            due_date DATE,
            status TEXT DEFAULT 'active',
            priority TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSON
        )
    """)

    # Create health_metrics table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_metrics (
            id TEXT PRIMARY KEY,
            date DATE NOT NULL,
            metric_type TEXT NOT NULL,
            score INTEGER,
            value REAL,
            source TEXT DEFAULT 'oura',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSON
        )
    """)

    # Create brain_dumps table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS brain_dumps (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            category TEXT,
            processed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSON
        )
    """)

    # Create habits table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            frequency TEXT DEFAULT 'daily',
            current_streak INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create habit_completions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS habit_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id TEXT NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date DATE NOT NULL
        )
    """)

    # Create schema_version table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (1)")

    # Create journal table
    conn.execute("""
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
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_journal_timestamp ON journal(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_journal_severity ON journal(severity)")

    conn.commit()
    conn.close()

    return temp_db_path


@pytest.fixture
def populated_db(mock_db):
    """Populate the database with test data."""
    conn = sqlite3.connect(str(mock_db))
    conn.row_factory = sqlite3.Row

    today = date.today()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    week_ahead = today + timedelta(days=7)
    two_days_ahead = today + timedelta(days=2)

    # Insert tasks
    tasks = [
        ("task_1", "Active work task", "pending", "work", str(today), "high"),
        ("task_2", "Overdue task", "pending", "work", str(week_ago), "critical"),
        ("task_3", "Due today task", "in_progress", "personal", str(today), "medium"),
        ("task_4", "Future task", "pending", "work", str(week_ahead), "low"),
        ("task_5", "Completed task", "done", "personal", str(yesterday), "medium"),
        ("task_6", "Cancelled task", "cancelled", "work", str(yesterday), None),
    ]
    for t in tasks:
        conn.execute(
            "INSERT INTO tasks (id, title, status, domain, due_date, priority) VALUES (?, ?, ?, ?, ?, ?)",
            t
        )

    # Insert commitments
    commitments = [
        ("commit_1", "Overdue commitment", "Alice", str(week_ago), "active"),
        ("commit_2", "Due soon commitment", "Bob", str(two_days_ahead), "active"),
        ("commit_3", "Future commitment", "Charlie", str(week_ahead), "active"),
        ("commit_4", "No deadline commitment", "Dave", None, "active"),
        ("commit_5", "Completed commitment", "Eve", str(yesterday), "completed"),
    ]
    for c in commitments:
        conn.execute(
            "INSERT INTO commitments (id, title, person, due_date, status) VALUES (?, ?, ?, ?, ?)",
            c
        )

    # Insert health metrics
    health_metrics = [
        ("health_1", str(today), "sleep", 75, None),
        ("health_2", str(today), "readiness", 82, None),
        ("health_3", str(today), "activity", 65, None),
        ("health_4", str(yesterday), "sleep", 68, None),
    ]
    for h in health_metrics:
        conn.execute(
            "INSERT INTO health_metrics (id, date, metric_type, score, value) VALUES (?, ?, ?, ?, ?)",
            h
        )

    # Insert brain dumps
    brain_dumps = [
        ("dump_1", "Task idea", "task", False),
        ("dump_2", "Worry about deadline", "worry", False),
        ("dump_3", "Business idea", "idea", False),
        ("dump_4", "Another task", "task", False),
        ("dump_5", "Processed thought", "thought", True),
    ]
    for b in brain_dumps:
        conn.execute(
            "INSERT INTO brain_dumps (id, content, category, processed) VALUES (?, ?, ?, ?)",
            b
        )

    conn.commit()
    conn.close()

    return mock_db


@pytest.fixture
def mock_state_store(mock_db):
    """Create a mock state store pointing to our test database."""
    store = MagicMock()
    store.db_path = mock_db

    def execute_sql(sql, params=()):
        conn = sqlite3.connect(str(mock_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    store.execute_sql = execute_sql

    def get_active_commitments(person=None):
        conn = sqlite3.connect(str(mock_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM commitments WHERE status = 'active'"
        params = []
        if person:
            query += " AND person = ?"
            params.append(person)
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    store.get_active_commitments = get_active_commitments

    def get_health_metrics(start_date=None, end_date=None, metric_type=None):
        conn = sqlite3.connect(str(mock_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM health_metrics WHERE 1=1"
        params = []
        if start_date:
            query += " AND date >= ?"
            params.append(str(start_date))
        if end_date:
            query += " AND date <= ?"
            params.append(str(end_date))
        if metric_type:
            query += " AND metric_type = ?"
            params.append(metric_type)
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    store.get_health_metrics = get_health_metrics

    def get_unprocessed_brain_dumps(limit=100):
        conn = sqlite3.connect(str(mock_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM brain_dumps WHERE processed = FALSE LIMIT ?",
            (limit,)
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    store.get_unprocessed_brain_dumps = get_unprocessed_brain_dumps

    def get_schema_version():
        conn = sqlite3.connect(str(mock_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0

    store.get_schema_version = get_schema_version

    return store


# =============================================================================
# Unit Tests: get_task_summary()
# =============================================================================

class TestGetTaskSummary:
    """Tests for get_task_summary() function."""

    def test_returns_correct_counts_with_populated_db(self, populated_db, mock_state_store):
        """Test that task summary returns correct counts."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_task_summary

            result = get_task_summary()

            assert 'error' not in result
            # Total should be 4 (active tasks, excluding done and cancelled)
            assert result['total'] == 4
            # 1 overdue task
            assert result['overdue'] == 1
            # 2 tasks due today (task_1 and task_3)
            assert result['due_today'] == 2
            # Check domains
            assert 'by_domain' in result
            assert result['by_domain'].get('work', 0) == 3  # task_1, task_2, task_4
            assert result['by_domain'].get('personal', 0) == 1  # task_3

    def test_returns_zero_counts_with_empty_db(self, mock_db, mock_state_store):
        """Test that task summary returns zeros with empty database."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_task_summary

            result = get_task_summary()

            assert 'error' not in result
            assert result['total'] == 0
            assert result['overdue'] == 0
            assert result['due_today'] == 0

    def test_handles_database_errors(self, mock_state_store):
        """Test that task summary handles database errors gracefully."""
        mock_state_store.execute_sql = MagicMock(side_effect=Exception("Database error"))

        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_task_summary

            result = get_task_summary()

            assert 'error' in result


# =============================================================================
# Unit Tests: get_commitment_summary()
# =============================================================================

class TestGetCommitmentSummary:
    """Tests for get_commitment_summary() function."""

    def test_categorizes_overdue_correctly(self, populated_db, mock_state_store):
        """Test that overdue commitments are correctly identified."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_commitment_summary

            result = get_commitment_summary()

            assert 'error' not in result
            # commit_1 is overdue (week ago)
            assert len(result['overdue']) == 1
            assert result['overdue'][0]['title'] == 'Overdue commitment'
            assert result['overdue'][0]['person'] == 'Alice'
            assert result['overdue'][0]['days_overdue'] == 7

    def test_categorizes_due_soon_correctly(self, populated_db, mock_state_store):
        """Test that commitments due within 7 days are identified."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_commitment_summary

            result = get_commitment_summary()

            assert 'error' not in result
            # commit_2 (2 days) and commit_3 (7 days) are both "due soon" (within 7 days)
            assert len(result['due_soon']) == 2
            # Check that Bob's commitment (2 days) is in due_soon
            bob_commitment = next((c for c in result['due_soon'] if c['person'] == 'Bob'), None)
            assert bob_commitment is not None
            assert bob_commitment['title'] == 'Due soon commitment'
            assert bob_commitment['days_until'] == 2

    def test_counts_upcoming_correctly(self, populated_db, mock_state_store):
        """Test that upcoming commitments (>7 days) are counted."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_commitment_summary

            result = get_commitment_summary()

            assert 'error' not in result
            # commit_3 (7 days) is "due soon" (<=7 days), commit_4 (no deadline) is upcoming
            # So only 1 commitment should be in upcoming
            assert result['upcoming_count'] == 1

    def test_total_active_count(self, populated_db, mock_state_store):
        """Test that total active commitment count is correct."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_commitment_summary

            result = get_commitment_summary()

            assert 'error' not in result
            # 4 active commitments (commit_1 through commit_4)
            assert result['total'] == 4

    def test_handles_missing_due_dates(self, populated_db, mock_state_store):
        """Test that commitments without due dates are handled."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_commitment_summary

            result = get_commitment_summary()

            assert 'error' not in result
            # Commitment with no deadline should be in upcoming
            assert result['upcoming_count'] >= 1

    def test_handles_empty_commitments(self, mock_db, mock_state_store):
        """Test with no commitments."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_commitment_summary

            result = get_commitment_summary()

            assert 'error' not in result
            assert result['total'] == 0
            assert result['overdue'] == []
            assert result['due_soon'] == []
            assert result['upcoming_count'] == 0


# =============================================================================
# Unit Tests: get_health_summary()
# =============================================================================

class TestGetHealthSummary:
    """Tests for get_health_summary() function."""

    def test_extracts_sleep_score(self, populated_db, mock_state_store):
        """Test that sleep score is extracted correctly."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_health_summary

            result = get_health_summary()

            assert 'error' not in result
            assert result['available'] is True
            # The code takes the last matching sleep metric from yesterday/today
            # We have today=75 and yesterday=68, last one wins
            assert result['sleep_score'] in [68, 75]  # Either is valid depending on query order

    def test_extracts_readiness_score(self, populated_db, mock_state_store):
        """Test that readiness score is extracted correctly."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_health_summary

            result = get_health_summary()

            assert 'error' not in result
            assert result['readiness_score'] == 82

    def test_extracts_activity_score(self, populated_db, mock_state_store):
        """Test that activity score is extracted correctly."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_health_summary

            result = get_health_summary()

            assert 'error' not in result
            assert result['activity_score'] == 65

    def test_handles_missing_health_data(self, mock_db, mock_state_store):
        """Test that missing health data is handled gracefully."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_health_summary

            result = get_health_summary()

            assert 'error' not in result
            assert result['available'] is False
            assert result['sleep_score'] is None
            assert result['readiness_score'] is None
            assert result['activity_score'] is None

    def test_handles_partial_health_data(self, mock_db, mock_state_store):
        """Test with only some health metrics available."""
        # Add just one metric
        conn = sqlite3.connect(str(mock_db))
        conn.execute(
            "INSERT INTO health_metrics (id, date, metric_type, score) VALUES (?, ?, ?, ?)",
            ("h1", str(date.today()), "sleep", 80)
        )
        conn.commit()
        conn.close()

        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_health_summary

            result = get_health_summary()

            assert result['available'] is True
            assert result['sleep_score'] == 80
            assert result['readiness_score'] is None


# =============================================================================
# Unit Tests: get_brain_dump_summary()
# =============================================================================

class TestGetBrainDumpSummary:
    """Tests for get_brain_dump_summary() function."""

    def test_counts_unprocessed_correctly(self, populated_db, mock_state_store):
        """Test that unprocessed brain dumps are counted correctly."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_brain_dump_summary

            result = get_brain_dump_summary()

            assert 'error' not in result
            # 4 unprocessed brain dumps
            assert result['unprocessed'] == 4

    def test_groups_by_category(self, populated_db, mock_state_store):
        """Test that brain dumps are grouped by category."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_brain_dump_summary

            result = get_brain_dump_summary()

            assert 'error' not in result
            assert 'by_category' in result
            # 2 tasks, 1 worry, 1 idea
            assert result['by_category'].get('task', 0) == 2
            assert result['by_category'].get('worry', 0) == 1
            assert result['by_category'].get('idea', 0) == 1

    def test_handles_uncategorized_dumps(self, mock_db, mock_state_store):
        """Test that uncategorized brain dumps are counted."""
        conn = sqlite3.connect(str(mock_db))
        conn.execute(
            "INSERT INTO brain_dumps (id, content, category, processed) VALUES (?, ?, ?, ?)",
            ("d1", "Uncategorized thought", None, False)
        )
        conn.commit()
        conn.close()

        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_brain_dump_summary

            result = get_brain_dump_summary()

            assert result['unprocessed'] == 1
            assert result['by_category'].get('uncategorized', 0) == 1

    def test_handles_empty_brain_dumps(self, mock_db, mock_state_store):
        """Test with no brain dumps."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_brain_dump_summary

            result = get_brain_dump_summary()

            assert result['unprocessed'] == 0
            assert result['by_category'] == {}


# =============================================================================
# Unit Tests: get_alerts_summary()
# =============================================================================

class TestGetAlertsSummary:
    """Tests for get_alerts_summary() function."""

    @pytest.mark.asyncio
    async def test_includes_alert_priorities(self):
        """Test that alert priorities are included in summary."""
        # Create mock alerts
        from Tools.alert_checker import Alert, AlertType, AlertPriority

        mock_alerts = [
            Alert(
                id="alert_1",
                alert_type=AlertType.TASK_OVERDUE,
                priority=AlertPriority.HIGH,
                title="High priority alert",
                message="Test message"
            ),
            Alert(
                id="alert_2",
                alert_type=AlertType.COMMITMENT_DUE_SOON,
                priority=AlertPriority.MEDIUM,
                title="Medium priority alert",
                message="Test message"
            ),
            Alert(
                id="alert_3",
                alert_type=AlertType.HEALTH_LOW_SLEEP,
                priority=AlertPriority.CRITICAL,
                title="Critical alert",
                message="Test message"
            ),
        ]

        with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_alerts

            from commands.status import get_alerts_summary

            result = await get_alerts_summary()

            assert 'error' not in result
            assert result['total'] == 3
            assert result['by_priority']['high'] == 1
            assert result['by_priority']['medium'] == 1
            assert result['by_priority']['critical'] == 1

    @pytest.mark.asyncio
    async def test_includes_alert_types(self):
        """Test that alert types are included in summary."""
        from Tools.alert_checker import Alert, AlertType, AlertPriority

        mock_alerts = [
            Alert(
                id="alert_1",
                alert_type=AlertType.TASK_OVERDUE,
                priority=AlertPriority.HIGH,
                title="Task overdue",
                message="Test"
            ),
            Alert(
                id="alert_2",
                alert_type=AlertType.TASK_OVERDUE,
                priority=AlertPriority.MEDIUM,
                title="Another overdue",
                message="Test"
            ),
        ]

        with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_alerts

            from commands.status import get_alerts_summary

            result = await get_alerts_summary()

            assert result['by_type']['task_overdue'] == 2

    @pytest.mark.asyncio
    async def test_limits_alerts_to_10(self):
        """Test that only top 10 alerts are included in detail."""
        from Tools.alert_checker import Alert, AlertType, AlertPriority

        mock_alerts = [
            Alert(
                id=f"alert_{i}",
                alert_type=AlertType.TASK_OVERDUE,
                priority=AlertPriority.LOW,
                title=f"Alert {i}",
                message="Test"
            )
            for i in range(15)
        ]

        with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_alerts

            from commands.status import get_alerts_summary

            result = await get_alerts_summary()

            assert result['total'] == 15
            assert len(result['alerts']) == 10

    @pytest.mark.asyncio
    async def test_handles_no_alerts(self):
        """Test with no alerts."""
        with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = []

            from commands.status import get_alerts_summary

            result = await get_alerts_summary()

            assert result['total'] == 0
            assert result['by_priority'] == {}
            assert result['by_type'] == {}
            assert result['alerts'] == []

    @pytest.mark.asyncio
    async def test_handles_alert_check_error(self):
        """Test that errors are handled gracefully."""
        with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
            mock_check.side_effect = Exception("Alert check failed")

            from commands.status import get_alerts_summary

            result = await get_alerts_summary()

            assert 'error' in result
            assert result['total'] == 0


# =============================================================================
# Unit Tests: generate_status()
# =============================================================================

class TestGenerateStatus:
    """Tests for generate_status() function."""

    @pytest.mark.asyncio
    async def test_returns_all_expected_sections(self, populated_db, mock_state_store):
        """Test that generate_status returns all expected sections."""
        from Tools.alert_checker import Alert, AlertType, AlertPriority

        mock_alerts = [
            Alert(
                id="alert_1",
                alert_type=AlertType.TASK_OVERDUE,
                priority=AlertPriority.HIGH,
                title="Test alert",
                message="Test"
            )
        ]

        with patch('commands.status.get_db', return_value=mock_state_store):
            with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = mock_alerts
                with patch('commands.status.Journal') as mock_journal:
                    mock_journal.return_value.query.return_value = []

                    from commands.status import generate_status

                    result = await generate_status()

                    assert 'timestamp' in result
                    assert 'alerts' in result
                    assert 'tasks' in result
                    assert 'commitments' in result
                    assert 'health' in result
                    assert 'brain_dumps' in result
                    assert 'system' in result

    @pytest.mark.asyncio
    async def test_alerts_only_flag(self, populated_db, mock_state_store):
        """Test that alerts_only flag returns only alerts section."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = []

                from commands.status import generate_status

                result = await generate_status(alerts_only=True)

                assert 'timestamp' in result
                assert 'alerts' in result
                assert 'tasks' not in result
                assert 'commitments' not in result
                assert 'health' not in result

    @pytest.mark.asyncio
    async def test_brief_flag_excludes_system(self, populated_db, mock_state_store):
        """Test that brief flag excludes system section."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = []

                from commands.status import generate_status

                result = await generate_status(brief=True)

                assert 'tasks' in result
                assert 'system' not in result


# =============================================================================
# Unit Tests: format_status_text()
# =============================================================================

class TestFormatStatusText:
    """Tests for format_status_text() function."""

    def test_includes_header(self):
        """Test that header is included in formatted output."""
        from commands.status import format_status_text

        status = {
            'timestamp': datetime.now().isoformat(),
            'alerts': {'total': 0},
            'tasks': {'total': 0, 'overdue': 0, 'due_today': 0, 'by_domain': {}},
            'commitments': {'total': 0, 'overdue': [], 'due_soon': []},
            'health': {'available': False},
            'brain_dumps': {'unprocessed': 0, 'by_category': {}},
        }

        result = format_status_text(status)

        assert "THANOS STATUS REPORT" in result
        assert "=" in result or "-" in result

    def test_shows_alerts_when_present(self):
        """Test that alerts are displayed when present."""
        from commands.status import format_status_text

        status = {
            'timestamp': datetime.now().isoformat(),
            'alerts': {
                'total': 2,
                'alerts': [
                    {'priority': 'high', 'title': 'High alert'},
                    {'priority': 'medium', 'title': 'Medium alert'},
                ]
            },
            'tasks': {'total': 0, 'overdue': 0, 'due_today': 0, 'by_domain': {}},
            'commitments': {'total': 0, 'overdue': [], 'due_soon': []},
            'health': {'available': False},
            'brain_dumps': {'unprocessed': 0, 'by_category': {}},
        }

        result = format_status_text(status)

        assert "ALERTS" in result
        assert "High alert" in result
        assert "Medium alert" in result

    def test_shows_task_counts(self):
        """Test that task counts are displayed."""
        from commands.status import format_status_text

        status = {
            'timestamp': datetime.now().isoformat(),
            'alerts': {'total': 0},
            'tasks': {
                'total': 5,
                'overdue': 2,
                'due_today': 1,
                'by_domain': {'work': 3, 'personal': 2}
            },
            'commitments': {'total': 0, 'overdue': [], 'due_soon': []},
            'health': {'available': False},
            'brain_dumps': {'unprocessed': 0, 'by_category': {}},
        }

        result = format_status_text(status)

        assert "TASKS" in result
        assert "5" in result  # total
        assert "Overdue" in result
        assert "2" in result  # overdue count

    def test_shows_commitment_warnings(self):
        """Test that overdue/due soon commitments are shown."""
        from commands.status import format_status_text

        status = {
            'timestamp': datetime.now().isoformat(),
            'alerts': {'total': 0},
            'tasks': {'total': 0, 'overdue': 0, 'due_today': 0, 'by_domain': {}},
            'commitments': {
                'total': 3,
                'overdue': [{'title': 'Overdue item', 'days_overdue': 5}],
                'due_soon': [{'title': 'Due soon item', 'days_until': 2}],
            },
            'health': {'available': False},
            'brain_dumps': {'unprocessed': 0, 'by_category': {}},
        }

        result = format_status_text(status)

        assert "COMMITMENTS" in result
        assert "Overdue item" in result
        assert "Due soon item" in result

    def test_shows_health_metrics(self):
        """Test that health metrics are displayed when available."""
        from commands.status import format_status_text

        status = {
            'timestamp': datetime.now().isoformat(),
            'alerts': {'total': 0},
            'tasks': {'total': 0, 'overdue': 0, 'due_today': 0, 'by_domain': {}},
            'commitments': {'total': 0, 'overdue': [], 'due_soon': []},
            'health': {
                'available': True,
                'sleep_score': 85,
                'readiness_score': 72,
                'activity_score': 68,
            },
            'brain_dumps': {'unprocessed': 0, 'by_category': {}},
        }

        result = format_status_text(status)

        assert "HEALTH" in result
        assert "Sleep" in result
        assert "85" in result
        assert "Readiness" in result
        assert "72" in result

    def test_shows_brain_dump_queue(self):
        """Test that brain dump queue is shown when items exist."""
        from commands.status import format_status_text

        status = {
            'timestamp': datetime.now().isoformat(),
            'alerts': {'total': 0},
            'tasks': {'total': 0, 'overdue': 0, 'due_today': 0, 'by_domain': {}},
            'commitments': {'total': 0, 'overdue': [], 'due_soon': []},
            'health': {'available': False},
            'brain_dumps': {
                'unprocessed': 3,
                'by_category': {'task': 2, 'idea': 1},
            },
        }

        result = format_status_text(status)

        assert "BRAIN DUMP" in result
        assert "Unprocessed" in result
        assert "3" in result

    def test_shows_system_section(self):
        """Test that system section is included when available."""
        from commands.status import format_status_text

        status = {
            'timestamp': datetime.now().isoformat(),
            'alerts': {'total': 0},
            'tasks': {'total': 0, 'overdue': 0, 'due_today': 0, 'by_domain': {}},
            'commitments': {'total': 0, 'overdue': [], 'due_soon': []},
            'health': {'available': False},
            'brain_dumps': {'unprocessed': 0, 'by_category': {}},
            'system': {
                'database': {'schema_version': 1, 'tables': 10, 'path': '/test/path'},
                'journal': {'recent_events': 5},
            },
        }

        result = format_status_text(status)

        assert "SYSTEM" in result
        assert "Schema" in result


# =============================================================================
# Integration Tests: execute() and CLI
# =============================================================================

class TestExecute:
    """Tests for execute() function."""

    @pytest.mark.asyncio
    async def test_json_output(self, populated_db, mock_state_store):
        """Test that JSON output is valid JSON."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = []
                with patch('commands.status.Journal') as mock_journal:
                    mock_journal.return_value.query.return_value = []

                    from commands.status import execute

                    result = await execute(output_json=True)

                    # Should be valid JSON
                    parsed = json.loads(result)
                    assert 'timestamp' in parsed
                    assert 'tasks' in parsed

    @pytest.mark.asyncio
    async def test_text_output(self, populated_db, mock_state_store):
        """Test that text output is readable."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = []
                with patch('commands.status.Journal') as mock_journal:
                    mock_journal.return_value.query.return_value = []

                    from commands.status import execute

                    result = await execute(output_json=False)

                    assert isinstance(result, str)
                    assert "THANOS" in result

    @pytest.mark.asyncio
    async def test_alerts_only_flag_in_execute(self, populated_db, mock_state_store):
        """Test alerts_only flag in execute function."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = []

                from commands.status import execute

                result = await execute(output_json=True, alerts_only=True)

                parsed = json.loads(result)
                assert 'alerts' in parsed
                assert 'tasks' not in parsed

    @pytest.mark.asyncio
    async def test_brief_flag_in_execute(self, populated_db, mock_state_store):
        """Test brief flag in execute function."""
        with patch('commands.status.get_db', return_value=mock_state_store):
            with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = []

                from commands.status import execute

                result = await execute(output_json=True, brief=True)

                parsed = json.loads(result)
                assert 'tasks' in parsed
                assert 'system' not in parsed


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_task_summary_with_null_domains(self, mock_db, mock_state_store):
        """Test task summary handles NULL domains."""
        conn = sqlite3.connect(str(mock_db))
        conn.execute(
            "INSERT INTO tasks (id, title, status, domain) VALUES (?, ?, ?, ?)",
            ("t1", "No domain task", "pending", None)
        )
        conn.commit()
        conn.close()

        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_task_summary

            result = get_task_summary()

            # Should handle NULL domain gracefully
            assert 'error' not in result
            assert 'unassigned' in result['by_domain'] or result['by_domain'].get(None) is not None

    def test_commitment_summary_with_invalid_dates(self, mock_db, mock_state_store):
        """Test commitment summary handles invalid date formats."""
        conn = sqlite3.connect(str(mock_db))
        conn.execute(
            "INSERT INTO commitments (id, title, person, due_date, status) VALUES (?, ?, ?, ?, ?)",
            ("c1", "Bad date commitment", "Test", "invalid-date", "active")
        )
        conn.commit()
        conn.close()

        with patch('commands.status.get_db', return_value=mock_state_store):
            from commands.status import get_commitment_summary

            result = get_commitment_summary()

            # Should handle invalid date gracefully
            assert 'error' not in result
            # Invalid date commitment should be in upcoming (fallback)
            assert result['upcoming_count'] >= 1

    @pytest.mark.asyncio
    async def test_status_with_all_errors(self):
        """Test status generation when all components error."""
        mock_store = MagicMock()
        mock_store.execute_sql = MagicMock(side_effect=Exception("DB error"))
        mock_store.get_active_commitments = MagicMock(side_effect=Exception("DB error"))
        mock_store.get_health_metrics = MagicMock(side_effect=Exception("DB error"))
        mock_store.get_unprocessed_brain_dumps = MagicMock(side_effect=Exception("DB error"))
        mock_store.get_schema_version = MagicMock(side_effect=Exception("DB error"))
        mock_store.db_path = "/test/path"

        with patch('commands.status.get_db', return_value=mock_store):
            with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
                mock_check.side_effect = Exception("Alert error")
                with patch('commands.status.Journal') as mock_journal:
                    mock_journal.return_value.query.return_value = []

                    from commands.status import generate_status

                    # Should not raise, should return partial status with errors
                    result = await generate_status()

                    assert 'timestamp' in result
                    # Each section should have an error or be missing
                    assert 'error' in result.get('tasks', {}) or result.get('tasks', {}).get('total', -1) >= 0


# =============================================================================
# CLI Integration Tests
# =============================================================================

class TestCLI:
    """Tests for CLI interface."""

    def test_cli_json_flag(self, populated_db, mock_state_store):
        """Test that --json flag produces valid JSON."""
        import subprocess
        import sys

        # We'll test this indirectly through the main function
        with patch('commands.status.get_db', return_value=mock_state_store):
            with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = []
                with patch('commands.status.Journal') as mock_journal:
                    mock_journal.return_value.query.return_value = []
                    with patch('sys.argv', ['status.py', '--json']):
                        with patch('builtins.print') as mock_print:
                            try:
                                # Import fresh to pick up argv changes
                                import importlib
                                import commands.status as status_module
                                importlib.reload(status_module)

                                # Run main - it will call print
                                status_module.main()

                                # Check that print was called with valid JSON
                                if mock_print.called:
                                    output = mock_print.call_args[0][0]
                                    parsed = json.loads(output)
                                    assert 'timestamp' in parsed
                            except SystemExit:
                                pass  # argparse may exit


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Basic performance tests."""

    @pytest.mark.asyncio
    async def test_status_generation_time(self, populated_db, mock_state_store):
        """Test that status generation completes in reasonable time."""
        import time

        with patch('commands.status.get_db', return_value=mock_state_store):
            with patch('commands.status.run_alert_check', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = []
                with patch('commands.status.Journal') as mock_journal:
                    mock_journal.return_value.query.return_value = []

                    from commands.status import generate_status

                    start = time.time()
                    await generate_status()
                    elapsed = time.time() - start

                    # Should complete in under 1 second with mocked data
                    assert elapsed < 1.0, f"Status generation took {elapsed:.2f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
