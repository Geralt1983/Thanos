#!/usr/bin/env python3
"""
Relationship Mention Tracker - Track when people are mentioned in conversation.

This module provides SQLite-backed tracking of person mentions to enable:
- Relationship decay detection (who haven't we talked about recently?)
- Importance-based alerting (critical people like family get shorter thresholds)
- Mention frequency analysis
- Proactive relationship maintenance reminders

Designed for ADHD users who may inadvertently neglect important relationships
due to focus on immediate tasks. Part of the commitment tracking system.

Key Classes:
    RelationshipMentionTracker: Core SQLite mention tracking
    ImportanceLevel: Enum of importance levels for people

Usage:
    from Tools.relationship_tracker import RelationshipMentionTracker

    tracker = RelationshipMentionTracker()

    # Record that someone was mentioned
    tracker.record_mention("Ashley")

    # Check who hasn't been mentioned recently
    stale = tracker.get_stale_relationships(threshold_days=5)

    # Set importance level for alerting
    tracker.set_importance("Sullivan", "critical")

    # Get person info
    info = tracker.get_person_info("Ashley")
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any


class ImportanceLevel(str, Enum):
    """Importance levels for people - affects alert thresholds."""
    CRITICAL = "critical"  # Ashley, Sullivan, Mom, Dad - alert after 5 days
    HIGH = "high"          # Close friends, siblings - alert after 7 days
    MEDIUM = "medium"      # Colleagues, extended family - alert after 14 days
    LOW = "low"            # Acquaintances - alert after 30 days


@dataclass
class PersonMention:
    """Record of a person and their mention history."""
    person_name: str
    last_mentioned_at: str  # ISO timestamp
    mention_count: int
    importance_level: str   # ImportanceLevel
    first_mentioned_at: str # ISO timestamp
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: tuple) -> "PersonMention":
        """Create PersonMention from SQLite row."""
        return cls(
            person_name=row[0],
            last_mentioned_at=row[1],
            mention_count=row[2],
            importance_level=row[3],
            first_mentioned_at=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
            created_at=row[6],
            updated_at=row[7],
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'person_name': self.person_name,
            'last_mentioned_at': self.last_mentioned_at,
            'mention_count': self.mention_count,
            'importance_level': self.importance_level,
            'importance': self.importance_level,  # Alias for convenience
            'first_mentioned_at': self.first_mentioned_at,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


class RelationshipMentionTracker:
    """
    SQLite-backed tracker for person mentions in conversation.

    Tracks when people are mentioned to enable proactive relationship
    maintenance alerts. Prevents relationship decay by surfacing when
    important people haven't been discussed recently.

    Attributes:
        db_path: Path to SQLite database file
        conn: SQLite connection
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize RelationshipMentionTracker.

        Args:
            db_path: Path to SQLite database. Defaults to State/relationship_tracker.db
        """
        if db_path is None:
            thanos_dir = Path(__file__).parent.parent
            db_path = thanos_dir / "State" / "relationship_tracker.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        cursor = self.conn.cursor()

        # Person mentions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS person_mentions (
                person_name TEXT PRIMARY KEY,
                last_mentioned_at TEXT NOT NULL,
                mention_count INTEGER DEFAULT 1,
                importance_level TEXT DEFAULT 'medium',
                first_mentioned_at TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Indexes for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_last_mentioned
            ON person_mentions(last_mentioned_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_importance
            ON person_mentions(importance_level)
        """)

        # Mention history table (detailed log)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mention_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_name TEXT NOT NULL,
                mentioned_at TEXT NOT NULL,
                context TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (person_name) REFERENCES person_mentions(person_name)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_person
            ON mention_history(person_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_time
            ON mention_history(mentioned_at)
        """)

        self.conn.commit()

    def record_mention(
        self,
        person: str,
        context: Optional[str] = None,
        importance: Optional[str] = None
    ) -> None:
        """
        Record that a person was mentioned in conversation.

        Args:
            person: Name of the person mentioned
            context: Optional context about the mention
            importance: Optional importance level override
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        # Check if person exists
        cursor.execute(
            "SELECT person_name FROM person_mentions WHERE person_name = ?",
            (person,)
        )
        exists = cursor.fetchone()

        if exists:
            # Update existing record
            cursor.execute("""
                UPDATE person_mentions
                SET last_mentioned_at = ?,
                    mention_count = mention_count + 1,
                    updated_at = ?
                WHERE person_name = ?
            """, (now, now, person))
        else:
            # Create new record
            importance_level = importance or ImportanceLevel.MEDIUM
            cursor.execute("""
                INSERT INTO person_mentions
                (person_name, last_mentioned_at, mention_count, importance_level,
                 first_mentioned_at, metadata, created_at, updated_at)
                VALUES (?, ?, 1, ?, ?, '{}', ?, ?)
            """, (person, now, importance_level, now, now, now))

        # Add to history
        cursor.execute("""
            INSERT INTO mention_history (person_name, mentioned_at, context, created_at)
            VALUES (?, ?, ?, ?)
        """, (person, now, context, now))

        self.conn.commit()

    def get_recent_mentions(self, days: int = 7) -> List[PersonMention]:
        """
        Get people mentioned within the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of PersonMention records
        """
        cursor = self.conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT person_name, last_mentioned_at, mention_count, importance_level,
                   first_mentioned_at, metadata, created_at, updated_at
            FROM person_mentions
            WHERE last_mentioned_at >= ?
            ORDER BY last_mentioned_at DESC
        """, (cutoff,))

        return [PersonMention.from_row(row) for row in cursor.fetchall()]

    def get_stale_relationships(
        self,
        threshold_days: int = 7,
        importance: Optional[str] = None
    ) -> List[PersonMention]:
        """
        Get people who haven't been mentioned in threshold_days.

        Args:
            threshold_days: Days since last mention to consider stale
            importance: Optional filter by importance level

        Returns:
            List of PersonMention records for stale relationships
        """
        cursor = self.conn.cursor()
        cutoff = (datetime.now() - timedelta(days=threshold_days)).isoformat()

        if importance:
            cursor.execute("""
                SELECT person_name, last_mentioned_at, mention_count, importance_level,
                       first_mentioned_at, metadata, created_at, updated_at
                FROM person_mentions
                WHERE last_mentioned_at < ? AND importance_level = ?
                ORDER BY importance_level, last_mentioned_at ASC
            """, (cutoff, importance))
        else:
            cursor.execute("""
                SELECT person_name, last_mentioned_at, mention_count, importance_level,
                       first_mentioned_at, metadata, created_at, updated_at
                FROM person_mentions
                WHERE last_mentioned_at < ?
                ORDER BY importance_level, last_mentioned_at ASC
            """, (cutoff,))

        return [PersonMention.from_row(row) for row in cursor.fetchall()]

    def set_importance(self, person: str, importance) -> None:
        """
        Set importance level for a person.

        Args:
            person: Name of the person
            importance: ImportanceLevel enum or string value (critical, high, medium, low)
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        # Normalize importance input - handle both str and ImportanceLevel enum
        if isinstance(importance, ImportanceLevel):
            importance_str = importance.value
        else:
            importance_str = str(importance)

        # Validate importance level
        ImportanceLevel(importance_str)  # Raises ValueError if invalid

        cursor.execute("""
            UPDATE person_mentions
            SET importance_level = ?, updated_at = ?
            WHERE person_name = ?
        """, (importance_str, now, person))

        # If person doesn't exist, create them
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO person_mentions
                (person_name, last_mentioned_at, mention_count, importance_level,
                 first_mentioned_at, metadata, created_at, updated_at)
                VALUES (?, ?, 0, ?, ?, '{}', ?, ?)
            """, (person, now, importance_str, now, now, now))

        self.conn.commit()

    def get_person_info(self, person: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a person.

        Args:
            person: Name of the person

        Returns:
            Dictionary with person info or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT person_name, last_mentioned_at, mention_count, importance_level,
                   first_mentioned_at, metadata, created_at, updated_at
            FROM person_mentions
            WHERE person_name = ?
        """, (person,))

        row = cursor.fetchone()
        if row:
            mention = PersonMention.from_row(row)
            return mention.to_dict()
        return None

    def get_all_people(self) -> List[PersonMention]:
        """
        Get all tracked people.

        Returns:
            List of all PersonMention records
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT person_name, last_mentioned_at, mention_count, importance_level,
                   first_mentioned_at, metadata, created_at, updated_at
            FROM person_mentions
            ORDER BY importance_level, last_mentioned_at DESC
        """)

        return [PersonMention.from_row(row) for row in cursor.fetchall()]

    def get_mention_history(
        self,
        person: Optional[str] = None,
        days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get detailed mention history.

        Args:
            person: Optional filter by person name
            days: Optional filter to last N days

        Returns:
            List of mention history records
        """
        cursor = self.conn.cursor()

        if person and days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute("""
                SELECT id, person_name, mentioned_at, context, created_at
                FROM mention_history
                WHERE person_name = ? AND mentioned_at >= ?
                ORDER BY mentioned_at DESC
            """, (person, cutoff))
        elif person:
            cursor.execute("""
                SELECT id, person_name, mentioned_at, context, created_at
                FROM mention_history
                WHERE person_name = ?
                ORDER BY mentioned_at DESC
            """, (person,))
        elif days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute("""
                SELECT id, person_name, mentioned_at, context, created_at
                FROM mention_history
                WHERE mentioned_at >= ?
                ORDER BY mentioned_at DESC
            """, (cutoff,))
        else:
            cursor.execute("""
                SELECT id, person_name, mentioned_at, context, created_at
                FROM mention_history
                ORDER BY mentioned_at DESC
                LIMIT 100
            """)

        rows = cursor.fetchall()
        return [
            {
                'id': row[0],
                'person_name': row[1],
                'mentioned_at': row[2],
                'context': row[3],
                'created_at': row[4],
            }
            for row in rows
        ]

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Basic smoke test
    tracker = RelationshipMentionTracker()

    # Test recording mentions
    tracker.record_mention("Ashley", "Discussed weekend plans")
    tracker.record_mention("Sullivan", "Talked about school")

    # Test setting importance
    tracker.set_importance("Ashley", ImportanceLevel.CRITICAL)
    tracker.set_importance("Sullivan", ImportanceLevel.CRITICAL)

    # Test getting info
    ashley_info = tracker.get_person_info("Ashley")
    print(f"Ashley info: {ashley_info}")

    # Test getting recent mentions
    recent = tracker.get_recent_mentions(days=1)
    print(f"Recent mentions (1 day): {len(recent)} people")

    # Test getting stale relationships
    stale = tracker.get_stale_relationships(threshold_days=100)
    print(f"Stale relationships (100 days): {len(stale)} people")

    tracker.close()
    print("\n✓ RelationshipMentionTracker smoke test passed")
