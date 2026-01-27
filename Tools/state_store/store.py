#!/usr/bin/env python3
"""
Unified State Store for Thanos.

Provides a comprehensive SQLite-based state management system for tasks,
commitments, ideas, notes, brain dumps, health metrics, and focus areas.

Usage:
    from Tools.state_store.store import StateStore

    store = StateStore()
    task_id = store.create_task(title="Review Q4 financials", domain="work")
    tasks = store.get_tasks(domain="work")
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from contextlib import contextmanager


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Task:
    """A task item with domain separation (work/personal)."""
    id: str
    title: str
    description: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, cancelled
    priority: Optional[str] = None  # p0, p1, p2, p3
    due_date: Optional[str] = None
    domain: str = "work"  # work, personal
    source: str = "manual"  # manual, brain_dump, workos, calendar
    source_id: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Commitment:
    """A promise or commitment made to someone."""
    id: str
    title: str
    description: Optional[str] = None
    stakeholder: Optional[str] = None
    deadline: Optional[str] = None
    status: str = "active"  # active, completed, abandoned
    priority: Optional[str] = None
    domain: str = "work"
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Idea:
    """A captured idea that may become a task."""
    id: str
    content: str
    category: Optional[str] = None  # feature, improvement, exploration
    domain: str = "work"
    source: str = "manual"  # manual, brain_dump, conversation
    status: str = "captured"  # captured, exploring, promoted, archived
    promoted_to_task_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Note:
    """A note or thought for reference."""
    id: str
    content: str
    title: Optional[str] = None
    category: Optional[str] = None
    domain: str = "personal"
    tags: Optional[List[str]] = None
    source: str = "manual"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class FocusArea:
    """An active area of focus or priority."""
    id: str
    title: str
    description: Optional[str] = None
    domain: str = "work"
    is_active: bool = True
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class HealthMetric:
    """A health or wellness metric."""
    id: int
    date: str
    metric_type: str  # sleep_score, hrv, readiness, steps, etc.
    value: float
    source: str = "oura"
    recorded_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class BrainDump:
    """A captured brain dump entry."""
    id: str
    content: str
    content_type: str = "text"  # text, voice, photo
    category: Optional[str] = None  # task, thought, idea, worry, commitment
    context: Optional[str] = None  # work, personal
    priority: Optional[str] = None
    source: str = "manual"  # manual, telegram, cli
    processed: bool = False
    archived: bool = False
    promoted_to_task_id: Optional[str] = None
    promoted_to_idea_id: Optional[str] = None
    created_at: Optional[str] = None
    processed_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# StateStore Implementation
# =============================================================================

class StateStore:
    """Unified SQLite state store for all Thanos data."""

    SCHEMA_VERSION = 2

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize state store.

        Args:
            db_path: Path to SQLite database. Defaults to State/thanos_unified.db
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "State" / "thanos_unified.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None  # Pooled connection for reuse
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

    def _get_pooled_connection(self):
        """Get persistent pooled connection for reuse.

        Returns the same connection across multiple calls for improved performance
        in high-frequency operations. Connection is configured with proper settings
        on first access.

        Returns:
            sqlite3.Connection: Persistent database connection
        """
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
        return self._conn

    def close(self):
        """Close the pooled connection if it exists.

        This method should be called when done with the StateStore instance
        to properly release database resources. It's also called automatically
        by __del__() during garbage collection.
        """
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                # Silently handle any errors during close
                pass
            finally:
                self._conn = None

    def __del__(self):
        """Destructor to ensure pooled connection is closed.

        Automatically called when the StateStore instance is garbage collected.
        Ensures proper cleanup of database resources.
        """
        self.close()

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
                    domain TEXT DEFAULT 'work',
                    source TEXT DEFAULT 'manual',
                    source_id TEXT,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
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
                    domain TEXT DEFAULT 'work',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata JSON
                );

                -- Ideas table
                CREATE TABLE IF NOT EXISTS ideas (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    category TEXT,
                    domain TEXT DEFAULT 'work',
                    source TEXT DEFAULT 'manual',
                    status TEXT DEFAULT 'captured',
                    promoted_to_task_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON,
                    FOREIGN KEY (promoted_to_task_id) REFERENCES tasks(id)
                );

                -- Notes table
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    content TEXT NOT NULL,
                    category TEXT,
                    domain TEXT DEFAULT 'personal',
                    tags TEXT,
                    source TEXT DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON
                );

                -- Focus areas table
                CREATE TABLE IF NOT EXISTS focus_areas (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    domain TEXT DEFAULT 'work',
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

                -- Brain dumps table
                CREATE TABLE IF NOT EXISTS brain_dumps (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    content_type TEXT DEFAULT 'text',
                    category TEXT,
                    context TEXT,
                    priority TEXT,
                    source TEXT DEFAULT 'manual',
                    processed BOOLEAN DEFAULT FALSE,
                    archived BOOLEAN DEFAULT FALSE,
                    promoted_to_task_id TEXT,
                    promoted_to_idea_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    metadata JSON,
                    FOREIGN KEY (promoted_to_task_id) REFERENCES tasks(id),
                    FOREIGN KEY (promoted_to_idea_id) REFERENCES ideas(id)
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
                CREATE INDEX IF NOT EXISTS idx_tasks_domain ON tasks(domain);
                CREATE INDEX IF NOT EXISTS idx_tasks_source ON tasks(source);
                CREATE INDEX IF NOT EXISTS idx_commitments_deadline ON commitments(deadline);
                CREATE INDEX IF NOT EXISTS idx_commitments_status ON commitments(status);
                CREATE INDEX IF NOT EXISTS idx_commitments_domain ON commitments(domain);
                CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status);
                CREATE INDEX IF NOT EXISTS idx_ideas_domain ON ideas(domain);
                CREATE INDEX IF NOT EXISTS idx_notes_domain ON notes(domain);
                CREATE INDEX IF NOT EXISTS idx_focus_areas_active ON focus_areas(is_active);
                CREATE INDEX IF NOT EXISTS idx_health_date ON health_metrics(date);
                CREATE INDEX IF NOT EXISTS idx_health_type ON health_metrics(metric_type);
                CREATE INDEX IF NOT EXISTS idx_brain_dumps_processed ON brain_dumps(processed);
                CREATE INDEX IF NOT EXISTS idx_brain_dumps_archived ON brain_dumps(archived);

                -- Record schema version
                INSERT OR IGNORE INTO schema_version (version) VALUES (2);
            ''')

    def _generate_id(self) -> str:
        """Generate a new UUID."""
        return str(uuid.uuid4())

    def _now_iso(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()

    def _today_iso(self) -> str:
        """Get today's date in ISO format."""
        return date.today().isoformat()

    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================

    def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[date] = None,
        domain: str = "work",
        source: str = "manual",
        source_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new task.

        Args:
            title: Task title
            description: Optional description
            priority: Priority level (p0, p1, p2, p3)
            due_date: Optional due date
            domain: 'work' or 'personal'
            source: Where the task came from
            source_id: External ID if synced from another system
            tags: List of tags
            metadata: Additional metadata

        Returns:
            Task ID
        """
        task_id = self._generate_id()
        now = self._now_iso()

        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO tasks (id, title, description, priority, due_date,
                                   domain, source, source_id, tags, metadata,
                                   created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id, title, description, priority,
                due_date.isoformat() if due_date else None,
                domain, source, source_id,
                json.dumps(tags) if tags else None,
                json.dumps(metadata) if metadata else None,
                now, now
            ))

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM tasks WHERE id = ?', (task_id,)
            ).fetchone()

            if row:
                return self._row_to_task(row)
        return None

    def get_tasks(
        self,
        domain: Optional[str] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        priority: Optional[str] = None,
        include_completed: bool = False,
        limit: int = 100
    ) -> List[Task]:
        """Get tasks with optional filters.

        Args:
            domain: Filter by domain ('work' or 'personal')
            status: Filter by status
            source: Filter by source
            priority: Filter by priority
            include_completed: Include completed tasks (default False)
            limit: Maximum number of tasks to return

        Returns:
            List of matching tasks
        """
        conditions = []
        params = []

        if domain:
            conditions.append('domain = ?')
            params.append(domain)
        if status:
            conditions.append('status = ?')
            params.append(status)
        if source:
            conditions.append('source = ?')
            params.append(source)
        if priority:
            conditions.append('priority = ?')
            params.append(priority)
        if not include_completed:
            conditions.append("status NOT IN ('completed', 'cancelled')")

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        with self._get_connection() as conn:
            rows = conn.execute(
                f'SELECT * FROM tasks WHERE {where_clause} ORDER BY created_at DESC LIMIT ?',
                params + [limit]
            ).fetchall()

            return [self._row_to_task(row) for row in rows]

    def update_task(self, task_id: str, **updates) -> bool:
        """Update task fields.

        Args:
            task_id: Task ID
            **updates: Fields to update

        Returns:
            True if task was updated
        """
        allowed_fields = {
            'title', 'description', 'status', 'priority',
            'due_date', 'domain', 'tags', 'metadata'
        }
        updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not updates:
            return False

        # Handle special cases
        if 'metadata' in updates:
            updates['metadata'] = json.dumps(updates['metadata'])
        if 'tags' in updates:
            updates['tags'] = json.dumps(updates['tags'])
        if 'due_date' in updates and isinstance(updates['due_date'], date):
            updates['due_date'] = updates['due_date'].isoformat()

        updates['updated_at'] = self._now_iso()

        # Track completion
        if updates.get('status') == 'completed':
            updates['completed_at'] = self._now_iso()

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

    def count_tasks(
        self,
        domain: Optional[str] = None,
        status: Optional[str] = None,
        overdue: bool = False
    ) -> int:
        """Count tasks with optional filters.

        Args:
            domain: Filter by domain
            status: Filter by status
            overdue: If True, count only overdue tasks (due_date < today)

        Returns:
            Count of matching tasks
        """
        conditions = []
        params = []

        if domain:
            conditions.append('domain = ?')
            params.append(domain)
        if status:
            conditions.append('status = ?')
            params.append(status)
        if overdue:
            today = self._today_iso()
            conditions.append('due_date < ?')
            params.append(today)
            conditions.append("status NOT IN ('completed', 'cancelled')")

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        conn = self._get_pooled_connection()
        row = conn.execute(
            f'SELECT COUNT(*) FROM tasks WHERE {where_clause}', params
        ).fetchone()
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
            domain=row['domain'],
            source=row['source'],
            source_id=row['source_id'],
            tags=json.loads(row['tags']) if row['tags'] else None,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            completed_at=row['completed_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # =========================================================================
    # COMMITMENT OPERATIONS
    # =========================================================================

    def create_commitment(
        self,
        title: str,
        description: Optional[str] = None,
        stakeholder: Optional[str] = None,
        deadline: Optional[date] = None,
        priority: Optional[str] = None,
        domain: str = "work",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new commitment.

        Returns:
            Commitment ID
        """
        commitment_id = self._generate_id()
        now = self._now_iso()

        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO commitments (id, title, description, stakeholder,
                                         deadline, priority, domain, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                commitment_id, title, description, stakeholder,
                deadline.isoformat() if deadline else None,
                priority, domain,
                json.dumps(metadata) if metadata else None,
                now
            ))

        return commitment_id

    def get_commitments(
        self,
        domain: Optional[str] = None,
        status: str = "active",
        stakeholder: Optional[str] = None,
        due_within_days: Optional[int] = None,
        limit: int = 100
    ) -> List[Commitment]:
        """Get commitments with optional filters.

        Args:
            domain: Filter by domain
            status: Filter by status (default 'active')
            stakeholder: Filter by stakeholder
            due_within_days: Only return commitments due within N days

        Returns:
            List of matching commitments
        """
        conditions = []
        params = []

        if domain:
            conditions.append('domain = ?')
            params.append(domain)
        if status:
            conditions.append('status = ?')
            params.append(status)
        if stakeholder:
            conditions.append('stakeholder = ?')
            params.append(stakeholder)
        if due_within_days is not None:
            deadline = (date.today() + timedelta(days=due_within_days)).isoformat()
            conditions.append('deadline <= ?')
            params.append(deadline)
            conditions.append('deadline IS NOT NULL')

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        with self._get_connection() as conn:
            rows = conn.execute(
                f'SELECT * FROM commitments WHERE {where_clause} ORDER BY deadline LIMIT ?',
                params + [limit]
            ).fetchall()

            return [self._row_to_commitment(row) for row in rows]

    def complete_commitment(self, commitment_id: str) -> bool:
        """Mark commitment as completed."""
        now = self._now_iso()

        with self._get_connection() as conn:
            cursor = conn.execute(
                'UPDATE commitments SET status = ?, completed_at = ? WHERE id = ?',
                ('completed', now, commitment_id)
            )
            return cursor.rowcount > 0

    def count_commitments(
        self,
        domain: Optional[str] = None,
        status: str = "active"
    ) -> int:
        """Count commitments."""
        conditions = ['status = ?']
        params = [status]

        if domain:
            conditions.append('domain = ?')
            params.append(domain)

        where_clause = ' AND '.join(conditions)

        conn = self._get_pooled_connection()
        row = conn.execute(
            f'SELECT COUNT(*) FROM commitments WHERE {where_clause}', params
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
            domain=row['domain'],
            created_at=row['created_at'],
            completed_at=row['completed_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # =========================================================================
    # IDEA OPERATIONS
    # =========================================================================

    def create_idea(
        self,
        content: str,
        category: Optional[str] = None,
        domain: str = "work",
        source: str = "manual",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new idea.

        Returns:
            Idea ID
        """
        idea_id = self._generate_id()
        now = self._now_iso()

        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO ideas (id, content, category, domain, source,
                                   metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                idea_id, content, category, domain, source,
                json.dumps(metadata) if metadata else None,
                now, now
            ))

        return idea_id

    def get_ideas(
        self,
        domain: Optional[str] = None,
        status: str = "captured",
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Idea]:
        """Get ideas with optional filters."""
        conditions = []
        params = []

        if domain:
            conditions.append('domain = ?')
            params.append(domain)
        if status:
            conditions.append('status = ?')
            params.append(status)
        if category:
            conditions.append('category = ?')
            params.append(category)

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        with self._get_connection() as conn:
            rows = conn.execute(
                f'SELECT * FROM ideas WHERE {where_clause} ORDER BY created_at DESC LIMIT ?',
                params + [limit]
            ).fetchall()

            return [self._row_to_idea(row) for row in rows]

    def promote_idea_to_task(
        self,
        idea_id: str,
        title: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[date] = None
    ) -> Optional[str]:
        """Promote an idea to a task.

        Args:
            idea_id: ID of the idea to promote
            title: Optional task title (defaults to idea content)
            priority: Optional priority for the task
            due_date: Optional due date for the task

        Returns:
            Task ID if successful, None if idea not found
        """
        with self._get_connection() as conn:
            # Get the idea
            row = conn.execute(
                'SELECT * FROM ideas WHERE id = ?', (idea_id,)
            ).fetchone()

            if not row:
                return None

            idea = self._row_to_idea(row)

            # Create the task
            task_id = self.create_task(
                title=title or idea.content[:100],
                description=idea.content if len(idea.content) > 100 else None,
                priority=priority,
                due_date=due_date,
                domain=idea.domain,
                source="idea",
                source_id=idea_id,
                metadata={"promoted_from_idea": idea_id}
            )

            # Update the idea status
            now = self._now_iso()
            conn.execute('''
                UPDATE ideas SET status = ?, promoted_to_task_id = ?, updated_at = ?
                WHERE id = ?
            ''', ('promoted', task_id, now, idea_id))

            return task_id

    def _row_to_idea(self, row: sqlite3.Row) -> Idea:
        """Convert database row to Idea object."""
        return Idea(
            id=row['id'],
            content=row['content'],
            category=row['category'],
            domain=row['domain'],
            source=row['source'],
            status=row['status'],
            promoted_to_task_id=row['promoted_to_task_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # =========================================================================
    # NOTE OPERATIONS
    # =========================================================================

    def create_note(
        self,
        content: str,
        title: Optional[str] = None,
        category: Optional[str] = None,
        domain: str = "personal",
        tags: Optional[List[str]] = None,
        source: str = "manual",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new note.

        Returns:
            Note ID
        """
        note_id = self._generate_id()
        now = self._now_iso()

        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO notes (id, title, content, category, domain, tags,
                                   source, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                note_id, title, content, category, domain,
                json.dumps(tags) if tags else None,
                source,
                json.dumps(metadata) if metadata else None,
                now, now
            ))

        return note_id

    def search_notes(
        self,
        query: str,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Note]:
        """Search notes by content.

        Args:
            query: Search query (matches title and content)
            domain: Filter by domain
            category: Filter by category
            limit: Maximum results

        Returns:
            List of matching notes
        """
        conditions = ["(content LIKE ? OR title LIKE ?)"]
        params = [f'%{query}%', f'%{query}%']

        if domain:
            conditions.append('domain = ?')
            params.append(domain)
        if category:
            conditions.append('category = ?')
            params.append(category)

        where_clause = ' AND '.join(conditions)

        with self._get_connection() as conn:
            rows = conn.execute(
                f'SELECT * FROM notes WHERE {where_clause} ORDER BY created_at DESC LIMIT ?',
                params + [limit]
            ).fetchall()

            return [self._row_to_note(row) for row in rows]

    def _row_to_note(self, row: sqlite3.Row) -> Note:
        """Convert database row to Note object."""
        return Note(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            category=row['category'],
            domain=row['domain'],
            tags=json.loads(row['tags']) if row['tags'] else None,
            source=row['source'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # =========================================================================
    # BRAIN DUMP OPERATIONS
    # =========================================================================

    def create_brain_dump(
        self,
        content: str,
        content_type: str = "text",
        category: Optional[str] = None,
        context: Optional[str] = None,
        priority: Optional[str] = None,
        source: str = "manual",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a brain dump entry.

        Returns:
            Brain dump ID
        """
        dump_id = self._generate_id()
        now = self._now_iso()

        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO brain_dumps (id, content, content_type, category,
                                         context, priority, source, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dump_id, content, content_type, category, context,
                priority, source,
                json.dumps(metadata) if metadata else None,
                now
            ))

        return dump_id

    def archive_brain_dump(self, dump_id: str) -> bool:
        """Archive a brain dump entry.

        Args:
            dump_id: Brain dump ID to archive

        Returns:
            True if archived successfully
        """
        now = self._now_iso()

        with self._get_connection() as conn:
            cursor = conn.execute('''
                UPDATE brain_dumps SET archived = TRUE, processed = TRUE, processed_at = ?
                WHERE id = ?
            ''', (now, dump_id))
            return cursor.rowcount > 0

    def get_brain_dumps(
        self,
        processed: Optional[bool] = None,
        archived: bool = False,
        context: Optional[str] = None,
        limit: int = 100
    ) -> List[BrainDump]:
        """Get brain dump entries.

        Args:
            processed: Filter by processed state
            archived: Include archived entries
            context: Filter by context (work/personal)
            limit: Maximum results

        Returns:
            List of brain dumps
        """
        conditions = []
        params = []

        if processed is not None:
            conditions.append('processed = ?')
            params.append(processed)
        if not archived:
            conditions.append('archived = FALSE')
        if context:
            conditions.append('context = ?')
            params.append(context)

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        with self._get_connection() as conn:
            rows = conn.execute(
                f'SELECT * FROM brain_dumps WHERE {where_clause} ORDER BY created_at DESC LIMIT ?',
                params + [limit]
            ).fetchall()

            return [self._row_to_brain_dump(row) for row in rows]

    def count_brain_dumps(
        self,
        processed: Optional[bool] = None,
        archived: bool = False
    ) -> int:
        """Count brain dump entries.

        Args:
            processed: Filter by processed state
            archived: Include archived entries

        Returns:
            Count of matching entries
        """
        conditions = []
        params = []

        if processed is not None:
            conditions.append('processed = ?')
            params.append(processed)
        if not archived:
            conditions.append('archived = FALSE')

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        conn = self._get_pooled_connection()
        row = conn.execute(
            f'SELECT COUNT(*) FROM brain_dumps WHERE {where_clause}', params
        ).fetchone()
        return row[0]

    def _row_to_brain_dump(self, row: sqlite3.Row) -> BrainDump:
        """Convert database row to BrainDump object."""
        return BrainDump(
            id=row['id'],
            content=row['content'],
            content_type=row['content_type'],
            category=row['category'],
            context=row['context'],
            priority=row['priority'],
            source=row['source'],
            processed=bool(row['processed']),
            archived=bool(row['archived']),
            promoted_to_task_id=row['promoted_to_task_id'],
            promoted_to_idea_id=row['promoted_to_idea_id'],
            created_at=row['created_at'],
            processed_at=row['processed_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # =========================================================================
    # HEALTH METRIC OPERATIONS
    # =========================================================================

    def log_health_metric(
        self,
        metric_type: str,
        value: float,
        metric_date: Optional[date] = None,
        source: str = "oura",
        metadata: Optional[Dict[str, Any]] = None
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
        metric_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        source: Optional[str] = None,
        limit: int = 100
    ) -> List[HealthMetric]:
        """Get health metrics with flexible filtering.

        Args:
            metric_date: Specific date to query
            metric_type: Filter by metric type
            start_date: Start of date range
            end_date: End of date range
            source: Filter by source
            limit: Maximum results

        Returns:
            List of matching health metrics
        """
        conditions = []
        params = []

        if metric_date:
            conditions.append('date = ?')
            params.append(metric_date.isoformat())
        if metric_type:
            conditions.append('metric_type = ?')
            params.append(metric_type)
        if start_date:
            conditions.append('date >= ?')
            params.append(start_date.isoformat())
        if end_date:
            conditions.append('date <= ?')
            params.append(end_date.isoformat())
        if source:
            conditions.append('source = ?')
            params.append(source)

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        with self._get_connection() as conn:
            rows = conn.execute(
                f'SELECT * FROM health_metrics WHERE {where_clause} ORDER BY date DESC LIMIT ?',
                params + [limit]
            ).fetchall()

            return [self._row_to_health_metric(row) for row in rows]

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

    # =========================================================================
    # FOCUS AREA OPERATIONS
    # =========================================================================

    def set_focus(
        self,
        title: str,
        description: Optional[str] = None,
        domain: str = "work",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Set a new focus area (deactivates existing ones in same domain).

        Args:
            title: Focus area title
            description: Optional description
            domain: 'work' or 'personal'
            metadata: Additional metadata

        Returns:
            Focus area ID
        """
        focus_id = self._generate_id()
        now = self._now_iso()

        with self._get_connection() as conn:
            # Deactivate existing focus areas in the same domain
            conn.execute('''
                UPDATE focus_areas SET is_active = FALSE, ended_at = ?
                WHERE domain = ? AND is_active = TRUE
            ''', (now, domain))

            # Create new focus area
            conn.execute('''
                INSERT INTO focus_areas (id, title, description, domain,
                                         metadata, started_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                focus_id, title, description, domain,
                json.dumps(metadata) if metadata else None,
                now
            ))

        return focus_id

    def get_active_focus(
        self,
        domain: Optional[str] = None
    ) -> List[FocusArea]:
        """Get active focus areas.

        Args:
            domain: Filter by domain (if None, returns all active)

        Returns:
            List of active focus areas
        """
        conditions = ['is_active = TRUE']
        params = []

        if domain:
            conditions.append('domain = ?')
            params.append(domain)

        where_clause = ' AND '.join(conditions)

        conn = self._get_pooled_connection()
        rows = conn.execute(
            f'SELECT * FROM focus_areas WHERE {where_clause} ORDER BY started_at DESC',
            params
        ).fetchall()

        return [self._row_to_focus_area(row) for row in rows]

    def _row_to_focus_area(self, row: sqlite3.Row) -> FocusArea:
        """Convert database row to FocusArea object."""
        return FocusArea(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            domain=row['domain'],
            is_active=bool(row['is_active']),
            started_at=row['started_at'],
            ended_at=row['ended_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # =========================================================================
    # EXPORT OPERATIONS
    # =========================================================================

    def export_summary(self) -> Dict[str, Any]:
        """Export a summary of all state.

        Returns:
            Dictionary with counts and summary info
        """
        return {
            'exported_at': self._now_iso(),
            'tasks': {
                'total': self.count_tasks(),
                'pending': self.count_tasks(status='pending'),
                'overdue': self.count_tasks(overdue=True),
                'work': self.count_tasks(domain='work'),
                'personal': self.count_tasks(domain='personal'),
            },
            'commitments': {
                'active': self.count_commitments(),
                'work': self.count_commitments(domain='work'),
                'personal': self.count_commitments(domain='personal'),
            },
            'brain_dumps': {
                'unprocessed': self.count_brain_dumps(processed=False),
                'total': self.count_brain_dumps(archived=True),
            },
            'focus_areas': [asdict(f) for f in self.get_active_focus()],
        }


# =============================================================================
# Module-level convenience function
# =============================================================================

_store_instance: Optional[StateStore] = None


def get_store(db_path: Optional[Path] = None) -> StateStore:
    """Get or create singleton StateStore instance."""
    global _store_instance

    if _store_instance is None or db_path is not None:
        _store_instance = StateStore(db_path)

    return _store_instance


if __name__ == "__main__":
    # Quick test
    store = StateStore()

    print("StateStore Test")
    print("=" * 60)

    # Test task creation
    task_id = store.create_task(
        title="Test work task",
        domain="work",
        priority="p1"
    )
    print(f"Created work task: {task_id}")

    personal_task_id = store.create_task(
        title="Test personal task",
        domain="personal"
    )
    print(f"Created personal task: {personal_task_id}")

    # Test get_tasks with domain filter
    work_tasks = store.get_tasks(domain="work")
    personal_tasks = store.get_tasks(domain="personal")
    print(f"Work tasks: {len(work_tasks)}")
    print(f"Personal tasks: {len(personal_tasks)}")

    # Test commitment
    commitment_id = store.create_commitment(
        title="Test commitment",
        stakeholder="Client X",
        deadline=date.today() + timedelta(days=5)
    )
    print(f"Created commitment: {commitment_id}")

    # Test commitments due within 7 days
    due_soon = store.get_commitments(due_within_days=7)
    print(f"Commitments due within 7 days: {len(due_soon)}")

    # Test idea
    idea_id = store.create_idea(content="A great new feature idea")
    print(f"Created idea: {idea_id}")

    # Test promote idea to task
    promoted_task_id = store.promote_idea_to_task(idea_id)
    print(f"Promoted idea to task: {promoted_task_id}")

    # Test brain dump
    dump_id = store.create_brain_dump(
        content="Quick thought to capture",
        context="work"
    )
    print(f"Created brain dump: {dump_id}")

    # Test archive
    store.archive_brain_dump(dump_id)
    print(f"Archived brain dump: {dump_id}")

    # Test health metrics
    metric_id = store.log_health_metric("sleep_score", 85.5)
    print(f"Logged health metric: {metric_id}")

    metrics = store.get_health_metrics(metric_date=date.today())
    print(f"Today's metrics: {len(metrics)}")

    # Test focus area
    focus_id = store.set_focus("Q1 Goals", domain="work")
    print(f"Set focus: {focus_id}")

    active_focus = store.get_active_focus()
    print(f"Active focus areas: {len(active_focus)}")

    # Export summary
    summary = store.export_summary()
    print(f"\nSummary: {json.dumps(summary, indent=2)}")
