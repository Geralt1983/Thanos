#!/usr/bin/env python3
"""
DEPRECATED: Use Tools.memory_v2 instead.

This module is being replaced by Memory V2 which uses:
- Neon pgvector (cloud PostgreSQL) instead of local ChromaDB
- mem0 for automatic fact extraction
- Heat decay for ADHD-friendly memory surfacing

Migration path:
    # Old (deprecated):
    from Tools.intelligent_memory import get_memory
    memory = get_memory()
    memory.search_memories("query")

    # New (preferred):
    from Tools.memory_v2 import get_memory_service
    service = get_memory_service()
    service.search("query")

See docs/adr/012-memory-v2-voyage-neon-heat.md for details.

---

Intelligent Memory System for Thanos (DEPRECATED).

Captures and organizes memories from conversations automatically:
- Activities: What you did, tasks, conversations, decisions
- Struggles: Blockers, challenges, frustrations
- Values: Priorities, commitments, relationships, goals

Uses hybrid storage:
- SQLite: Structured data with relationships and metadata
- ChromaDB: Vector embeddings for semantic search

Usage:
    from Tools.intelligent_memory import get_memory, MemoryCapture

    # Get memory system
    memory = get_memory()

    # Capture an activity
    memory.capture_activity(
        activity_type="task",
        summary="Completed Q4 financial review",
        details="Reviewed all department budgets and identified 15% savings",
        energy_level="high",
        tags=["finance", "quarterly"]
    )

    # Search memories semantically
    results = memory.search_memories("financial work", memory_type="activities")

    # Get day summary
    summary = memory.get_day_summary()
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict, field
from contextlib import contextmanager
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Data Classes
# =============================================================================

class ActivityType(Enum):
    """Types of activities that can be captured."""
    TASK = "task"
    CONVERSATION = "conversation"
    COMMAND = "command"
    DECISION = "decision"
    MEETING = "meeting"
    REFLECTION = "reflection"
    BREAK = "break"
    LEARNING = "learning"


class EnergyLevel(Enum):
    """Energy levels for activity context."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DEPLETED = "depleted"


class ValueCategory(Enum):
    """Categories of values/things that matter."""
    PRIORITY = "priority"
    COMMITMENT = "commitment"
    RELATIONSHIP = "relationship"
    GOAL = "goal"
    PRINCIPLE = "principle"
    BOUNDARY = "boundary"


class EmotionType(Enum):
    """Emotional states captured from conversations."""
    EXCITED = "excited"
    MOTIVATED = "motivated"
    CALM = "calm"
    ANXIOUS = "anxious"
    FRUSTRATED = "frustrated"
    OVERWHELMED = "overwhelmed"
    ACCOMPLISHED = "accomplished"
    UNCERTAIN = "uncertain"
    GRATEFUL = "grateful"
    STRESSED = "stressed"


@dataclass
class Activity:
    """Represents a captured activity."""
    id: int
    timestamp: str
    activity_type: str
    summary: str
    details: Optional[str]
    duration_minutes: Optional[int]
    energy_level: Optional[str]
    tags: List[str]
    session_id: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class Struggle:
    """Represents a captured struggle or blocker."""
    id: int
    timestamp: str
    description: str
    context: Optional[str]
    resolved: bool
    resolution: Optional[str]
    category: Optional[str] = None
    severity: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class Value:
    """Represents something that matters to the user."""
    id: int
    timestamp: str
    category: str
    description: str
    importance_score: float
    mentions: int
    last_mentioned: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class EmotionalSnapshot:
    """Captures emotional state at a point in time."""
    id: int
    timestamp: str
    emotion: str
    intensity: float  # 0.0 to 1.0
    trigger: Optional[str]
    context: Optional[str]
    session_id: Optional[str] = None


@dataclass
class MemorySearchResult:
    """Result from a memory search."""
    id: str
    memory_type: str
    content: str
    timestamp: str
    similarity: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DaySummary:
    """Summary of a day's activities and state."""
    date: str
    activity_count: int
    activities_by_type: Dict[str, int]
    total_duration_minutes: int
    struggles_count: int
    resolved_struggles: int
    dominant_energy: str
    dominant_emotion: Optional[str]
    key_activities: List[str]
    active_values: List[str]


# =============================================================================
# ChromaDB Integration
# =============================================================================

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    chromadb = None
    Settings = None
    CHROMADB_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False


# =============================================================================
# Memory Storage Class
# =============================================================================

