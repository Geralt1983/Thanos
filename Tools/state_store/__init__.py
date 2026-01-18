"""
SQLite-based unified state store for Thanos life operating system.
Provides persistent storage for tasks, calendar, commitments, health metrics,
finances, brain dumps, and system state.
"""
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from contextlib import contextmanager

# Default database location
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "State" / "thanos.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Module-level database instance
_db_instance: Optional["UnifiedStateStore"] = None


def get_db(db_path: Optional[Path] = None) -> "UnifiedStateStore":
    """Get the unified state store instance.

    Creates the database at State/thanos.db if it doesn't exist.
    Uses singleton pattern for efficiency.

    Args:
        db_path: Optional custom database path. Defaults to State/thanos.db.

    Returns:
        UnifiedStateStore instance.
    """
    global _db_instance

    path = db_path or DEFAULT_DB_PATH

    if _db_instance is None or _db_instance.db_path != path:
        _db_instance = UnifiedStateStore(path)

    return _db_instance


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}{uid}" if prefix else uid


class UnifiedStateStore:
    """Unified SQLite-backed state storage for Thanos life operating system."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        """Initialize the unified state store.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with the full schema.

        Handles existing databases by only creating missing tables/indexes.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Check if this is a fresh database or needs migration
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='schema_version'
            """)

            if cursor.fetchone() is None:
                # Check if there are existing tables (legacy database)
                cursor.execute("""
                    SELECT COUNT(*) FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                has_tables = cursor.fetchone()[0] > 0

                if has_tables:
                    # Existing database - apply schema incrementally
                    self._apply_schema_incremental(conn)
                elif SCHEMA_PATH.exists():
                    # Fresh database - run full schema
                    schema_sql = SCHEMA_PATH.read_text()
                    conn.executescript(schema_sql)
                else:
                    # Fallback: create minimal tables inline
                    self._create_minimal_schema(cursor)
                    conn.commit()

    def _apply_schema_incremental(self, conn: sqlite3.Connection) -> None:
        """Apply schema incrementally to existing database.

        Only creates tables/indexes that don't exist yet.
        """
        cursor = conn.cursor()

        # Get existing tables
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        existing_tables = {row[0] for row in cursor.fetchall()}

        # Define new tables to add (ones that don't conflict with existing schema)
        new_tables = {
            "tasks": """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    priority TEXT,
                    due_date DATE,
                    due_time TIME,
                    domain TEXT NOT NULL DEFAULT 'work',
                    context TEXT,
                    energy_level TEXT,
                    estimated_minutes INTEGER,
                    actual_minutes INTEGER,
                    source TEXT NOT NULL DEFAULT 'manual',
                    source_id TEXT,
                    parent_task_id TEXT,
                    project_id TEXT,
                    tags JSON,
                    recurrence JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata JSON
                )
            """,
            "calendar_events": """
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    location TEXT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    all_day BOOLEAN DEFAULT FALSE,
                    calendar_id TEXT,
                    calendar_name TEXT,
                    event_type TEXT,
                    attendees JSON,
                    conferencing JSON,
                    reminders JSON,
                    recurrence_rule TEXT,
                    source TEXT DEFAULT 'google',
                    source_id TEXT,
                    status TEXT DEFAULT 'confirmed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_at TIMESTAMP,
                    metadata JSON
                )
            """,
            "commitments": """
                CREATE TABLE IF NOT EXISTS commitments (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    person TEXT NOT NULL,
                    person_email TEXT,
                    commitment_type TEXT,
                    due_date DATE,
                    due_time TIME,
                    status TEXT DEFAULT 'active',
                    priority TEXT,
                    context TEXT,
                    reminder_sent BOOLEAN DEFAULT FALSE,
                    reminder_count INTEGER DEFAULT 0,
                    last_reminder_at TIMESTAMP,
                    related_task_id TEXT,
                    related_event_id TEXT,
                    source TEXT DEFAULT 'manual',
                    source_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    notes TEXT,
                    metadata JSON
                )
            """,
            "focus_areas": """
                CREATE TABLE IF NOT EXISTS focus_areas (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    domain TEXT NOT NULL,
                    timeframe TEXT,
                    status TEXT DEFAULT 'active',
                    priority INTEGER DEFAULT 0,
                    progress_percent INTEGER DEFAULT 0,
                    target_date DATE,
                    success_criteria TEXT,
                    key_results JSON,
                    parent_focus_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata JSON
                )
            """,
            "ideas": """
                CREATE TABLE IF NOT EXISTS ideas (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    domain TEXT,
                    status TEXT DEFAULT 'captured',
                    potential_value TEXT,
                    effort_estimate TEXT,
                    related_focus_id TEXT,
                    converted_to_task_id TEXT,
                    source TEXT DEFAULT 'brain_dump',
                    tags JSON,
                    links JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    metadata JSON
                )
            """,
            "notes": """
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    content_type TEXT DEFAULT 'markdown',
                    category TEXT,
                    tags JSON,
                    related_task_id TEXT,
                    related_event_id TEXT,
                    related_person TEXT,
                    source TEXT DEFAULT 'manual',
                    source_id TEXT,
                    pinned BOOLEAN DEFAULT FALSE,
                    archived BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON
                )
            """,
            "health_metrics": """
                CREATE TABLE IF NOT EXISTS health_metrics (
                    id TEXT PRIMARY KEY,
                    date DATE NOT NULL,
                    metric_type TEXT NOT NULL,
                    score INTEGER,
                    value REAL,
                    unit TEXT,
                    details JSON,
                    source TEXT DEFAULT 'oura',
                    source_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_at TIMESTAMP,
                    metadata JSON,
                    UNIQUE(date, metric_type, source)
                )
            """,
            "finance_accounts": """
                CREATE TABLE IF NOT EXISTS finance_accounts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    institution TEXT,
                    account_type TEXT,
                    currency TEXT DEFAULT 'USD',
                    is_active BOOLEAN DEFAULT TRUE,
                    source TEXT,
                    source_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON
                )
            """,
            "finance_balances": """
                CREATE TABLE IF NOT EXISTS finance_balances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    balance REAL NOT NULL,
                    available_balance REAL,
                    as_of_date DATE NOT NULL,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON,
                    UNIQUE(account_id, as_of_date)
                )
            """,
            "finance_transactions": """
                CREATE TABLE IF NOT EXISTS finance_transactions (
                    id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    date DATE NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    description TEXT,
                    merchant TEXT,
                    category TEXT,
                    subcategory TEXT,
                    transaction_type TEXT,
                    is_pending BOOLEAN DEFAULT FALSE,
                    is_recurring BOOLEAN DEFAULT FALSE,
                    tags JSON,
                    source TEXT,
                    source_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON
                )
            """,
            "habits": """
                CREATE TABLE IF NOT EXISTS habits (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    emoji TEXT,
                    frequency TEXT DEFAULT 'daily',
                    time_of_day TEXT,
                    target_count INTEGER DEFAULT 1,
                    category TEXT,
                    current_streak INTEGER DEFAULT 0,
                    longest_streak INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    source TEXT DEFAULT 'workos',
                    source_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON
                )
            """,
            "habit_completions": """
                CREATE TABLE IF NOT EXISTS habit_completions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id TEXT NOT NULL,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date DATE NOT NULL,
                    count INTEGER DEFAULT 1,
                    note TEXT,
                    source TEXT DEFAULT 'manual',
                    metadata JSON,
                    UNIQUE(habit_id, date)
                )
            """,
            "contacts": """
                CREATE TABLE IF NOT EXISTS contacts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    company TEXT,
                    role TEXT,
                    relationship_type TEXT,
                    importance TEXT,
                    last_contact_date DATE,
                    next_contact_date DATE,
                    contact_frequency TEXT,
                    notes TEXT,
                    tags JSON,
                    source TEXT DEFAULT 'manual',
                    source_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON
                )
            """,
            "sync_state": """
                CREATE TABLE IF NOT EXISTS sync_state (
                    id TEXT PRIMARY KEY,
                    last_sync_at TIMESTAMP,
                    last_sync_status TEXT,
                    last_sync_error TEXT,
                    sync_cursor TEXT,
                    items_synced INTEGER DEFAULT 0,
                    next_sync_at TIMESTAMP,
                    config JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "schema_version": """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """,
        }

        # Create missing tables
        for table_name, create_sql in new_tables.items():
            if table_name not in existing_tables:
                cursor.execute(create_sql)
                print(f"Created table: {table_name}")

        # Add journal_v2 for new schema (keeps old journal intact)
        if "journal_v2" not in existing_tables:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS journal_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id TEXT,
                    action TEXT NOT NULL,
                    actor TEXT DEFAULT 'system',
                    changes JSON,
                    context JSON,
                    session_id TEXT,
                    metadata JSON
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_journal_v2_timestamp ON journal_v2(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_journal_v2_type ON journal_v2(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_journal_v2_entity ON journal_v2(entity_type, entity_id)")

        # Add brain_dumps if not exists
        if "brain_dumps" not in existing_tables:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS brain_dumps (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_context JSON,
                    category TEXT,
                    processed BOOLEAN DEFAULT FALSE,
                    processed_at TIMESTAMP,
                    processing_result JSON,
                    sentiment TEXT,
                    urgency TEXT,
                    domain TEXT,
                    tags JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON
                )
            """)

        # Create indexes for new tables
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_domain ON tasks(domain)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)",
            "CREATE INDEX IF NOT EXISTS idx_calendar_start ON calendar_events(start_time)",
            "CREATE INDEX IF NOT EXISTS idx_commitments_person ON commitments(person)",
            "CREATE INDEX IF NOT EXISTS idx_commitments_due ON commitments(due_date)",
            "CREATE INDEX IF NOT EXISTS idx_health_date ON health_metrics(date)",
            "CREATE INDEX IF NOT EXISTS idx_health_type ON health_metrics(metric_type)",
            "CREATE INDEX IF NOT EXISTS idx_brain_dumps_processed ON brain_dumps(processed)",
            "CREATE INDEX IF NOT EXISTS idx_brain_dumps_created ON brain_dumps(created_at)",
        ]
        for idx_sql in indexes:
            try:
                cursor.execute(idx_sql)
            except sqlite3.OperationalError:
                pass  # Index may already exist or table missing

        # Record schema version
        cursor.execute("""
            INSERT OR IGNORE INTO schema_version (version, description)
            VALUES (1, 'Unified state store schema (incremental migration)')
        """)

        conn.commit()

    def _create_minimal_schema(self, cursor: sqlite3.Cursor) -> None:
        """Create minimal schema if schema.sql is not available."""
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT,
                due_date DATE,
                due_time TIME,
                domain TEXT NOT NULL,
                context TEXT,
                source TEXT NOT NULL,
                source_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                metadata JSON
            )
        """)

        # State table for key-value storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Journal for event logging
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                entity_type TEXT,
                entity_id TEXT,
                action TEXT NOT NULL,
                actor TEXT DEFAULT 'system',
                changes JSON,
                context JSON,
                session_id TEXT,
                metadata JSON
            )
        """)

        # Brain dumps
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS brain_dumps (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                source_context JSON,
                category TEXT,
                processed BOOLEAN DEFAULT FALSE,
                processed_at TIMESTAMP,
                processing_result JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON
            )
        """)

        # Turn logs for API usage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS turn_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                latency_ms REAL DEFAULT 0.0,
                tool_call_count INTEGER DEFAULT 0,
                state_size INTEGER DEFAULT 0,
                prompt_bytes INTEGER DEFAULT 0,
                response_bytes INTEGER DEFAULT 0
            )
        """)

        # Tool summaries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tool_name TEXT,
                summary TEXT,
                result_type TEXT
            )
        """)

    @contextmanager
    def connection(self):
        """Context manager for database connections with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # =========================================================================
    # State Key-Value Store (Legacy compatibility)
    # =========================================================================

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state value by key."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM state WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return default
        except (sqlite3.Error, json.JSONDecodeError):
            return default

    def set_state(self, key: str, value: Any) -> None:
        """Set a state value."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO state (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, json.dumps(value)))
        except (sqlite3.Error, TypeError):
            pass

    def get_state_size(self) -> int:
        """Get the total size of stored state in bytes."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(LENGTH(value)) FROM state")
                row = cursor.fetchone()
                return row[0] or 0
        except sqlite3.Error:
            return 0

    # =========================================================================
    # Tasks
    # =========================================================================

    def create_task(
        self,
        title: str,
        domain: str,
        source: str,
        description: Optional[str] = None,
        status: str = "pending",
        priority: Optional[str] = None,
        due_date: Optional[Union[str, date]] = None,
        due_time: Optional[str] = None,
        context: Optional[str] = None,
        source_id: Optional[str] = None,
        energy_level: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Create a new task.

        Returns:
            The task ID.
        """
        task_id = generate_id("task_")

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (
                    id, title, description, status, priority,
                    due_date, due_time, domain, context, source,
                    source_id, energy_level, tags, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id, title, description, status, priority,
                str(due_date) if due_date else None, due_time,
                domain, context, source, source_id, energy_level,
                json.dumps(tags) if tags else None,
                json.dumps(metadata) if metadata else None,
            ))

            # Log to journal
            self._log_event(
                cursor, "task_created", "task", task_id, "create",
                context={"title": title, "domain": domain}
            )

        return task_id

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a task by ID."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_tasks(
        self,
        status: Optional[str] = None,
        domain: Optional[str] = None,
        due_date: Optional[Union[str, date]] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Get tasks with optional filters."""
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        if due_date:
            query += " AND due_date = ?"
            params.append(str(due_date))

        query += " ORDER BY due_date, priority DESC LIMIT ?"
        params.append(limit)

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def update_task(self, task_id: str, **updates) -> bool:
        """Update a task."""
        if not updates:
            return False

        # Handle JSON fields
        for field in ["tags", "metadata"]:
            if field in updates and updates[field] is not None:
                updates[field] = json.dumps(updates[field])

        updates["updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [task_id]

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE tasks SET {set_clause} WHERE id = ?",
                values
            )

            if cursor.rowcount > 0:
                self._log_event(
                    cursor, "task_updated", "task", task_id, "update",
                    changes=updates
                )
                return True
        return False

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed."""
        return self.update_task(
            task_id,
            status="done",
            completed_at=datetime.now().isoformat()
        )

    # =========================================================================
    # Brain Dumps
    # =========================================================================

    def create_brain_dump(
        self,
        content: str,
        source: str,
        category: Optional[str] = None,
        source_context: Optional[Dict] = None,
        domain: Optional[str] = None,
        urgency: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Create a new brain dump entry."""
        dump_id = generate_id("dump_")

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO brain_dumps (
                    id, content, source, source_context, category,
                    domain, urgency, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dump_id, content, source,
                json.dumps(source_context) if source_context else None,
                category, domain, urgency,
                json.dumps(metadata) if metadata else None,
            ))

            self._log_event(
                cursor, "brain_dump_created", "brain_dump", dump_id, "create",
                context={"source": source, "category": category}
            )

        return dump_id

    def get_unprocessed_brain_dumps(self, limit: int = 20) -> List[Dict]:
        """Get unprocessed brain dump entries."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM brain_dumps
                WHERE processed = FALSE
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def process_brain_dump(
        self,
        dump_id: str,
        result: Optional[Dict] = None,
    ) -> bool:
        """Mark a brain dump as processed."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE brain_dumps
                SET processed = TRUE,
                    processed_at = CURRENT_TIMESTAMP,
                    processing_result = ?
                WHERE id = ?
            """, (json.dumps(result) if result else None, dump_id))

            if cursor.rowcount > 0:
                self._log_event(
                    cursor, "brain_dump_processed", "brain_dump", dump_id, "process",
                    context=result
                )
                return True
        return False

    # =========================================================================
    # Journal (Event Log)
    # =========================================================================

    def _log_event(
        self,
        cursor: sqlite3.Cursor,
        event_type: str,
        entity_type: Optional[str],
        entity_id: Optional[str],
        action: str,
        actor: str = "system",
        changes: Optional[Dict] = None,
        context: Optional[Dict] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log an event to the journal.

        Uses journal_v2 if available (for migrated databases),
        otherwise uses the standard journal table.
        """
        # Check which journal table to use
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='journal_v2'
        """)
        use_v2 = cursor.fetchone() is not None

        if use_v2:
            cursor.execute("""
                INSERT INTO journal_v2 (
                    event_type, entity_type, entity_id, action, actor,
                    changes, context, session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_type, entity_type, entity_id, action, actor,
                json.dumps(changes) if changes else None,
                json.dumps(context) if context else None,
                session_id,
            ))
        else:
            # Try the new journal schema
            try:
                cursor.execute("""
                    INSERT INTO journal (
                        event_type, entity_type, entity_id, action, actor,
                        changes, context, session_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_type, entity_type, entity_id, action, actor,
                    json.dumps(changes) if changes else None,
                    json.dumps(context) if context else None,
                    session_id,
                ))
            except sqlite3.OperationalError:
                # Fall back to legacy journal format
                cursor.execute("""
                    INSERT INTO journal (
                        event_type, source, severity, title, data, session_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event_type, actor, "info",
                    f"{action}: {entity_type}/{entity_id}" if entity_type else action,
                    json.dumps({"changes": changes, "context": context}),
                    session_id,
                ))

    def log_event(
        self,
        event_type: str,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        actor: str = "system",
        changes: Optional[Dict] = None,
        context: Optional[Dict] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log an event to the journal (public API)."""
        with self.connection() as conn:
            cursor = conn.cursor()
            self._log_event(
                cursor, event_type, entity_type, entity_id, action,
                actor, changes, context, session_id
            )

    def get_journal_events(
        self,
        event_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Get journal events with optional filters."""
        query = "SELECT * FROM journal WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Health Metrics
    # =========================================================================

    def store_health_metric(
        self,
        date: Union[str, date],
        metric_type: str,
        score: Optional[int] = None,
        value: Optional[float] = None,
        unit: Optional[str] = None,
        details: Optional[Dict] = None,
        source: str = "oura",
        source_id: Optional[str] = None,
    ) -> str:
        """Store a health metric."""
        metric_id = generate_id("health_")

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO health_metrics (
                    id, date, metric_type, score, value, unit,
                    details, source, source_id, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                metric_id, str(date), metric_type, score, value, unit,
                json.dumps(details) if details else None, source, source_id,
            ))

        return metric_id

    def get_health_metrics(
        self,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        metric_type: Optional[str] = None,
    ) -> List[Dict]:
        """Get health metrics with optional filters."""
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

        query += " ORDER BY date DESC, metric_type"

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Commitments
    # =========================================================================

    def create_commitment(
        self,
        title: str,
        person: str,
        commitment_type: str = "deliverable",
        due_date: Optional[Union[str, date]] = None,
        description: Optional[str] = None,
        priority: str = "medium",
        source: str = "manual",
        metadata: Optional[Dict] = None,
    ) -> str:
        """Create a new commitment."""
        commit_id = generate_id("commit_")

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO commitments (
                    id, title, description, person, commitment_type,
                    due_date, priority, source, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                commit_id, title, description, person, commitment_type,
                str(due_date) if due_date else None, priority, source,
                json.dumps(metadata) if metadata else None,
            ))

            self._log_event(
                cursor, "commitment_created", "commitment", commit_id, "create",
                context={"title": title, "person": person}
            )

        return commit_id

    def get_active_commitments(self, person: Optional[str] = None) -> List[Dict]:
        """Get active commitments."""
        query = "SELECT * FROM commitments WHERE status = 'active'"
        params = []

        if person:
            query += " AND person = ?"
            params.append(person)

        query += " ORDER BY due_date"

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Turn Logs (Legacy compatibility)
    # =========================================================================

    def record_turn_log(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        tool_call_count: int = 0,
        state_size: int = 0,
        prompt_bytes: int = 0,
        response_bytes: int = 0,
    ) -> None:
        """Record a turn log entry for API usage tracking."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO turn_logs (
                        model, input_tokens, output_tokens, cost_usd,
                        latency_ms, tool_call_count, state_size,
                        prompt_bytes, response_bytes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    model, input_tokens, output_tokens, cost_usd,
                    latency_ms, tool_call_count, state_size,
                    prompt_bytes, response_bytes
                ))
        except sqlite3.Error:
            pass

    def get_recent_summaries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent tool summaries."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT tool_name, summary, result_type, timestamp
                    FROM tool_summaries
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def add_tool_summary(
        self,
        tool_name: str,
        summary: str,
        result_type: str = "success"
    ) -> None:
        """Add a tool execution summary."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tool_summaries (tool_name, summary, result_type)
                    VALUES (?, ?, ?)
                """, (tool_name, summary, result_type))
        except sqlite3.Error:
            pass

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def execute_sql(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute raw SQL and return results."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if cursor.description:
                return [dict(row) for row in cursor.fetchall()]
            return []

    def get_today_agenda(self) -> List[Dict]:
        """Get today's agenda (tasks and events)."""
        return self.execute_sql("SELECT * FROM v_today_agenda")

    def get_overdue_items(self) -> List[Dict]:
        """Get overdue tasks and commitments."""
        return self.execute_sql("SELECT * FROM v_overdue")

    def get_schema_version(self) -> int:
        """Get the current schema version."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(version) FROM schema_version")
                row = cursor.fetchone()
                return row[0] if row and row[0] else 0
        except sqlite3.Error:
            return 0


# Legacy compatibility: SQLiteStateStore alias
SQLiteStateStore = UnifiedStateStore

# Export public API
__all__ = [
    "get_db",
    "generate_id",
    "UnifiedStateStore",
    "SQLiteStateStore",  # Legacy alias
    "DEFAULT_DB_PATH",
]
