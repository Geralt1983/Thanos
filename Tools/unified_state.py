#!/usr/bin/env python3
"""
Unified State Store for Thanos.

Consolidates all state into a single SQLite database with generated views.
Provides single source of truth for tasks, calendar, commitments, health,
finances, and focus areas.

Usage:
    from Tools.state_store import StateStore, get_state_store

    store = get_state_store()
    store.add_task(title="Review Q4 financials", priority="p1")
    tasks = store.get_tasks_due_today()
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import contextmanager


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    P0 = "p0"  # Critical/urgent
    P1 = "p1"  # High priority
    P2 = "p2"  # Medium priority
    P3 = "p3"  # Low priority


class CommitmentStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class TaskSource(Enum):
    WORKOS = "workos"
    BRAIN_DUMP = "brain_dump"
    MANUAL = "manual"
    CALENDAR = "calendar"


@dataclass
class Task:
    id: str
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: Optional[str] = None
    due_date: Optional[str] = None
    source: str = "manual"
    source_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class CalendarEvent:
    id: str
    title: str
    start_time: str
    end_time: Optional[str] = None
    location: Optional[str] = None
    source: str = "google"
    source_id: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class Commitment:
    id: str
    title: str
    description: Optional[str] = None
    stakeholder: Optional[str] = None
    deadline: Optional[str] = None
    status: str = "active"
    priority: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class FocusArea:
    id: str
    title: str
    description: Optional[str] = None
    is_active: bool = True
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class HealthMetric:
    id: int
    date: str
    metric_type: str
    value: float
    source: str = "oura"
    recorded_at: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class FinanceAccount:
    id: int
    date: str
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    balance: Optional[float] = None
    available: Optional[float] = None
    source: str = "monarch"
    recorded_at: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class Habit:
    """A habit to track."""
    id: int
    name: str
    description: Optional[str] = None
    emoji: Optional[str] = None
    frequency: str = "daily"  # daily, weekly, weekdays
    target_count: int = 1
    time_of_day: Optional[str] = None  # morning, evening, anytime
    category: Optional[str] = None  # health, productivity, relationship, personal
    is_active: bool = True
    current_streak: int = 0
    longest_streak: int = 0
    created_at: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class HabitCompletion:
    """A habit completion record."""
    id: int
    habit_id: int
    completed_at: str
    note: Optional[str] = None


@dataclass
class PendingReview:
    """A pending review for low-confidence brain dump classification."""
    id: int
    dump_id: str
    raw_content: str
    source: Optional[str] = None
    suggested_classification: Optional[str] = None
    confidence: Optional[float] = None
    review_reason: Optional[str] = None
    status: str = "pending"
    reviewed_at: Optional[str] = None
    final_classification: Optional[str] = None
    created_at: Optional[str] = None


class StateStore:
    """Unified SQLite state store for all Thanos data."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize state store.

        Args:
            db_path: Path to SQLite database. Defaults to State/thanos_unified.db
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "State" / "thanos_unified.db"

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
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript('''
                -- Schema version tracking
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Tasks table
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    priority TEXT,
                    due_date DATE,
                    source TEXT,
                    source_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata JSON
                );

                -- Calendar events table
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    location TEXT,
                    source TEXT,
                    source_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON
                );

                -- Commitments table
                CREATE TABLE IF NOT EXISTS commitments (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    stakeholder TEXT,
                    deadline DATE,
                    status TEXT DEFAULT 'active',
                    priority TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata JSON
                );

                -- Focus areas table
                CREATE TABLE IF NOT EXISTS focus_areas (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    metadata JSON
                );

                -- Health metrics table
                CREATE TABLE IF NOT EXISTS health_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    source TEXT DEFAULT 'oura',
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON,
                    UNIQUE(date, metric_type, source)
                );

                -- Finance accounts table
                CREATE TABLE IF NOT EXISTS finances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    account_id TEXT,
                    account_name TEXT,
                    balance REAL,
                    available REAL,
                    source TEXT DEFAULT 'monarch',
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON
                );

                -- Finance transactions table
                CREATE TABLE IF NOT EXISTS finance_transactions (
                    id TEXT PRIMARY KEY,
                    date DATE NOT NULL,
                    amount REAL NOT NULL,
                    merchant TEXT,
                    category TEXT,
                    account_id TEXT,
                    is_recurring BOOLEAN DEFAULT FALSE,
                    source TEXT DEFAULT 'monarch',
                    metadata JSON
                );

                -- Habits table (local, not WorkOS)
                CREATE TABLE IF NOT EXISTS habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    emoji TEXT,
                    frequency TEXT DEFAULT 'daily',
                    target_count INTEGER DEFAULT 1,
                    time_of_day TEXT,
                    category TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    current_streak INTEGER DEFAULT 0,
                    longest_streak INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON
                );

                -- Habit completions table
                CREATE TABLE IF NOT EXISTS habit_completions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id INTEGER NOT NULL,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_date DATE NOT NULL,
                    note TEXT,
                    FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE,
                    UNIQUE(habit_id, completed_date)
                );

                -- Pending reviews table (for low-confidence brain dump classifications)
                CREATE TABLE IF NOT EXISTS pending_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dump_id TEXT NOT NULL,
                    raw_content TEXT NOT NULL,
                    source TEXT,
                    suggested_classification TEXT,
                    confidence REAL,
                    review_reason TEXT,
                    status TEXT DEFAULT 'pending',
                    reviewed_at TIMESTAMP,
                    final_classification TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
                CREATE INDEX IF NOT EXISTS idx_tasks_source ON tasks(source);
                CREATE INDEX IF NOT EXISTS idx_calendar_start ON calendar_events(start_time);
                CREATE INDEX IF NOT EXISTS idx_commitments_deadline ON commitments(deadline);
                CREATE INDEX IF NOT EXISTS idx_commitments_status ON commitments(status);
                CREATE INDEX IF NOT EXISTS idx_health_date ON health_metrics(date);
                CREATE INDEX IF NOT EXISTS idx_health_type ON health_metrics(metric_type);
                CREATE INDEX IF NOT EXISTS idx_finances_date ON finances(date);
                CREATE INDEX IF NOT EXISTS idx_transactions_date ON finance_transactions(date);
                CREATE INDEX IF NOT EXISTS idx_habits_active ON habits(is_active);
                CREATE INDEX IF NOT EXISTS idx_habits_time ON habits(time_of_day);
                CREATE INDEX IF NOT EXISTS idx_habit_completions_habit ON habit_completions(habit_id);
                CREATE INDEX IF NOT EXISTS idx_habit_completions_date ON habit_completions(completed_date);
                CREATE INDEX IF NOT EXISTS idx_pending_reviews_status ON pending_reviews(status);

                -- Record schema version
                INSERT OR IGNORE INTO schema_version (version) VALUES (1);
            ''')

    # ==================== TASK OPERATIONS ====================

    def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[date] = None,
        source: str = "manual",
        source_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add a new task.

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO tasks (id, title, description, priority, due_date,
                                   source, source_id, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id, title, description, priority,
                due_date.isoformat() if due_date else None,
                source, source_id,
                json.dumps(metadata) if metadata else None,
                now, now
            ))

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM tasks WHERE id = ?', (task_id,)
            ).fetchone()

            if row:
                return self._row_to_task(row)
        return None

    def update_task(self, task_id: str, **updates) -> bool:
        """Update task fields.

        Args:
            task_id: Task ID
            **updates: Fields to update (title, description, status, priority, due_date, metadata)

        Returns:
            True if task was updated
        """
        allowed_fields = {'title', 'description', 'status', 'priority', 'due_date', 'metadata'}
        updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not updates:
            return False

        # Handle special cases
        if 'metadata' in updates:
            updates['metadata'] = json.dumps(updates['metadata'])
        if 'due_date' in updates and isinstance(updates['due_date'], date):
            updates['due_date'] = updates['due_date'].isoformat()

        updates['updated_at'] = datetime.now().isoformat()

        # Track completion
        if updates.get('status') == 'completed':
            updates['completed_at'] = datetime.now().isoformat()

        set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
        values = list(updates.values()) + [task_id]

        with self._get_connection() as conn:
            cursor = conn.execute(
                f'UPDATE tasks SET {set_clause} WHERE id = ?', values
            )
            return cursor.rowcount > 0

    def complete_task(self, task_id: str) -> bool:
        """Mark task as completed."""
        return self.update_task(task_id, status='completed')

    def get_tasks(
        self,
        status: Optional[str] = None,
        source: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100
    ) -> List[Task]:
        """Get tasks with optional filters."""
        conditions = []
        params = []

        if status:
            conditions.append('status = ?')
            params.append(status)
        if source:
            conditions.append('source = ?')
            params.append(source)
        if priority:
            conditions.append('priority = ?')
            params.append(priority)

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        with self._get_connection() as conn:
            rows = conn.execute(
                f'SELECT * FROM tasks WHERE {where_clause} ORDER BY created_at DESC LIMIT ?',
                params + [limit]
            ).fetchall()

            return [self._row_to_task(row) for row in rows]

    def get_tasks_due_today(self) -> List[Task]:
        """Get tasks due today."""
        today = date.today().isoformat()

        with self._get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM tasks WHERE due_date = ? AND status NOT IN (?, ?)',
                (today, 'completed', 'cancelled')
            ).fetchall()

            return [self._row_to_task(row) for row in rows]

    def get_overdue_tasks(self) -> List[Task]:
        """Get overdue tasks."""
        today = date.today().isoformat()

        with self._get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM tasks WHERE due_date < ? AND status NOT IN (?, ?)',
                (today, 'completed', 'cancelled')
            ).fetchall()

            return [self._row_to_task(row) for row in rows]

    def count_tasks(self, status: Optional[str] = None) -> int:
        """Count tasks, optionally by status."""
        with self._get_connection() as conn:
            if status:
                row = conn.execute(
                    'SELECT COUNT(*) FROM tasks WHERE status = ?', (status,)
                ).fetchone()
            else:
                row = conn.execute('SELECT COUNT(*) FROM tasks').fetchone()
            return row[0]

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert database row to Task object."""
        return Task(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            status=row['status'],
            priority=row['priority'],
            due_date=row['due_date'],
            source=row['source'],
            source_id=row['source_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            completed_at=row['completed_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # ==================== CALENDAR OPERATIONS ====================

    def add_calendar_event(
        self,
        title: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        source: str = "google",
        source_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add a calendar event."""
        event_id = str(uuid.uuid4())

        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO calendar_events (id, title, start_time, end_time,
                                             location, source, source_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id, title, start_time.isoformat(),
                end_time.isoformat() if end_time else None,
                location, source, source_id,
                json.dumps(metadata) if metadata else None
            ))

        return event_id

    def get_events_today(self) -> List[CalendarEvent]:
        """Get today's calendar events."""
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())

        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM calendar_events
                WHERE start_time BETWEEN ? AND ?
                ORDER BY start_time
            ''', (today_start.isoformat(), today_end.isoformat())).fetchall()

            return [self._row_to_event(row) for row in rows]

    def get_events_range(
        self,
        start: datetime,
        end: datetime
    ) -> List[CalendarEvent]:
        """Get events in a date range."""
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM calendar_events
                WHERE start_time BETWEEN ? AND ?
                ORDER BY start_time
            ''', (start.isoformat(), end.isoformat())).fetchall()

            return [self._row_to_event(row) for row in rows]

    def get_next_event(self) -> Optional[CalendarEvent]:
        """Get the next upcoming event."""
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            row = conn.execute('''
                SELECT * FROM calendar_events
                WHERE start_time > ?
                ORDER BY start_time
                LIMIT 1
            ''', (now,)).fetchone()

            if row:
                return self._row_to_event(row)
        return None

    def count_events_today(self) -> int:
        """Count today's events."""
        return len(self.get_events_today())

    def _row_to_event(self, row: sqlite3.Row) -> CalendarEvent:
        """Convert database row to CalendarEvent object."""
        return CalendarEvent(
            id=row['id'],
            title=row['title'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            location=row['location'],
            source=row['source'],
            source_id=row['source_id'],
            created_at=row['created_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # ==================== COMMITMENT OPERATIONS ====================

    def add_commitment(
        self,
        title: str,
        description: Optional[str] = None,
        stakeholder: Optional[str] = None,
        deadline: Optional[date] = None,
        priority: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add a new commitment."""
        commitment_id = str(uuid.uuid4())

        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO commitments (id, title, description, stakeholder,
                                         deadline, priority, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                commitment_id, title, description, stakeholder,
                deadline.isoformat() if deadline else None,
                priority,
                json.dumps(metadata) if metadata else None
            ))

        return commitment_id

    def get_active_commitments(self) -> List[Commitment]:
        """Get all active commitments."""
        with self._get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM commitments WHERE status = ? ORDER BY deadline',
                ('active',)
            ).fetchall()

            return [self._row_to_commitment(row) for row in rows]

    def get_commitments_due_soon(self, days: int = 7) -> List[Commitment]:
        """Get commitments due within specified days."""
        today = date.today()
        deadline = (today + timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM commitments
                WHERE status = 'active' AND deadline <= ?
                ORDER BY deadline
            ''', (deadline,)).fetchall()

            return [self._row_to_commitment(row) for row in rows]

    def complete_commitment(self, commitment_id: str) -> bool:
        """Mark commitment as completed."""
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute(
                'UPDATE commitments SET status = ?, completed_at = ? WHERE id = ?',
                ('completed', now, commitment_id)
            )
            return cursor.rowcount > 0

    def count_active_commitments(self) -> int:
        """Count active commitments."""
        with self._get_connection() as conn:
            row = conn.execute(
                'SELECT COUNT(*) FROM commitments WHERE status = ?', ('active',)
            ).fetchone()
            return row[0]

    def _row_to_commitment(self, row: sqlite3.Row) -> Commitment:
        """Convert database row to Commitment object."""
        return Commitment(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            stakeholder=row['stakeholder'],
            deadline=row['deadline'],
            status=row['status'],
            priority=row['priority'],
            created_at=row['created_at'],
            completed_at=row['completed_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # ==================== HABIT OPERATIONS ====================

    def add_habit(
        self,
        name: str,
        description: Optional[str] = None,
        emoji: Optional[str] = None,
        frequency: str = "daily",
        target_count: int = 1,
        time_of_day: Optional[str] = None,
        category: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """Add a new habit.

        Args:
            name: Habit name
            description: Optional description
            emoji: Emoji icon
            frequency: daily, weekly, weekdays
            target_count: Times per period
            time_of_day: morning, evening, anytime
            category: health, productivity, relationship, personal
            metadata: Additional data

        Returns:
            Habit ID
        """
        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO habits (name, description, emoji, frequency, target_count,
                                    time_of_day, category, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, description, emoji, frequency, target_count,
                time_of_day, category,
                json.dumps(metadata) if metadata else None
            ))
            return cursor.lastrowid

    def get_habit(self, habit_id: int) -> Optional[Habit]:
        """Get habit by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM habits WHERE id = ?', (habit_id,)
            ).fetchone()

            if row:
                return self._row_to_habit(row)
        return None

    def get_habits(self, active_only: bool = True) -> List[Habit]:
        """Get all habits.

        Args:
            active_only: Only return active habits

        Returns:
            List of habits
        """
        with self._get_connection() as conn:
            if active_only:
                rows = conn.execute(
                    'SELECT * FROM habits WHERE is_active = TRUE ORDER BY id'
                ).fetchall()
            else:
                rows = conn.execute('SELECT * FROM habits ORDER BY id').fetchall()

            return [self._row_to_habit(row) for row in rows]

    def get_habits_by_time(self, time_of_day: str) -> List[Habit]:
        """Get habits for specific time of day.

        Args:
            time_of_day: morning, evening, or anytime

        Returns:
            Habits matching the time
        """
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM habits
                WHERE is_active = TRUE AND (time_of_day = ? OR time_of_day = 'anytime' OR time_of_day IS NULL)
                ORDER BY id
            ''', (time_of_day,)).fetchall()

            return [self._row_to_habit(row) for row in rows]

    def complete_habit(
        self,
        habit_id: int,
        note: Optional[str] = None,
        completion_date: Optional[date] = None
    ) -> bool:
        """Mark habit as completed for today (or specified date).

        Args:
            habit_id: Habit ID
            note: Optional note
            completion_date: Date of completion (defaults to today)

        Returns:
            True if completion was recorded
        """
        completion_date = completion_date or date.today()
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            try:
                conn.execute('''
                    INSERT INTO habit_completions (habit_id, completed_at, completed_date, note)
                    VALUES (?, ?, ?, ?)
                ''', (habit_id, now, completion_date.isoformat(), note))

                # Update streak
                self._update_habit_streak(conn, habit_id)
                return True

            except sqlite3.IntegrityError:
                # Already completed today
                return False

    def is_habit_completed_today(self, habit_id: int) -> bool:
        """Check if habit is completed today."""
        today = date.today().isoformat()

        with self._get_connection() as conn:
            row = conn.execute('''
                SELECT COUNT(*) FROM habit_completions
                WHERE habit_id = ? AND completed_date = ?
            ''', (habit_id, today)).fetchone()

            return row[0] > 0

    def get_habit_completions(
        self,
        habit_id: Optional[int] = None,
        days: int = 7
    ) -> List[HabitCompletion]:
        """Get habit completions for the past N days.

        Args:
            habit_id: Filter by habit (optional)
            days: Number of days to look back

        Returns:
            List of completions
        """
        start_date = (date.today() - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            if habit_id:
                rows = conn.execute('''
                    SELECT * FROM habit_completions
                    WHERE habit_id = ? AND completed_date >= ?
                    ORDER BY completed_date DESC
                ''', (habit_id, start_date)).fetchall()
            else:
                rows = conn.execute('''
                    SELECT * FROM habit_completions
                    WHERE completed_date >= ?
                    ORDER BY completed_date DESC
                ''', (start_date,)).fetchall()

            return [HabitCompletion(
                id=row['id'],
                habit_id=row['habit_id'],
                completed_at=row['completed_at'],
                note=row['note']
            ) for row in rows]

    def get_habit_streak(self, habit_id: int) -> Dict[str, int]:
        """Get streak information for a habit.

        Returns:
            Dict with current_streak and longest_streak
        """
        habit = self.get_habit(habit_id)
        if not habit:
            return {'current_streak': 0, 'longest_streak': 0}

        return {
            'current_streak': habit.current_streak,
            'longest_streak': habit.longest_streak
        }

    def get_habits_due_checkin(
        self,
        time_of_day: str = "all",
        include_completed: bool = False
    ) -> List[Dict[str, Any]]:
        """Get habits due for check-in.

        Args:
            time_of_day: morning, evening, or all
            include_completed: Include already completed habits

        Returns:
            List of habit dicts with completion status
        """
        if time_of_day == "all":
            habits = self.get_habits(active_only=True)
        else:
            habits = self.get_habits_by_time(time_of_day)

        today = date.today().isoformat()
        result = []

        with self._get_connection() as conn:
            for habit in habits:
                completion = conn.execute('''
                    SELECT * FROM habit_completions
                    WHERE habit_id = ? AND completed_date = ?
                ''', (habit.id, today)).fetchone()

                is_completed = completion is not None

                if include_completed or not is_completed:
                    result.append({
                        'id': habit.id,
                        'name': habit.name,
                        'emoji': habit.emoji or '📋',
                        'category': habit.category,
                        'time_of_day': habit.time_of_day,
                        'current_streak': habit.current_streak,
                        'is_completed': is_completed,
                        'completion_note': completion['note'] if completion else None
                    })

        return result

    def delete_habit(self, habit_id: int) -> bool:
        """Delete a habit and all its completions."""
        with self._get_connection() as conn:
            cursor = conn.execute('DELETE FROM habits WHERE id = ?', (habit_id,))
            return cursor.rowcount > 0

    def deactivate_habit(self, habit_id: int) -> bool:
        """Deactivate a habit (soft delete)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                'UPDATE habits SET is_active = FALSE WHERE id = ?', (habit_id,)
            )
            return cursor.rowcount > 0

    def _update_habit_streak(self, conn: sqlite3.Connection, habit_id: int) -> None:
        """Update streak count for a habit."""
        today = date.today()
        current_streak = 0

        # Count consecutive days backward from today
        check_date = today
        while True:
            row = conn.execute('''
                SELECT COUNT(*) FROM habit_completions
                WHERE habit_id = ? AND completed_date = ?
            ''', (habit_id, check_date.isoformat())).fetchone()

            if row[0] > 0:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        # Update habit record
        conn.execute('''
            UPDATE habits
            SET current_streak = ?,
                longest_streak = MAX(longest_streak, ?)
            WHERE id = ?
        ''', (current_streak, current_streak, habit_id))

    def recalculate_all_streaks(self) -> int:
        """Recalculate streaks for all active habits.

        Returns:
            Number of habits updated
        """
        habits = self.get_habits(active_only=True)
        count = 0

        with self._get_connection() as conn:
            for habit in habits:
                self._update_habit_streak(conn, habit.id)
                count += 1

        return count

    def _row_to_habit(self, row: sqlite3.Row) -> Habit:
        """Convert database row to Habit object."""
        return Habit(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            emoji=row['emoji'],
            frequency=row['frequency'],
            target_count=row['target_count'],
            time_of_day=row['time_of_day'],
            category=row['category'],
            is_active=bool(row['is_active']),
            current_streak=row['current_streak'] or 0,
            longest_streak=row['longest_streak'] or 0,
            created_at=row['created_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    def get_habit_dashboard(self, days: int = 7) -> Dict[str, Any]:
        """Get habit dashboard data.

        Returns:
            Dict with habits, completions, and streaks
        """
        habits = self.get_habits(active_only=True)
        today = date.today()

        # Build completion grid
        grid = {}
        for habit in habits:
            grid[habit.id] = {
                'name': habit.name,
                'emoji': habit.emoji or '📋',
                'streak': habit.current_streak,
                'completions': []
            }

        # Get completions for date range
        start_date = today - timedelta(days=days - 1)
        completions = self.get_habit_completions(days=days)

        # Map completions to dates
        completion_map = {}
        for c in completions:
            key = (c.habit_id, c.completed_at[:10])  # Date portion only
            completion_map[key] = True

        # Fill in grid
        for habit_id in grid:
            for i in range(days):
                check_date = (start_date + timedelta(days=i)).isoformat()
                grid[habit_id]['completions'].append(
                    (habit_id, check_date) in completion_map
                )

        return {
            'habits': grid,
            'date_range': {
                'start': start_date.isoformat(),
                'end': today.isoformat()
            },
            'total_habits': len(habits),
            'dates': [(start_date + timedelta(days=i)).strftime('%a') for i in range(days)]
        }

    # ==================== PENDING REVIEW OPERATIONS ====================

    def add_pending_review(
        self,
        dump_id: str,
        raw_content: str,
        source: Optional[str] = None,
        suggested_classification: Optional[str] = None,
        confidence: Optional[float] = None,
        review_reason: Optional[str] = None
    ) -> int:
        """Add a pending review for low-confidence brain dump classification.

        Args:
            dump_id: Brain dump ID
            raw_content: Raw brain dump content
            source: Source of the dump (telegram, cli, etc.)
            suggested_classification: AI-suggested classification
            confidence: Confidence score (0-1)
            review_reason: Why this needs review

        Returns:
            Review ID
        """
        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO pending_reviews
                (dump_id, raw_content, source, suggested_classification, confidence, review_reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (dump_id, raw_content, source, suggested_classification, confidence, review_reason))
            return cursor.lastrowid

    def get_pending_reviews(self, status: str = 'pending') -> List[Dict]:
        """Get pending reviews by status.

        Args:
            status: Review status (pending, approved, rejected)

        Returns:
            List of review dicts
        """
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM pending_reviews
                WHERE status = ?
                ORDER BY created_at DESC
            ''', (status,)).fetchall()

            return [dict(row) for row in rows]

    def approve_review(
        self,
        review_id: int,
        final_classification: Optional[str] = None
    ) -> bool:
        """Approve a pending review.

        Args:
            review_id: Review ID
            final_classification: Optional classification override

        Returns:
            True if review was approved
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            # Get the review to see suggested classification
            review = conn.execute(
                'SELECT suggested_classification FROM pending_reviews WHERE id = ?',
                (review_id,)
            ).fetchone()

            if not review:
                return False

            # Use provided classification or fall back to suggested
            classification = final_classification or review['suggested_classification']

            cursor = conn.execute('''
                UPDATE pending_reviews
                SET status = 'approved',
                    reviewed_at = ?,
                    final_classification = ?
                WHERE id = ?
            ''', (now, classification, review_id))

            return cursor.rowcount > 0

    def reject_review(self, review_id: int) -> bool:
        """Reject a pending review.

        Args:
            review_id: Review ID

        Returns:
            True if review was rejected
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute('''
                UPDATE pending_reviews
                SET status = 'rejected',
                    reviewed_at = ?
                WHERE id = ?
            ''', (now, review_id))

            return cursor.rowcount > 0

    def count_pending_reviews(self) -> int:
        """Count pending reviews.

        Returns:
            Number of pending reviews
        """
        with self._get_connection() as conn:
            row = conn.execute(
                'SELECT COUNT(*) FROM pending_reviews WHERE status = ?',
                ('pending',)
            ).fetchone()
            return row[0]

    # ==================== HEALTH METRICS ====================

    def log_health_metric(
        self,
        metric_type: str,
        value: float,
        metric_date: Optional[date] = None,
        source: str = "oura",
        metadata: Optional[Dict] = None
    ) -> int:
        """Log a health metric.

        Args:
            metric_type: Type of metric (sleep_score, hrv, readiness, steps, etc.)
            value: Metric value
            metric_date: Date of metric (defaults to today)
            source: Data source
            metadata: Additional metadata

        Returns:
            Metric ID
        """
        if metric_date is None:
            metric_date = date.today()

        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT OR REPLACE INTO health_metrics
                (date, metric_type, value, source, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                metric_date.isoformat(), metric_type, value, source,
                json.dumps(metadata) if metadata else None
            ))
            return cursor.lastrowid

    def get_health_metrics(
        self,
        metric_date: Optional[date] = None,
        metric_type: Optional[str] = None
    ) -> List[HealthMetric]:
        """Get health metrics."""
        conditions = []
        params = []

        if metric_date:
            conditions.append('date = ?')
            params.append(metric_date.isoformat())
        if metric_type:
            conditions.append('metric_type = ?')
            params.append(metric_type)

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        with self._get_connection() as conn:
            rows = conn.execute(
                f'SELECT * FROM health_metrics WHERE {where_clause} ORDER BY date DESC',
                params
            ).fetchall()

            return [self._row_to_health_metric(row) for row in rows]

    def get_today_health(self) -> Dict[str, float]:
        """Get today's health metrics as a dictionary."""
        metrics = self.get_health_metrics(metric_date=date.today())
        return {m.metric_type: m.value for m in metrics}

    def _row_to_health_metric(self, row: sqlite3.Row) -> HealthMetric:
        """Convert database row to HealthMetric object."""
        return HealthMetric(
            id=row['id'],
            date=row['date'],
            metric_type=row['metric_type'],
            value=row['value'],
            source=row['source'],
            recorded_at=row['recorded_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # ==================== FINANCE OPERATIONS ====================

    def log_account_balance(
        self,
        account_id: str,
        account_name: str,
        balance: float,
        available: Optional[float] = None,
        balance_date: Optional[date] = None,
        source: str = "monarch",
        metadata: Optional[Dict] = None
    ) -> int:
        """Log account balance."""
        if balance_date is None:
            balance_date = date.today()

        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO finances
                (date, account_id, account_name, balance, available, source, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                balance_date.isoformat(), account_id, account_name,
                balance, available, source,
                json.dumps(metadata) if metadata else None
            ))
            return cursor.lastrowid

    def get_latest_balances(self) -> List[FinanceAccount]:
        """Get most recent balance for each account."""
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT f1.* FROM finances f1
                INNER JOIN (
                    SELECT account_id, MAX(date) as max_date
                    FROM finances GROUP BY account_id
                ) f2 ON f1.account_id = f2.account_id AND f1.date = f2.max_date
            ''').fetchall()

            return [self._row_to_finance(row) for row in rows]

    def get_total_available(self) -> float:
        """Get total available balance across all accounts."""
        balances = self.get_latest_balances()
        return sum(b.available or b.balance or 0 for b in balances)

    def _row_to_finance(self, row: sqlite3.Row) -> FinanceAccount:
        """Convert database row to FinanceAccount object."""
        return FinanceAccount(
            id=row['id'],
            date=row['date'],
            account_id=row['account_id'],
            account_name=row['account_name'],
            balance=row['balance'],
            available=row['available'],
            source=row['source'],
            recorded_at=row['recorded_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # ==================== FOCUS AREAS ====================

    def add_focus_area(
        self,
        title: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add a new focus area."""
        focus_id = str(uuid.uuid4())

        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO focus_areas (id, title, description, metadata)
                VALUES (?, ?, ?, ?)
            ''', (
                focus_id, title, description,
                json.dumps(metadata) if metadata else None
            ))

        return focus_id

    def get_active_focus_areas(self) -> List[FocusArea]:
        """Get all active focus areas."""
        with self._get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM focus_areas WHERE is_active = TRUE'
            ).fetchall()

            return [self._row_to_focus(row) for row in rows]

    def _row_to_focus(self, row: sqlite3.Row) -> FocusArea:
        """Convert database row to FocusArea object."""
        return FocusArea(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            is_active=bool(row['is_active']),
            started_at=row['started_at'],
            ended_at=row['ended_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # ==================== SNAPSHOT OPERATIONS ====================

    def export_snapshot(self) -> Dict[str, Any]:
        """Export current state as JSON snapshot."""
        return {
            'exported_at': datetime.now().isoformat(),
            'schema_version': self.SCHEMA_VERSION,
            'tasks': [asdict(t) for t in self.get_tasks(limit=1000)],
            'commitments': [asdict(c) for c in self.get_active_commitments()],
            'focus_areas': [asdict(f) for f in self.get_active_focus_areas()],
            'health_today': self.get_today_health(),
            'finances': [asdict(f) for f in self.get_latest_balances()],
            'stats': {
                'tasks_total': self.count_tasks(),
                'tasks_pending': self.count_tasks('pending'),
                'tasks_completed': self.count_tasks('completed'),
                'commitments_active': self.count_active_commitments(),
                'events_today': self.count_events_today()
            }
        }

    def save_daily_snapshot(self, snapshot_dir: Optional[Path] = None) -> Path:
        """Save daily snapshot to file."""
        if snapshot_dir is None:
            snapshot_dir = self.db_path.parent / "snapshots"

        snapshot_dir.mkdir(parents=True, exist_ok=True)

        snapshot = self.export_snapshot()
        filename = f"{date.today().isoformat()}.json"
        filepath = snapshot_dir / filename

        filepath.write_text(json.dumps(snapshot, indent=2))
        return filepath

    # ==================== MARKDOWN EXPORT ====================

    def export_today_markdown(self) -> str:
        """Generate Today.md equivalent from DB state."""
        lines = [f"# Today - {date.today().strftime('%A, %B %d, %Y')}", ""]

        # Events
        events = self.get_events_today()
        if events:
            lines.append("## Schedule")
            for event in events:
                start = datetime.fromisoformat(event.start_time).strftime("%I:%M %p")
                lines.append(f"- {start}: {event.title}")
            lines.append("")

        # Tasks due today
        tasks = self.get_tasks_due_today()
        if tasks:
            lines.append("## Tasks Due Today")
            for task in tasks:
                checkbox = "[ ]" if task.status != 'completed' else "[x]"
                priority = f" ({task.priority})" if task.priority else ""
                lines.append(f"- {checkbox} {task.title}{priority}")
            lines.append("")

        # Overdue
        overdue = self.get_overdue_tasks()
        if overdue:
            lines.append("## Overdue")
            for task in overdue:
                lines.append(f"- [ ] {task.title} (due: {task.due_date})")
            lines.append("")

        return "\n".join(lines)

    def export_commitments_markdown(self) -> str:
        """Generate Commitments.md equivalent from DB state."""
        lines = ["# Commitments", ""]

        commitments = self.get_active_commitments()

        # Group by stakeholder
        by_stakeholder: Dict[str, List[Commitment]] = {}
        for c in commitments:
            key = c.stakeholder or "General"
            if key not in by_stakeholder:
                by_stakeholder[key] = []
            by_stakeholder[key].append(c)

        for stakeholder, items in sorted(by_stakeholder.items()):
            lines.append(f"## {stakeholder}")
            for c in items:
                deadline = f" (by {c.deadline})" if c.deadline else ""
                lines.append(f"- [ ] {c.title}{deadline}")
            lines.append("")

        return "\n".join(lines)


# Singleton instance
_state_store: Optional[StateStore] = None


def get_state_store(db_path: Optional[Path] = None) -> StateStore:
    """Get or create singleton StateStore instance."""
    global _state_store

    if _state_store is None or db_path is not None:
        _state_store = StateStore(db_path)

    return _state_store


if __name__ == "__main__":
    # Test the state store
    store = get_state_store()

    print("State Store Test")
    print("=" * 60)

    # Add a test task
    task_id = store.add_task(
        title="Test task from StateStore",
        priority="p1",
        due_date=date.today()
    )
    print(f"Created task: {task_id}")

    # Get tasks
    tasks = store.get_tasks()
    print(f"Total tasks: {len(tasks)}")

    # Export snapshot
    snapshot = store.export_snapshot()
    print(f"Snapshot keys: {list(snapshot.keys())}")
    print(f"Stats: {snapshot['stats']}")