class IntelligentMemory:
    """
    Intelligent memory system for capturing and retrieving life context.

    Combines SQLite for structured storage with ChromaDB for semantic search.
    Automatically extracts patterns from activities, struggles, and values.
    """

    SCHEMA_VERSION = 1
    EMBEDDING_MODEL = "text-embedding-3-small"

    def __init__(
        self,
        db_path: Optional[Path] = None,
        chroma_path: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize the intelligent memory system.

        Args:
            db_path: Path to SQLite database (default: State/thanos_memory.db)
            chroma_path: Path for ChromaDB persistence (default: ~/.claude/Memory/intelligent)
            openai_api_key: OpenAI API key for embeddings
        """
        # SQLite setup
        if db_path is None:
            db_path = Path(__file__).parent.parent / "State" / "thanos_memory.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # ChromaDB setup
        self._chroma_client = None
        self._collections: Dict[str, Any] = {}

        if CHROMADB_AVAILABLE:
            import os
            chroma_path = chroma_path or os.path.expanduser("~/.claude/Memory/intelligent")
            Path(chroma_path).mkdir(parents=True, exist_ok=True)

            try:
                # Try HTTP client first
                self._chroma_client = chromadb.HttpClient(host='localhost', port=8000)
                self._chroma_client.heartbeat()
                logger.info("Connected to ChromaDB server")
            except Exception:
                # Fallback to local persistent
                self._chroma_client = chromadb.Client(Settings(
                    persist_directory=chroma_path,
                    anonymized_telemetry=False
                ))
                logger.info("Using local ChromaDB storage")

        # OpenAI setup for embeddings
        self._openai_client = None
        if OPENAI_AVAILABLE:
            import os
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self._openai_client = OpenAI(api_key=api_key)

        # Initialize database
        self._init_database()
        self._ensure_collections()

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
        """Initialize SQLite schema."""
        with self._get_connection() as conn:
            conn.executescript('''
                -- Schema version tracking
                CREATE TABLE IF NOT EXISTS memory_schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Daily activities
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    activity_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    details TEXT,
                    duration_minutes INTEGER,
                    energy_level TEXT,
                    tags TEXT,
                    session_id TEXT,
                    metadata JSON,
                    embedding_id TEXT
                );

                -- Struggles and blockers
                CREATE TABLE IF NOT EXISTS struggles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    description TEXT NOT NULL,
                    context TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution TEXT,
                    resolved_at DATETIME,
                    category TEXT,
                    severity TEXT DEFAULT 'medium',
                    metadata JSON,
                    embedding_id TEXT
                );

                -- Things that matter (values, priorities, relationships)
                CREATE TABLE IF NOT EXISTS user_values (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    importance_score REAL DEFAULT 0.5,
                    mentions INTEGER DEFAULT 1,
                    last_mentioned DATETIME,
                    metadata JSON,
                    embedding_id TEXT
                );

                -- Emotional snapshots
                CREATE TABLE IF NOT EXISTS emotions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    emotion TEXT NOT NULL,
                    intensity REAL DEFAULT 0.5,
                    trigger TEXT,
                    context TEXT,
                    session_id TEXT,
                    metadata JSON
                );

                -- Memory links (relationships between memories)
                CREATE TABLE IF NOT EXISTS memory_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    source_id INTEGER NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id INTEGER NOT NULL,
                    relationship TEXT NOT NULL,
                    strength REAL DEFAULT 1.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source_type, source_id, target_type, target_id, relationship)
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_activities_timestamp ON activities(timestamp);
                CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(activity_type);
                CREATE INDEX IF NOT EXISTS idx_activities_session ON activities(session_id);
                CREATE INDEX IF NOT EXISTS idx_struggles_timestamp ON struggles(timestamp);
                CREATE INDEX IF NOT EXISTS idx_struggles_resolved ON struggles(resolved);
                CREATE INDEX IF NOT EXISTS idx_values_category ON user_values(category);
                CREATE INDEX IF NOT EXISTS idx_values_importance ON user_values(importance_score);
                CREATE INDEX IF NOT EXISTS idx_emotions_timestamp ON emotions(timestamp);
                CREATE INDEX IF NOT EXISTS idx_emotions_emotion ON emotions(emotion);

                -- Record schema version
                INSERT OR IGNORE INTO memory_schema_version (version) VALUES (1);
            ''')

    def _ensure_collections(self):
        """Ensure ChromaDB collections exist."""
        if not self._chroma_client:
            return

        collection_names = ["activities", "struggles", "values"]
        for name in collection_names:
            try:
                self._collections[name] = self._chroma_client.get_or_create_collection(
                    name=f"memory_{name}",
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                logger.warning(f"Could not create collection {name}: {e}")

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        if not self._openai_client:
            return None

        try:
            response = self._openai_client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    def _store_embedding(
        self,
        collection_name: str,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Store embedding in ChromaDB."""
        if collection_name not in self._collections:
            return False

        embedding = self._generate_embedding(text)
        if not embedding:
            return False

        try:
            # Clean metadata for ChromaDB (only str, int, float, bool)
            clean_metadata = {}
            for k, v in metadata.items():
                if v is None:
                    continue
                elif isinstance(v, (str, int, float, bool)):
                    clean_metadata[k] = v
                elif isinstance(v, (list, dict)):
                    clean_metadata[k] = json.dumps(v)
                else:
                    clean_metadata[k] = str(v)

            self._collections[collection_name].add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[clean_metadata]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            return False

    # =========================================================================
    # Activity Capture
    # =========================================================================

    def capture_activity(
        self,
        activity_type: str,
        summary: str,
        details: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        energy_level: Optional[str] = None,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ) -> int:
        """
        Capture an activity.

        Args:
            activity_type: Type of activity (task, conversation, decision, etc.)
            summary: Brief summary of the activity
            details: Detailed description (optional)
            duration_minutes: How long the activity took (optional)
            energy_level: Energy level during activity (high, medium, low, depleted)
            tags: Tags for categorization (optional)
            session_id: Associated session ID (optional)
            metadata: Additional metadata (optional)
            timestamp: Override timestamp (default: now)

        Returns:
            Activity ID
        """
        tags = tags or []
        metadata = metadata or {}
        timestamp = timestamp or datetime.now()

        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO activities
                (timestamp, activity_type, summary, details, duration_minutes,
                 energy_level, tags, session_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp.isoformat(),
                activity_type,
                summary,
                details,
                duration_minutes,
                energy_level,
                json.dumps(tags),
                session_id,
                json.dumps(metadata)
            ))
            activity_id = cursor.lastrowid

        # Store embedding
        doc_id = f"activity_{activity_id}"
        embed_text = f"{summary}. {details}" if details else summary
        embed_metadata = {
            "activity_type": activity_type,
            "timestamp": timestamp.isoformat(),
            "energy_level": energy_level or "",
            "tags": json.dumps(tags)
        }

        if self._store_embedding("activities", doc_id, embed_text, embed_metadata):
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE activities SET embedding_id = ? WHERE id = ?",
                    (doc_id, activity_id)
                )

        return activity_id

    def get_activity(self, activity_id: int) -> Optional[Activity]:
        """Get activity by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM activities WHERE id = ?", (activity_id,)
            ).fetchone()

            if row:
                return self._row_to_activity(row)
        return None

    def get_activities(
        self,
        activity_type: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        energy_level: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Activity]:
        """Get activities with filters."""
        conditions = []
        params = []

        if activity_type:
            conditions.append("activity_type = ?")
            params.append(activity_type)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since.isoformat())
        if until:
            conditions.append("timestamp <= ?")
            params.append(until.isoformat())
        if energy_level:
            conditions.append("energy_level = ?")
            params.append(energy_level)
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self._get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM activities WHERE {where_clause} ORDER BY timestamp DESC LIMIT ?",
                params + [limit]
            ).fetchall()

            return [self._row_to_activity(row) for row in rows]

    def _row_to_activity(self, row: sqlite3.Row) -> Activity:
        """Convert row to Activity."""
        return Activity(
            id=row["id"],
            timestamp=row["timestamp"],
            activity_type=row["activity_type"],
            summary=row["summary"],
            details=row["details"],
            duration_minutes=row["duration_minutes"],
            energy_level=row["energy_level"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            session_id=row["session_id"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None
        )

    # =========================================================================
    # Struggle Capture
    # =========================================================================

    def capture_struggle(
        self,
        description: str,
        context: Optional[str] = None,
        category: Optional[str] = None,
        severity: str = "medium",
        metadata: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ) -> int:
        """
        Capture a struggle or blocker.

        Args:
            description: What the struggle is about
            context: Additional context (optional)
            category: Category (technical, emotional, resource, etc.)
            severity: Severity level (low, medium, high, critical)
            metadata: Additional metadata (optional)
            timestamp: Override timestamp (default: now)

        Returns:
            Struggle ID
        """
        metadata = metadata or {}
        timestamp = timestamp or datetime.now()

        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO struggles
                (timestamp, description, context, category, severity, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                timestamp.isoformat(),
                description,
                context,
                category,
                severity,
                json.dumps(metadata)
            ))
            struggle_id = cursor.lastrowid

        # Store embedding
        doc_id = f"struggle_{struggle_id}"
        embed_text = f"{description}. {context}" if context else description
        embed_metadata = {
            "timestamp": timestamp.isoformat(),
            "category": category or "",
            "severity": severity,
            "resolved": False
        }

        if self._store_embedding("struggles", doc_id, embed_text, embed_metadata):
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE struggles SET embedding_id = ? WHERE id = ?",
                    (doc_id, struggle_id)
                )

        return struggle_id

    def resolve_struggle(
        self,
        struggle_id: int,
        resolution: str
    ) -> bool:
        """
        Mark a struggle as resolved.

        Args:
            struggle_id: Struggle ID to resolve
            resolution: How it was resolved

        Returns:
            True if resolved
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute('''
                UPDATE struggles
                SET resolved = TRUE, resolution = ?, resolved_at = ?
                WHERE id = ?
            ''', (resolution, now, struggle_id))
            return cursor.rowcount > 0

    def get_struggles(
        self,
        resolved: Optional[bool] = None,
        category: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Struggle]:
        """Get struggles with filters."""
        conditions = []
        params = []

        if resolved is not None:
            conditions.append("resolved = ?")
            params.append(resolved)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since.isoformat())

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self._get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM struggles WHERE {where_clause} ORDER BY timestamp DESC LIMIT ?",
                params + [limit]
            ).fetchall()

            return [self._row_to_struggle(row) for row in rows]

    def _row_to_struggle(self, row: sqlite3.Row) -> Struggle:
        """Convert row to Struggle."""
        return Struggle(
            id=row["id"],
            timestamp=row["timestamp"],
            description=row["description"],
            context=row["context"],
            resolved=bool(row["resolved"]),
            resolution=row["resolution"],
            category=row["category"],
            severity=row["severity"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None
        )

    # =========================================================================
    # Value Capture
    # =========================================================================

    def capture_value(
        self,
        category: str,
        description: str,
        importance_score: float = 0.5,
        metadata: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ) -> int:
        """
        Capture something that matters (value, priority, relationship, goal).

        If a similar value already exists, increments the mention count instead.

        Args:
            category: Category (priority, commitment, relationship, goal, principle, boundary)
            description: Description of the value
            importance_score: Importance score (0.0 to 1.0)
            metadata: Additional metadata (optional)
            timestamp: Override timestamp (default: now)

        Returns:
            Value ID
        """
        metadata = metadata or {}
        timestamp = timestamp or datetime.now()

        # Check for existing similar value
        existing = self._find_similar_value(category, description)

        if existing:
            # Update existing value
            with self._get_connection() as conn:
                conn.execute('''
                    UPDATE user_values
                    SET mentions = mentions + 1,
                        last_mentioned = ?,
                        importance_score = MAX(importance_score, ?)
                    WHERE id = ?
                ''', (timestamp.isoformat(), importance_score, existing["id"]))
                return existing["id"]

        # Create new value
        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO user_values
                (timestamp, category, description, importance_score, mentions, last_mentioned, metadata)
                VALUES (?, ?, ?, ?, 1, ?, ?)
            ''', (
                timestamp.isoformat(),
                category,
                description,
                importance_score,
                timestamp.isoformat(),
                json.dumps(metadata)
            ))
            value_id = cursor.lastrowid

        # Store embedding
        doc_id = f"value_{value_id}"
        embed_metadata = {
            "category": category,
            "timestamp": timestamp.isoformat(),
            "importance_score": importance_score
        }

        if self._store_embedding("values", doc_id, description, embed_metadata):
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE user_values SET embedding_id = ? WHERE id = ?",
                    (doc_id, value_id)
                )

        return value_id

    def _find_similar_value(self, category: str, description: str) -> Optional[Dict]:
        """Find existing similar value using semantic search."""
        if "values" not in self._collections or not self._openai_client:
            # Fall back to exact match
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM user_values WHERE category = ? AND description = ?",
                    (category, description)
                ).fetchone()
                return {"id": row["id"]} if row else None

        # Use semantic search
        embedding = self._generate_embedding(description)
        if not embedding:
            return None

        try:
            results = self._collections["values"].query(
                query_embeddings=[embedding],
                n_results=1,
                where={"category": category}
            )

            if results["distances"] and results["distances"][0]:
                # Check if similarity is high enough (distance < 0.3 = >70% similar)
                if results["distances"][0][0] < 0.3:
                    doc_id = results["ids"][0][0]
                    value_id = int(doc_id.split("_")[1])
                    return {"id": value_id}
        except Exception as e:
            logger.warning(f"Semantic value search failed: {e}")

        return None

    def get_priorities(self, limit: int = 10) -> List[Value]:
        """Get top priorities sorted by importance."""
        return self.get_values(category="priority", sort_by="importance", limit=limit)

    def get_values(
        self,
        category: Optional[str] = None,
        min_importance: float = 0.0,
        sort_by: str = "mentions",
        limit: int = 20
    ) -> List[Value]:
        """Get values with filters."""
        conditions = ["importance_score >= ?"]
        params: List[Any] = [min_importance]

        if category:
            conditions.append("category = ?")
            params.append(category)

        where_clause = " AND ".join(conditions)

        order_by = "mentions DESC" if sort_by == "mentions" else "importance_score DESC"

        with self._get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM user_values WHERE {where_clause} ORDER BY {order_by} LIMIT ?",
                params + [limit]
            ).fetchall()

            return [self._row_to_value(row) for row in rows]

    def _row_to_value(self, row: sqlite3.Row) -> Value:
        """Convert row to Value."""
        return Value(
            id=row["id"],
            timestamp=row["timestamp"],
            category=row["category"],
            description=row["description"],
            importance_score=row["importance_score"],
            mentions=row["mentions"],
            last_mentioned=row["last_mentioned"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None
        )

    # =========================================================================
    # Emotion Capture
    # =========================================================================

    def capture_emotion(
        self,
        emotion: str,
        intensity: float = 0.5,
        trigger: Optional[str] = None,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> int:
        """
        Capture an emotional snapshot.

        Args:
            emotion: The emotion being felt
            intensity: Intensity (0.0 to 1.0)
            trigger: What triggered this emotion (optional)
            context: Additional context (optional)
            session_id: Associated session ID (optional)
            timestamp: Override timestamp (default: now)

        Returns:
            Emotion snapshot ID
        """
        timestamp = timestamp or datetime.now()

        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO emotions
                (timestamp, emotion, intensity, trigger, context, session_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                timestamp.isoformat(),
                emotion,
                intensity,
                trigger,
                context,
                session_id
            ))
            return cursor.lastrowid

    def get_recent_emotions(
        self,
        hours: int = 24,
        limit: int = 10
    ) -> List[EmotionalSnapshot]:
        """Get recent emotional snapshots."""
        since = datetime.now() - timedelta(hours=hours)

        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM emotions
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (since.isoformat(), limit)).fetchall()

            return [self._row_to_emotion(row) for row in rows]

    def _row_to_emotion(self, row: sqlite3.Row) -> EmotionalSnapshot:
        """Convert row to EmotionalSnapshot."""
        return EmotionalSnapshot(
            id=row["id"],
            timestamp=row["timestamp"],
            emotion=row["emotion"],
            intensity=row["intensity"],
            trigger=row["trigger"],
            context=row["context"],
            session_id=row["session_id"]
        )

    # =========================================================================
    # Memory Search
    # =========================================================================

    def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        limit: int = 10
    ) -> List[MemorySearchResult]:
        """
        Search memories semantically.

        Args:
            query: Natural language search query
            memory_type: Filter by type (activities, struggles, values) or None for all
            time_range: Optional (start, end) datetime tuple
            limit: Maximum results

        Returns:
            List of search results with similarity scores
        """
        results: List[MemorySearchResult] = []

        if not self._openai_client:
            logger.warning("Semantic search unavailable - no OpenAI client")
            return results

        embedding = self._generate_embedding(query)
        if not embedding:
            return results

        # Determine which collections to search
        collections_to_search = []
        if memory_type:
            if memory_type in self._collections:
                collections_to_search.append((memory_type, self._collections[memory_type]))
        else:
            collections_to_search = list(self._collections.items())

        # Build time filter if provided
        where_filter = None
        if time_range:
            start, end = time_range
            # ChromaDB where filter for timestamp range
            where_filter = {
                "$and": [
                    {"timestamp": {"$gte": start.isoformat()}},
                    {"timestamp": {"$lte": end.isoformat()}}
                ]
            }

        # Search each collection
        for collection_name, collection in collections_to_search:
            try:
                query_kwargs = {
                    "query_embeddings": [embedding],
                    "n_results": limit
                }
                if where_filter:
                    query_kwargs["where"] = where_filter

                search_results = collection.query(**query_kwargs)

                if search_results["ids"] and search_results["ids"][0]:
                    for i, doc_id in enumerate(search_results["ids"][0]):
                        results.append(MemorySearchResult(
                            id=doc_id,
                            memory_type=collection_name,
                            content=search_results["documents"][0][i],
                            timestamp=search_results["metadatas"][0][i].get("timestamp", ""),
                            similarity=1 - search_results["distances"][0][i],
                            metadata=search_results["metadatas"][0][i]
                        ))
            except Exception as e:
                logger.warning(f"Search failed for {collection_name}: {e}")

        # Sort by similarity
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:limit]

    # =========================================================================
    # Day Summary
    # =========================================================================

    def get_day_summary(self, target_date: Optional[date] = None) -> DaySummary:
        """
        Get a summary of activities and state for a specific day.

        Args:
            target_date: Date to summarize (default: today)

        Returns:
            DaySummary with aggregated data
        """
        target_date = target_date or date.today()
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())

        with self._get_connection() as conn:
            # Get activities
            activities = conn.execute('''
                SELECT activity_type, summary, duration_minutes, energy_level
                FROM activities
                WHERE timestamp BETWEEN ? AND ?
            ''', (day_start.isoformat(), day_end.isoformat())).fetchall()

            # Aggregate activity data
            activity_count = len(activities)
            activities_by_type: Dict[str, int] = {}
            total_duration = 0
            energy_levels: Dict[str, int] = {}
            key_activities: List[str] = []

            for act in activities:
                act_type = act["activity_type"]
                activities_by_type[act_type] = activities_by_type.get(act_type, 0) + 1

                if act["duration_minutes"]:
                    total_duration += act["duration_minutes"]

                if act["energy_level"]:
                    energy_levels[act["energy_level"]] = energy_levels.get(act["energy_level"], 0) + 1

                key_activities.append(act["summary"])

            # Get struggles
            struggles = conn.execute('''
                SELECT resolved FROM struggles
                WHERE timestamp BETWEEN ? AND ?
            ''', (day_start.isoformat(), day_end.isoformat())).fetchall()

            struggles_count = len(struggles)
            resolved_count = sum(1 for s in struggles if s["resolved"])

            # Get emotions
            emotions = conn.execute('''
                SELECT emotion, intensity FROM emotions
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY intensity DESC
            ''', (day_start.isoformat(), day_end.isoformat())).fetchall()

            dominant_emotion = emotions[0]["emotion"] if emotions else None

            # Get active values (recently mentioned)
            values = conn.execute('''
                SELECT description FROM user_values
                WHERE last_mentioned BETWEEN ? AND ?
                ORDER BY importance_score DESC
                LIMIT 5
            ''', (day_start.isoformat(), day_end.isoformat())).fetchall()

            active_values = [v["description"] for v in values]

            # Determine dominant energy
            dominant_energy = "medium"
            if energy_levels:
                dominant_energy = max(energy_levels.items(), key=lambda x: x[1])[0]

        return DaySummary(
            date=target_date.isoformat(),
            activity_count=activity_count,
            activities_by_type=activities_by_type,
            total_duration_minutes=total_duration,
            struggles_count=struggles_count,
            resolved_struggles=resolved_count,
            dominant_energy=dominant_energy,
            dominant_emotion=dominant_emotion,
            key_activities=key_activities[:10],  # Top 10
            active_values=active_values
        )

    # =========================================================================
    # Memory Links
    # =========================================================================

    def link_memories(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        relationship: str,
        strength: float = 1.0
    ) -> bool:
        """
        Create a link between two memories.

        Args:
            source_type: Type of source memory (activities, struggles, values)
            source_id: Source memory ID
            target_type: Type of target memory
            target_id: Target memory ID
            relationship: Type of relationship (caused, resolved, supports, etc.)
            strength: Strength of the relationship (0.0 to 1.0)

        Returns:
            True if link created
        """
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO memory_links
                    (source_type, source_id, target_type, target_id, relationship, strength)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (source_type, source_id, target_type, target_id, relationship, strength))
                return True
        except Exception as e:
            logger.error(f"Failed to create memory link: {e}")
            return False

    def get_linked_memories(
        self,
        memory_type: str,
        memory_id: int,
        relationship: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get memories linked to a specific memory."""
        conditions = ["(source_type = ? AND source_id = ?) OR (target_type = ? AND target_id = ?)"]
        params: List[Any] = [memory_type, memory_id, memory_type, memory_id]

        if relationship:
            conditions.append("relationship = ?")
            params.append(relationship)

        where_clause = " AND ".join(conditions)

        with self._get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM memory_links WHERE {where_clause}",
                params
            ).fetchall()

            return [dict(row) for row in rows]

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get overall memory statistics."""
        with self._get_connection() as conn:
            stats = {}

            # Activity stats
            stats["total_activities"] = conn.execute(
                "SELECT COUNT(*) FROM activities"
            ).fetchone()[0]

            stats["activities_today"] = conn.execute('''
                SELECT COUNT(*) FROM activities
                WHERE date(timestamp) = date('now')
            ''').fetchone()[0]

            # Struggle stats
            stats["total_struggles"] = conn.execute(
                "SELECT COUNT(*) FROM struggles"
            ).fetchone()[0]

            stats["unresolved_struggles"] = conn.execute(
                "SELECT COUNT(*) FROM struggles WHERE resolved = FALSE"
            ).fetchone()[0]

            # Value stats
            stats["total_values"] = conn.execute(
                "SELECT COUNT(*) FROM user_values"
            ).fetchone()[0]

            stats["high_priority_values"] = conn.execute(
                "SELECT COUNT(*) FROM user_values WHERE importance_score >= 0.7"
            ).fetchone()[0]

            # Emotion stats
            stats["emotions_today"] = conn.execute('''
                SELECT COUNT(*) FROM emotions
                WHERE date(timestamp) = date('now')
            ''').fetchone()[0]

            # ChromaDB stats
            stats["vector_collections"] = len(self._collections)
            stats["embeddings_available"] = self._openai_client is not None

            return stats

    @property
    def status(self) -> Dict[str, Any]:
        """Get memory system status."""
        return {
            "sqlite": "connected",
            "sqlite_path": str(self.db_path),
            "chromadb": "connected" if self._chroma_client else "unavailable",
            "embeddings": "available" if self._openai_client else "unavailable",
            "collections": list(self._collections.keys()),
            "stats": self.get_stats()
        }


# =============================================================================
# Memory Capture Class (Conversation Hook)
# =============================================================================

class MemoryCapture:
    """
    Hooks into conversation flow to automatically extract memories.

    Analyzes messages for:
    - Activities mentioned
    - Struggles expressed
    - Values revealed
    - Emotions detected
    """

    # Keywords indicating different memory types
    ACTIVITY_KEYWORDS = [
        "completed", "finished", "did", "worked on", "met with",
        "decided", "chose", "started", "created", "sent", "reviewed"
    ]

    STRUGGLE_KEYWORDS = [
        "struggling", "stuck", "blocked", "frustrated", "can't",
        "difficult", "problem", "issue", "challenge", "worried"
    ]

    VALUE_KEYWORDS = [
        "important", "priority", "matters", "care about", "need to",
        "committed", "promised", "goal", "must", "should"
    ]

    EMOTION_MAP = {
        "excited": ["excited", "thrilled", "pumped", "eager"],
        "motivated": ["motivated", "inspired", "energized", "determined"],
        "frustrated": ["frustrated", "annoyed", "irritated", "bothered"],
        "anxious": ["anxious", "worried", "nervous", "concerned"],
        "overwhelmed": ["overwhelmed", "swamped", "drowning", "buried"],
        "accomplished": ["accomplished", "proud", "satisfied", "pleased"],
        "stressed": ["stressed", "tense", "pressured", "under pressure"],
        "grateful": ["grateful", "thankful", "appreciative"]
    }

    def __init__(self, memory: Optional[IntelligentMemory] = None):
        """
        Initialize the memory capture system.

        Args:
            memory: IntelligentMemory instance (default: singleton)
        """
        self.memory = memory or get_memory()
        self._current_session_id: Optional[str] = None

    def set_session(self, session_id: str):
        """Set the current session ID for captured memories."""
        self._current_session_id = session_id

    def process_message(
        self,
        content: str,
        role: str = "user",
        context: Optional[Dict] = None
    ) -> Dict[str, List[int]]:
        """
        Process a message and extract memories.

        Args:
            content: Message content
            role: Message role (user or assistant)
            context: Additional context (optional)

        Returns:
            Dict of captured memory IDs by type
        """
        captured = {
            "activities": [],
            "struggles": [],
            "values": [],
            "emotions": []
        }

        content_lower = content.lower()

        # Only process user messages for personal memories
        if role != "user":
            return captured

        # Check for activities
        for keyword in self.ACTIVITY_KEYWORDS:
            if keyword in content_lower:
                # Found activity indicator - extract and capture
                activity_id = self.memory.capture_activity(
                    activity_type="conversation",
                    summary=content[:200],  # Truncate for summary
                    details=content if len(content) > 200 else None,
                    session_id=self._current_session_id,
                    metadata={"extracted_from": "conversation", "keyword": keyword}
                )
                captured["activities"].append(activity_id)
                break  # Only capture once per message

        # Check for struggles
        for keyword in self.STRUGGLE_KEYWORDS:
            if keyword in content_lower:
                struggle_id = self.memory.capture_struggle(
                    description=content[:300],
                    context=context.get("previous_message") if context else None,
                    category="conversation",
                    metadata={"extracted_from": "conversation", "keyword": keyword}
                )
                captured["struggles"].append(struggle_id)
                break

        # Check for values
        for keyword in self.VALUE_KEYWORDS:
            if keyword in content_lower:
                # Determine category
                category = "priority"
                if "committed" in content_lower or "promised" in content_lower:
                    category = "commitment"
                elif "goal" in content_lower:
                    category = "goal"

                value_id = self.memory.capture_value(
                    category=category,
                    description=content[:200],
                    importance_score=0.6,  # Default moderate importance
                    metadata={"extracted_from": "conversation", "keyword": keyword}
                )
                captured["values"].append(value_id)
                break

        # Check for emotions
        detected_emotion = None
        detected_intensity = 0.5

        for emotion, keywords in self.EMOTION_MAP.items():
            for keyword in keywords:
                if keyword in content_lower:
                    detected_emotion = emotion
                    # Higher intensity for explicit emotion words
                    detected_intensity = 0.7
                    break
            if detected_emotion:
                break

        if detected_emotion:
            emotion_id = self.memory.capture_emotion(
                emotion=detected_emotion,
                intensity=detected_intensity,
                trigger=content[:100],
                session_id=self._current_session_id
            )
            captured["emotions"].append(emotion_id)

        return captured

    def get_session_context(self) -> Dict[str, Any]:
        """
        Get memory context for the current session.

        Returns context useful for personalized responses:
        - Recent struggles (to be empathetic)
        - Active priorities (to stay focused)
        - Emotional state (to adapt tone)
        """
        context = {
            "unresolved_struggles": [],
            "active_priorities": [],
            "recent_emotion": None,
            "today_activities": []
        }

        # Get unresolved struggles
        struggles = self.memory.get_struggles(resolved=False, limit=3)
        context["unresolved_struggles"] = [s.description[:100] for s in struggles]

        # Get top priorities
        priorities = self.memory.get_priorities(limit=3)
        context["active_priorities"] = [p.description[:100] for p in priorities]

        # Get recent emotion
        emotions = self.memory.get_recent_emotions(hours=4, limit=1)
        if emotions:
            context["recent_emotion"] = {
                "emotion": emotions[0].emotion,
                "intensity": emotions[0].intensity
            }

        # Get today's activities
        today_start = datetime.combine(date.today(), datetime.min.time())
        activities = self.memory.get_activities(since=today_start, limit=5)
        context["today_activities"] = [a.summary[:100] for a in activities]

        return context


# =============================================================================
# Singleton Instance
# =============================================================================

_memory_instance: Optional[IntelligentMemory] = None
_capture_instance: Optional[MemoryCapture] = None


def get_memory(db_path: Optional[Path] = None) -> IntelligentMemory:
    """Get or create singleton IntelligentMemory instance."""
    global _memory_instance

    if _memory_instance is None or db_path is not None:
        _memory_instance = IntelligentMemory(db_path=db_path)

    return _memory_instance


def get_capture() -> MemoryCapture:
    """Get or create singleton MemoryCapture instance."""
    global _capture_instance

    if _capture_instance is None:
        _capture_instance = MemoryCapture()

    return _capture_instance


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio

    print("Intelligent Memory System Test")
    print("=" * 60)

    # Initialize
    memory = get_memory()
    print(f"\nStatus: {memory.status}")

    # Test activity capture
    activity_id = memory.capture_activity(
        activity_type="task",
        summary="Reviewed Q4 financial reports",
        details="Analyzed budget variances and identified $50k in savings opportunities",
        energy_level="high",
        tags=["finance", "quarterly-review"]
    )
    print(f"\nCaptured activity: {activity_id}")

    # Test struggle capture
    struggle_id = memory.capture_struggle(
        description="Struggling to find time for deep work",
        context="Too many meetings fragmenting the day",
        category="productivity",
        severity="medium"
    )
    print(f"Captured struggle: {struggle_id}")

    # Test value capture
    value_id = memory.capture_value(
        category="priority",
        description="Protecting morning focus time for important work",
        importance_score=0.8
    )
    print(f"Captured value: {value_id}")

    # Test emotion capture
    emotion_id = memory.capture_emotion(
        emotion="motivated",
        intensity=0.7,
        trigger="Good progress on quarterly goals"
    )
    print(f"Captured emotion: {emotion_id}")

    # Test day summary
    summary = memory.get_day_summary()
    print(f"\nDay Summary:")
    print(f"  Activities: {summary.activity_count}")
    print(f"  Struggles: {summary.struggles_count} ({summary.resolved_struggles} resolved)")
    print(f"  Dominant energy: {summary.dominant_energy}")
    print(f"  Dominant emotion: {summary.dominant_emotion}")

    # Test search
    results = memory.search_memories("financial work")
    print(f"\nSearch results for 'financial work': {len(results)}")
    for r in results[:3]:
        print(f"  - [{r.memory_type}] {r.content[:50]}... (similarity: {r.similarity:.2f})")

    # Test memory capture from conversation
    capture = get_capture()
    captured = capture.process_message(
        "I finally completed the budget analysis I've been struggling with. Feeling accomplished!"
    )
    print(f"\nExtracted from conversation: {captured}")

    # Get session context
    context = capture.get_session_context()
    print(f"\nSession context:")
    print(f"  Unresolved struggles: {len(context['unresolved_struggles'])}")
    print(f"  Active priorities: {len(context['active_priorities'])}")
    print(f"  Recent emotion: {context['recent_emotion']}")

    print("\n" + "=" * 60)
    print("Intelligent Memory System initialized successfully!")
