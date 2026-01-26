"""
SQLite Storage Implementation for Thanos Memory System.

Provides persistent storage for activities, struggles, values,
relationships, and summaries with full-text search support.
"""

import sqlite3
import json
import logging
import uuid
from pathlib import Path
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

from .models import (
    Activity, Struggle, UserValue, Relationship,
    DaySummary, WeekSummary, MemoryResult
)

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "State" / "memory.db"


class MemoryStore:
    """
    SQLite-based storage for the memory system.

    Handles all CRUD operations for activities, struggles, values,
    relationships, and summaries. Supports full-text search via FTS5.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the memory store.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper settings."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _initialize_schema(self):
        """Initialize the database schema."""
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            with self._get_connection() as conn:
                conn.executescript(schema_sql)
                logger.info(f"Memory database initialized at {self.db_path}")
        else:
            logger.warning(f"Schema file not found at {schema_path}")

    # =========================================================================
    # Activity Operations
    # =========================================================================

    async def store_activity(self, activity: Activity) -> str:
        """
        Store an activity in the database.

        Args:
            activity: Activity to store.

        Returns:
            Activity ID.
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO activities (
                    id, timestamp, activity_type, title, description, content,
                    project, domain, energy_level,
                    duration_minutes, started_at, ended_at,
                    source, source_context,
                    related_task_id, related_event_id, related_commitment_id, session_id,
                    sentiment, struggle_detected, struggle_type,
                    search_text, embedding_id, metadata
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?
                )
            """, (
                activity.id,
                activity.timestamp.isoformat(),
                activity.activity_type,
                activity.title,
                activity.description,
                activity.content,
                activity.project,
                activity.domain,
                activity.energy_level,
                activity.duration_minutes,
                activity.started_at.isoformat() if activity.started_at else None,
                activity.ended_at.isoformat() if activity.ended_at else None,
                activity.source,
                json.dumps(activity.source_context) if activity.source_context else None,
                activity.related_task_id,
                activity.related_event_id,
                activity.related_commitment_id,
                activity.session_id,
                activity.sentiment,
                activity.struggle_detected,
                activity.struggle_type,
                activity.search_text,
                activity.embedding_id,
                json.dumps(activity.metadata) if activity.metadata else None
            ))

        logger.debug(f"Stored activity {activity.id}: {activity.title}")
        return activity.id

    async def get_activity(self, activity_id: str) -> Optional[Activity]:
        """Get an activity by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM activities WHERE id = ?",
                (activity_id,)
            ).fetchone()

            if row:
                return self._row_to_activity(row)
        return None

    async def get_activities_by_date(
        self,
        target_date: date,
        activity_types: Optional[List[str]] = None,
        project: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 100
    ) -> List[Activity]:
        """Get activities for a specific date."""
        query = "SELECT * FROM activities WHERE date = ?"
        params: List[Any] = [target_date.isoformat()]

        if activity_types:
            placeholders = ','.join('?' * len(activity_types))
            query += f" AND activity_type IN ({placeholders})"
            params.extend(activity_types)

        if project:
            query += " AND project = ?"
            params.append(project)

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_activity(row) for row in rows]

    async def get_activities_by_range(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> List[Activity]:
        """Get activities within a date range."""
        query = "SELECT * FROM activities WHERE date >= ? AND date <= ?"
        params: List[Any] = [start_date.isoformat(), end_date.isoformat()]

        if kwargs.get('activity_types'):
            placeholders = ','.join('?' * len(kwargs['activity_types']))
            query += f" AND activity_type IN ({placeholders})"
            params.extend(kwargs['activity_types'])

        if kwargs.get('project'):
            query += " AND project = ?"
            params.append(kwargs['project'])

        if kwargs.get('domain'):
            query += " AND domain = ?"
            params.append(kwargs['domain'])

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(kwargs.get('limit', 500))

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_activity(row) for row in rows]

    async def search_activities(
        self,
        query: str,
        limit: int = 20
    ) -> List[Activity]:
        """Search activities using FTS5 full-text search."""
        with self._get_connection() as conn:
            # Use FTS5 for full-text search
            rows = conn.execute("""
                SELECT a.* FROM activities a
                JOIN activities_fts fts ON a.rowid = fts.rowid
                WHERE activities_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit)).fetchall()
            return [self._row_to_activity(row) for row in rows]

    def _row_to_activity(self, row: sqlite3.Row) -> Activity:
        """Convert a database row to an Activity object."""
        return Activity(
            id=row['id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            activity_type=row['activity_type'],
            title=row['title'],
            description=row['description'],
            content=row['content'],
            project=row['project'],
            domain=row['domain'],
            energy_level=row['energy_level'],
            duration_minutes=row['duration_minutes'],
            started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
            ended_at=datetime.fromisoformat(row['ended_at']) if row['ended_at'] else None,
            source=row['source'],
            source_context=json.loads(row['source_context']) if row['source_context'] else None,
            related_task_id=row['related_task_id'],
            related_event_id=row['related_event_id'],
            related_commitment_id=row['related_commitment_id'],
            session_id=row['session_id'],
            sentiment=row['sentiment'],
            struggle_detected=bool(row['struggle_detected']),
            struggle_type=row['struggle_type'],
            search_text=row['search_text'],
            embedding_id=row['embedding_id'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # =========================================================================
    # Struggle Operations
    # =========================================================================

    async def store_struggle(self, struggle: Struggle) -> str:
        """Store a struggle in the database."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO struggles (
                    id, detected_at, struggle_type, title, description, trigger_text,
                    project, domain, related_task_id,
                    time_of_day, day_of_week,
                    resolved, resolved_at, resolution_notes,
                    recurrence_count, last_occurred,
                    confidence, source_activity_id, metadata
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?, ?
                )
            """, (
                struggle.id,
                struggle.detected_at.isoformat(),
                struggle.struggle_type,
                struggle.title,
                struggle.description,
                struggle.trigger_text,
                struggle.project,
                struggle.domain,
                struggle.related_task_id,
                struggle.time_of_day,
                struggle.day_of_week,
                struggle.resolved,
                struggle.resolved_at.isoformat() if struggle.resolved_at else None,
                struggle.resolution_notes,
                struggle.recurrence_count,
                struggle.last_occurred.isoformat() if struggle.last_occurred else None,
                struggle.confidence,
                struggle.source_activity_id,
                json.dumps(struggle.metadata) if struggle.metadata else None
            ))

        logger.debug(f"Stored struggle {struggle.id}: {struggle.title}")
        return struggle.id

    async def get_struggles_by_date(
        self,
        target_date: date,
        struggle_types: Optional[List[str]] = None,
        resolved: Optional[bool] = None,
        limit: int = 50
    ) -> List[Struggle]:
        """Get struggles for a specific date."""
        query = "SELECT * FROM struggles WHERE date = ?"
        params: List[Any] = [target_date.isoformat()]

        if struggle_types:
            placeholders = ','.join('?' * len(struggle_types))
            query += f" AND struggle_type IN ({placeholders})"
            params.extend(struggle_types)

        if resolved is not None:
            query += " AND resolved = ?"
            params.append(resolved)

        query += " ORDER BY detected_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_struggle(row) for row in rows]

    async def get_struggle_patterns(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """Analyze struggle patterns over a time period."""
        start_date = (date.today() - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            # Get struggle counts by type
            type_counts = conn.execute("""
                SELECT struggle_type, COUNT(*) as count
                FROM struggles
                WHERE date >= ?
                GROUP BY struggle_type
                ORDER BY count DESC
            """, (start_date,)).fetchall()

            # Get struggle counts by time of day
            time_counts = conn.execute("""
                SELECT time_of_day, COUNT(*) as count
                FROM struggles
                WHERE date >= ?
                GROUP BY time_of_day
                ORDER BY count DESC
            """, (start_date,)).fetchall()

            # Get struggle counts by day of week
            day_counts = conn.execute("""
                SELECT day_of_week, COUNT(*) as count
                FROM struggles
                WHERE date >= ?
                GROUP BY day_of_week
                ORDER BY day_of_week
            """, (start_date,)).fetchall()

            return {
                'by_type': {row['struggle_type']: row['count'] for row in type_counts},
                'by_time_of_day': {row['time_of_day']: row['count'] for row in time_counts},
                'by_day_of_week': {row['day_of_week']: row['count'] for row in day_counts},
                'period_days': days,
                'total_struggles': sum(row['count'] for row in type_counts)
            }

    async def resolve_struggle(
        self,
        struggle_id: str,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """Mark a struggle as resolved."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE struggles
                SET resolved = TRUE, resolved_at = ?, resolution_notes = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), resolution_notes, struggle_id))
            return cursor.rowcount > 0

    def _row_to_struggle(self, row: sqlite3.Row) -> Struggle:
        """Convert a database row to a Struggle object."""
        return Struggle(
            id=row['id'],
            detected_at=datetime.fromisoformat(row['detected_at']),
            struggle_type=row['struggle_type'],
            title=row['title'],
            description=row['description'],
            trigger_text=row['trigger_text'],
            project=row['project'],
            domain=row['domain'],
            related_task_id=row['related_task_id'],
            time_of_day=row['time_of_day'],
            day_of_week=row['day_of_week'],
            resolved=bool(row['resolved']),
            resolved_at=datetime.fromisoformat(row['resolved_at']) if row['resolved_at'] else None,
            resolution_notes=row['resolution_notes'],
            recurrence_count=row['recurrence_count'],
            last_occurred=datetime.fromisoformat(row['last_occurred']) if row['last_occurred'] else None,
            confidence=row['confidence'],
            source_activity_id=row['source_activity_id'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # =========================================================================
    # Value Operations
    # =========================================================================

    async def store_value(self, value: UserValue) -> str:
        """Store a user value in the database."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_values (
                    id, detected_at, last_reinforced,
                    value_type, title, description,
                    mention_count, emotional_weight, explicit_importance,
                    domain, related_entity,
                    is_active, source_quotes, metadata
                ) VALUES (
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?, ?
                )
            """, (
                value.id,
                value.detected_at.isoformat(),
                value.last_reinforced.isoformat() if value.last_reinforced else None,
                value.value_type,
                value.title,
                value.description,
                value.mention_count,
                value.emotional_weight,
                value.explicit_importance,
                value.domain,
                value.related_entity,
                value.is_active,
                json.dumps(value.source_quotes) if value.source_quotes else None,
                json.dumps(value.metadata) if value.metadata else None
            ))

        logger.debug(f"Stored value {value.id}: {value.title}")
        return value.id

    async def get_active_values(
        self,
        domain: Optional[str] = None,
        value_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[UserValue]:
        """Get active user values."""
        query = "SELECT * FROM user_values WHERE is_active = TRUE"
        params: List[Any] = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if value_types:
            placeholders = ','.join('?' * len(value_types))
            query += f" AND value_type IN ({placeholders})"
            params.extend(value_types)

        query += " ORDER BY emotional_weight DESC, mention_count DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_value(row) for row in rows]

    async def reinforce_value(
        self,
        value_id: str,
        quote: Optional[str] = None
    ) -> bool:
        """Reinforce a value (increment mention count, update timestamp)."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE user_values
                SET mention_count = mention_count + 1,
                    last_reinforced = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), value_id))

            if quote:
                # Add quote to source_quotes array
                row = conn.execute(
                    "SELECT source_quotes FROM user_values WHERE id = ?",
                    (value_id,)
                ).fetchone()
                if row:
                    quotes = json.loads(row['source_quotes'] or '[]')
                    quotes.append(quote)
                    # Keep only last 10 quotes
                    quotes = quotes[-10:]
                    conn.execute(
                        "UPDATE user_values SET source_quotes = ? WHERE id = ?",
                        (json.dumps(quotes), value_id)
                    )

            return cursor.rowcount > 0

    def _row_to_value(self, row: sqlite3.Row) -> UserValue:
        """Convert a database row to a UserValue object."""
        return UserValue(
            id=row['id'],
            detected_at=datetime.fromisoformat(row['detected_at']),
            last_reinforced=datetime.fromisoformat(row['last_reinforced']) if row['last_reinforced'] else None,
            value_type=row['value_type'],
            title=row['title'],
            description=row['description'],
            mention_count=row['mention_count'],
            emotional_weight=row['emotional_weight'],
            explicit_importance=bool(row['explicit_importance']),
            domain=row['domain'],
            related_entity=row['related_entity'],
            is_active=bool(row['is_active']),
            source_quotes=json.loads(row['source_quotes']) if row['source_quotes'] else None,
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # =========================================================================
    # Relationship Operations
    # =========================================================================

    async def update_relationship(
        self,
        entity_name: str,
        entity_type: str,
        domain: Optional[str] = None,
        sentiment: Optional[str] = None,
        commitment_text: Optional[str] = None
    ) -> str:
        """Update or create a relationship entry."""
        with self._get_connection() as conn:
            # Check if relationship exists
            row = conn.execute(
                "SELECT * FROM memory_relationships WHERE entity_name = ?",
                (entity_name,)
            ).fetchone()

            if row:
                # Update existing
                updates = ["mention_count = mention_count + 1", "last_mentioned = ?"]
                params: List[Any] = [datetime.now().isoformat()]

                if sentiment:
                    updates.append("sentiment_trend = ?")
                    params.append(sentiment)

                if commitment_text:
                    commitments = json.loads(row['commitments_to'] or '[]')
                    commitments.append({
                        'text': commitment_text,
                        'made_at': datetime.now().isoformat()
                    })
                    updates.append("commitments_to = ?")
                    params.append(json.dumps(commitments[-10:]))  # Keep last 10

                updates.append("updated_at = ?")
                params.append(datetime.now().isoformat())

                params.append(entity_name)
                conn.execute(
                    f"UPDATE memory_relationships SET {', '.join(updates)} WHERE entity_name = ?",
                    params
                )
                return row['id']
            else:
                # Create new
                rel_id = str(uuid.uuid4())[:12]
                commitments = None
                if commitment_text:
                    commitments = json.dumps([{
                        'text': commitment_text,
                        'made_at': datetime.now().isoformat()
                    }])

                conn.execute("""
                    INSERT INTO memory_relationships (
                        id, entity_name, entity_type, domain,
                        mention_count, last_mentioned, sentiment_trend,
                        commitments_to, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                """, (
                    rel_id,
                    entity_name,
                    entity_type,
                    domain,
                    datetime.now().isoformat(),
                    sentiment,
                    commitments,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                return rel_id

    async def get_relationship(self, entity_name: str) -> Optional[Relationship]:
        """Get a relationship by entity name."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM memory_relationships WHERE entity_name = ?",
                (entity_name,)
            ).fetchone()

            if row:
                return self._row_to_relationship(row)
        return None

    async def get_important_relationships(
        self,
        domain: Optional[str] = None,
        limit: int = 20
    ) -> List[Relationship]:
        """Get important relationships."""
        query = """
            SELECT * FROM memory_relationships
            WHERE importance IN ('critical', 'high')
        """
        params: List[Any] = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        query += " ORDER BY mention_count DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_relationship(row) for row in rows]

    def _row_to_relationship(self, row: sqlite3.Row) -> Relationship:
        """Convert a database row to a Relationship object."""
        return Relationship(
            id=row['id'],
            entity_name=row['entity_name'],
            entity_type=row['entity_type'],
            importance=row['importance'],
            mention_count=row['mention_count'],
            last_mentioned=datetime.fromisoformat(row['last_mentioned']) if row['last_mentioned'] else None,
            company=row['company'],
            role=row['role'],
            domain=row['domain'],
            sentiment_trend=row['sentiment_trend'],
            last_interaction_date=date.fromisoformat(row['last_interaction_date']) if row['last_interaction_date'] else None,
            interaction_frequency=row['interaction_frequency'],
            notes=row['notes'],
            key_facts=json.loads(row['key_facts']) if row['key_facts'] else None,
            commitments_to=json.loads(row['commitments_to']) if row['commitments_to'] else None,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    # =========================================================================
    # Summary Operations
    # =========================================================================

    async def get_day_summary(self, target_date: date) -> Optional[DaySummary]:
        """Get or generate a day summary."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM daily_summaries WHERE date = ?",
                (target_date.isoformat(),)
            ).fetchone()

            if row:
                return self._row_to_day_summary(row)

            # Generate summary if not exists
            return await self._generate_day_summary(target_date)

    async def _generate_day_summary(self, target_date: date) -> Optional[DaySummary]:
        """Generate a day summary from activities."""
        activities = await self.get_activities_by_date(target_date, limit=1000)
        if not activities:
            return None

        # Calculate metrics
        tasks_completed = sum(1 for a in activities if a.activity_type == 'task_complete')
        brain_dumps = sum(1 for a in activities if a.activity_type == 'brain_dump')
        commands = sum(1 for a in activities if a.activity_type == 'command')
        work_activities = sum(1 for a in activities if a.domain == 'work')
        personal_activities = sum(1 for a in activities if a.domain == 'personal')
        struggles = sum(1 for a in activities if a.struggle_detected)

        # Get time range
        timestamps = [a.timestamp for a in activities]
        first_time = min(timestamps).time() if timestamps else None
        last_time = max(timestamps).time() if timestamps else None

        # Get projects
        projects = list(set(a.project for a in activities if a.project))

        # Get struggles for the day
        struggles_list = await self.get_struggles_by_date(target_date)

        summary = DaySummary(
            date=target_date,
            total_activities=len(activities),
            tasks_completed=tasks_completed,
            brain_dumps=brain_dumps,
            commands_executed=commands,
            first_activity_time=first_time,
            last_activity_time=last_time,
            struggles_detected=struggles,
            work_activities=work_activities,
            personal_activities=personal_activities,
            projects_touched=projects if projects else None,
            notable_struggles=[s.to_dict() for s in struggles_list[:3]] if struggles_list else None
        )

        # Store the summary
        await self._store_day_summary(summary)

        return summary

    async def _store_day_summary(self, summary: DaySummary) -> None:
        """Store a day summary."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO daily_summaries (
                    date, total_activities, tasks_completed, tasks_created,
                    brain_dumps, commands_executed,
                    first_activity_time, last_activity_time, total_active_minutes,
                    focus_sessions, focus_minutes, context_switches,
                    struggles_detected, predominant_sentiment, energy_trend,
                    work_activities, personal_activities,
                    projects_touched, key_accomplishments, notable_struggles,
                    oura_readiness, oura_sleep_score, oura_activity_score,
                    generated_summary, user_reflection
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?
                )
            """, (
                summary.date.isoformat(),
                summary.total_activities,
                summary.tasks_completed,
                summary.tasks_created,
                summary.brain_dumps,
                summary.commands_executed,
                summary.first_activity_time.isoformat() if summary.first_activity_time else None,
                summary.last_activity_time.isoformat() if summary.last_activity_time else None,
                summary.total_active_minutes,
                summary.focus_sessions,
                summary.focus_minutes,
                summary.context_switches,
                summary.struggles_detected,
                summary.predominant_sentiment,
                summary.energy_trend,
                summary.work_activities,
                summary.personal_activities,
                json.dumps(summary.projects_touched) if summary.projects_touched else None,
                json.dumps(summary.key_accomplishments) if summary.key_accomplishments else None,
                json.dumps(summary.notable_struggles) if summary.notable_struggles else None,
                summary.oura_readiness,
                summary.oura_sleep_score,
                summary.oura_activity_score,
                summary.generated_summary,
                summary.user_reflection
            ))

    def _row_to_day_summary(self, row: sqlite3.Row) -> DaySummary:
        """Convert a database row to a DaySummary object."""
        return DaySummary(
            date=date.fromisoformat(row['date']),
            total_activities=row['total_activities'],
            tasks_completed=row['tasks_completed'],
            tasks_created=row['tasks_created'] or 0,
            brain_dumps=row['brain_dumps'],
            commands_executed=row['commands_executed'],
            first_activity_time=time.fromisoformat(row['first_activity_time']) if row['first_activity_time'] else None,
            last_activity_time=time.fromisoformat(row['last_activity_time']) if row['last_activity_time'] else None,
            total_active_minutes=row['total_active_minutes'],
            focus_sessions=row['focus_sessions'],
            focus_minutes=row['focus_minutes'],
            context_switches=row['context_switches'],
            struggles_detected=row['struggles_detected'],
            predominant_sentiment=row['predominant_sentiment'],
            energy_trend=row['energy_trend'],
            work_activities=row['work_activities'],
            personal_activities=row['personal_activities'],
            projects_touched=json.loads(row['projects_touched']) if row['projects_touched'] else None,
            key_accomplishments=json.loads(row['key_accomplishments']) if row['key_accomplishments'] else None,
            notable_struggles=json.loads(row['notable_struggles']) if row['notable_struggles'] else None,
            oura_readiness=row['oura_readiness'],
            oura_sleep_score=row['oura_sleep_score'],
            oura_activity_score=row['oura_activity_score'],
            generated_summary=row['generated_summary'],
            user_reflection=row['user_reflection']
        )

    # =========================================================================
    # Statistics and Analytics
    # =========================================================================

    async def get_activity_stats(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get activity statistics for a time period."""
        start_date = (date.today() - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            # Total activities
            total = conn.execute(
                "SELECT COUNT(*) FROM activities WHERE date >= ?",
                (start_date,)
            ).fetchone()[0]

            # By type
            by_type = conn.execute("""
                SELECT activity_type, COUNT(*) as count
                FROM activities WHERE date >= ?
                GROUP BY activity_type
            """, (start_date,)).fetchall()

            # By domain
            by_domain = conn.execute("""
                SELECT domain, COUNT(*) as count
                FROM activities WHERE date >= ? AND domain IS NOT NULL
                GROUP BY domain
            """, (start_date,)).fetchall()

            # By hour (productivity patterns)
            by_hour = conn.execute("""
                SELECT hour, COUNT(*) as count
                FROM activities WHERE date >= ?
                GROUP BY hour ORDER BY hour
            """, (start_date,)).fetchall()

            # By day of week
            by_day = conn.execute("""
                SELECT day_of_week, COUNT(*) as count
                FROM activities WHERE date >= ?
                GROUP BY day_of_week ORDER BY day_of_week
            """, (start_date,)).fetchall()

            # Projects
            projects = conn.execute("""
                SELECT project, COUNT(*) as count
                FROM activities WHERE date >= ? AND project IS NOT NULL
                GROUP BY project ORDER BY count DESC LIMIT 10
            """, (start_date,)).fetchall()

            return {
                'period_days': days,
                'total_activities': total,
                'avg_per_day': round(total / days, 1) if days > 0 else 0,
                'by_type': {row['activity_type']: row['count'] for row in by_type},
                'by_domain': {row['domain']: row['count'] for row in by_domain},
                'by_hour': {row['hour']: row['count'] for row in by_hour},
                'by_day_of_week': {row['day_of_week']: row['count'] for row in by_day},
                'top_projects': {row['project']: row['count'] for row in projects}
            }
