#!/usr/bin/env python3
"""
RelationshipStore - SQLite-backed relationship tracking for MemOS.

Provides explicit relationship storage between memories to enable:
- Causal chain tracking (what led to this?)
- Cross-domain correlation (sleep → missed commitment → stress)
- Pattern recognition through relationship analysis
- Proactive insight surfacing

Designed to complement ChromaDB vector search with structured relationships
while maintaining minimal resource overhead on M1 MacBook Air.

Key Classes:
    RelationshipStore: Core SQLite relationship storage
    RelationType: Enum of relationship types
    Relationship: Dataclass for relationship records

Usage:
    from Tools.relationships import RelationshipStore, RelationType

    store = RelationshipStore()

    # Link memories with explicit relationship
    store.link_memories(
        source_id="memory_123",
        target_id="memory_456",
        rel_type=RelationType.CAUSED,
        metadata={"confidence": 0.9}
    )

    # Find what led to a memory
    chain = store.traverse_chain("memory_456", direction="backward")

    # Find all related memories
    related = store.get_related("memory_123", rel_type=RelationType.CAUSED)
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class RelationType(Enum):
    """Types of relationships between memories."""

    # Causal relationships
    CAUSED = "caused"           # A caused B
    PREVENTED = "prevented"     # A prevented B
    ENABLED = "enabled"         # A made B possible

    # Temporal relationships
    PRECEDED = "preceded"       # A happened before B (direct sequence)
    FOLLOWED = "followed"       # A happened after B
    CONCURRENT = "concurrent"   # A and B happened together

    # Semantic relationships
    RELATED_TO = "related_to"   # General semantic relationship
    CONTRADICTS = "contradicts" # A conflicts with B
    SUPPORTS = "supports"       # A provides evidence for B
    ELABORATES = "elaborates"   # A adds detail to B

    # Domain relationships
    BELONGS_TO = "belongs_to"   # A is part of domain/category B
    IMPACTS = "impacts"         # A affects domain B

    # Learning relationships
    LEARNED_FROM = "learned_from"     # Pattern learned from experience
    APPLIED_TO = "applied_to"         # Pattern applied in situation
    INVALIDATED_BY = "invalidated_by" # Pattern disproven by evidence


@dataclass
class Relationship:
    """A relationship between two memories."""

    id: int
    source_id: str           # Source memory ID (ChromaDB ID or observation ID)
    target_id: str           # Target memory ID
    rel_type: RelationType   # Type of relationship
    strength: float          # Relationship strength (0.0-1.0)
    metadata: dict[str, Any] # Additional context
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "Relationship":
        """Create Relationship from SQLite row."""
        return cls(
            id=row[0],
            source_id=row[1],
            target_id=row[2],
            rel_type=RelationType(row[3]),
            strength=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]),
        )


@dataclass
class TraversalResult:
    """Result of a relationship chain traversal."""

    memory_id: str
    depth: int
    path: list[str]              # Memory IDs in order
    relationships: list[Relationship]  # Relationships traversed

    def __repr__(self) -> str:
        return f"TraversalResult(id={self.memory_id}, depth={self.depth}, path_len={len(self.path)})"


class RelationshipStore:
    """
    SQLite-backed relationship storage for cross-memory linking.

    Enables explicit relationship tracking between memories stored in
    ChromaDB, providing graph-like traversal without Neo4j overhead.

    Attributes:
        db_path: Path to SQLite database file
        conn: SQLite connection
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize RelationshipStore.

        Args:
            db_path: Path to SQLite database. Defaults to State/relationships.db
        """
        if db_path is None:
            thanos_dir = Path(__file__).parent.parent
            db_path = thanos_dir / "State" / "relationships.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        cursor = self.conn.cursor()

        # Main relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                rel_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(source_id, target_id, rel_type)
            )
        """)

        # Indexes for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source ON relationships(source_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_target ON relationships(target_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(rel_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strength ON relationships(strength)
        """)

        # Pattern cache for frequently accessed chains
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_key TEXT UNIQUE NOT NULL,
                memory_ids TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                hit_count INTEGER DEFAULT 1,
                last_hit TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Insight log for proactive surfacing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_type TEXT NOT NULL,
                content TEXT NOT NULL,
                source_memories TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                surfaced BOOLEAN DEFAULT FALSE,
                surfaced_at TEXT,
                created_at TEXT NOT NULL
            )
        """)

        self.conn.commit()

    def link_memories(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationType,
        strength: float = 1.0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Relationship:
        """
        Create a relationship between two memories.

        Args:
            source_id: Source memory ID (from ChromaDB or observation ID)
            target_id: Target memory ID
            rel_type: Type of relationship
            strength: Relationship strength (0.0-1.0)
            metadata: Additional context

        Returns:
            Created Relationship object
        """
        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        cursor = self.conn.cursor()

        # Upsert - update if exists, insert if not
        cursor.execute("""
            INSERT INTO relationships (source_id, target_id, rel_type, strength, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id, target_id, rel_type) DO UPDATE SET
                strength = excluded.strength,
                metadata = excluded.metadata,
                updated_at = excluded.updated_at
        """, (source_id, target_id, rel_type.value, strength, metadata_json, now, now))

        self.conn.commit()

        # Return the created/updated relationship
        cursor.execute("""
            SELECT * FROM relationships
            WHERE source_id = ? AND target_id = ? AND rel_type = ?
        """, (source_id, target_id, rel_type.value))

        row = cursor.fetchone()
        return Relationship.from_row(row)

    def get_related(
        self,
        memory_id: str,
        rel_type: Optional[RelationType] = None,
        direction: str = "both",
        min_strength: float = 0.0,
        limit: int = 50,
    ) -> list[Relationship]:
        """
        Get memories related to a given memory.

        Args:
            memory_id: Memory ID to find relations for
            rel_type: Optional filter by relationship type
            direction: "outgoing" (source), "incoming" (target), or "both"
            min_strength: Minimum relationship strength
            limit: Maximum relationships to return

        Returns:
            List of Relationship objects
        """
        cursor = self.conn.cursor()
        relationships = []

        if direction in ("outgoing", "both"):
            query = "SELECT * FROM relationships WHERE source_id = ? AND strength >= ?"
            params: list[Any] = [memory_id, min_strength]

            if rel_type:
                query += " AND rel_type = ?"
                params.append(rel_type.value)

            query += " ORDER BY strength DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            relationships.extend([Relationship.from_row(row) for row in cursor.fetchall()])

        if direction in ("incoming", "both"):
            query = "SELECT * FROM relationships WHERE target_id = ? AND strength >= ?"
            params = [memory_id, min_strength]

            if rel_type:
                query += " AND rel_type = ?"
                params.append(rel_type.value)

            query += " ORDER BY strength DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            relationships.extend([Relationship.from_row(row) for row in cursor.fetchall()])

        return relationships

    def traverse_chain(
        self,
        start_id: str,
        direction: str = "backward",
        rel_types: Optional[list[RelationType]] = None,
        max_depth: int = 10,
        min_strength: float = 0.0,
    ) -> list[TraversalResult]:
        """
        Traverse relationship chains from a starting memory.

        Answers questions like "what led to this?" or "what resulted from this?"

        Args:
            start_id: Starting memory ID
            direction: "backward" (find causes) or "forward" (find effects)
            rel_types: Filter by specific relationship types
            max_depth: Maximum chain depth to traverse
            min_strength: Minimum relationship strength

        Returns:
            List of TraversalResult objects, ordered by depth
        """
        visited: set[str] = set()
        results: list[TraversalResult] = []

        # BFS traversal
        queue: list[tuple[str, int, list[str], list[Relationship]]] = [
            (start_id, 0, [start_id], [])
        ]

        while queue:
            current_id, depth, path, rels = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            # Add result (skip start node)
            if depth > 0:
                results.append(TraversalResult(
                    memory_id=current_id,
                    depth=depth,
                    path=path.copy(),
                    relationships=rels.copy(),
                ))

            # Get next relationships
            dir_filter = "incoming" if direction == "backward" else "outgoing"
            relationships = self.get_related(
                current_id,
                direction=dir_filter,
                min_strength=min_strength,
            )

            # Filter by type if specified
            if rel_types:
                relationships = [r for r in relationships if r.rel_type in rel_types]

            # Add neighbors to queue
            for rel in relationships:
                next_id = rel.source_id if direction == "backward" else rel.target_id
                if next_id not in visited:
                    queue.append((
                        next_id,
                        depth + 1,
                        path + [next_id],
                        rels + [rel],
                    ))

        return sorted(results, key=lambda r: r.depth)

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> list[list[Relationship]]:
        """
        Find all paths between two memories.

        Args:
            source_id: Starting memory ID
            target_id: Ending memory ID
            max_depth: Maximum path length

        Returns:
            List of paths (each path is a list of Relationships)
        """
        paths: list[list[Relationship]] = []

        def dfs(current: str, target: str, path: list[Relationship], visited: set[str]):
            if len(path) > max_depth:
                return

            if current == target and path:
                paths.append(path.copy())
                return

            visited.add(current)

            for rel in self.get_related(current, direction="outgoing"):
                if rel.target_id not in visited:
                    path.append(rel)
                    dfs(rel.target_id, target, path, visited)
                    path.pop()

            visited.remove(current)

        dfs(source_id, target_id, [], set())
        return paths

    def get_correlation_candidates(
        self,
        memory_ids: list[str],
        min_shared_connections: int = 2,
    ) -> list[dict[str, Any]]:
        """
        Find memories that connect multiple input memories.

        Useful for cross-domain correlation discovery.

        Args:
            memory_ids: List of memory IDs to find connections between
            min_shared_connections: Minimum connections to be considered

        Returns:
            List of candidate memories with connection details
        """
        cursor = self.conn.cursor()

        # Find memories connected to multiple input memories
        placeholders = ",".join("?" * len(memory_ids))

        cursor.execute(f"""
            SELECT
                CASE
                    WHEN source_id IN ({placeholders}) THEN target_id
                    ELSE source_id
                END as connected_id,
                COUNT(DISTINCT CASE
                    WHEN source_id IN ({placeholders}) THEN source_id
                    ELSE target_id
                END) as connection_count,
                GROUP_CONCAT(rel_type) as rel_types
            FROM relationships
            WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})
            GROUP BY connected_id
            HAVING connection_count >= ?
            ORDER BY connection_count DESC
        """, memory_ids * 4 + [min_shared_connections])

        results = []
        for row in cursor.fetchall():
            if row[0] not in memory_ids:  # Exclude input memories
                results.append({
                    "memory_id": row[0],
                    "connection_count": row[1],
                    "relationship_types": row[2].split(",") if row[2] else [],
                })

        return results

    def store_insight(
        self,
        insight_type: str,
        content: str,
        source_memories: list[str],
        confidence: float = 0.5,
    ) -> int:
        """
        Store a discovered insight for later surfacing.

        Args:
            insight_type: Type of insight (pattern, correlation, warning, etc.)
            content: Human-readable insight description
            source_memories: Memory IDs that support this insight
            confidence: Confidence level (0.0-1.0)

        Returns:
            Insight ID
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO insights (insight_type, content, source_memories, confidence, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (insight_type, content, json.dumps(source_memories), confidence, now))

        self.conn.commit()
        return cursor.lastrowid

    def get_unsurfaced_insights(
        self,
        min_confidence: float = 0.5,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get insights that haven't been surfaced to the user yet.

        Args:
            min_confidence: Minimum confidence threshold
            limit: Maximum insights to return

        Returns:
            List of insight dictionaries
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT id, insight_type, content, source_memories, confidence, created_at
            FROM insights
            WHERE surfaced = FALSE AND confidence >= ?
            ORDER BY confidence DESC, created_at DESC
            LIMIT ?
        """, (min_confidence, limit))

        insights = []
        for row in cursor.fetchall():
            insights.append({
                "id": row[0],
                "type": row[1],
                "content": row[2],
                "source_memories": json.loads(row[3]),
                "confidence": row[4],
                "created_at": row[5],
            })

        return insights

    def mark_insight_surfaced(self, insight_id: int) -> None:
        """Mark an insight as having been surfaced to the user."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            UPDATE insights SET surfaced = TRUE, surfaced_at = ? WHERE id = ?
        """, (now, insight_id))

        self.conn.commit()

    def get_stats(self) -> dict[str, Any]:
        """Get relationship store statistics."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM relationships")
        total_relationships = cursor.fetchone()[0]

        cursor.execute("""
            SELECT rel_type, COUNT(*) as count
            FROM relationships
            GROUP BY rel_type
            ORDER BY count DESC
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("SELECT COUNT(DISTINCT source_id) + COUNT(DISTINCT target_id) FROM relationships")
        unique_memories = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM insights WHERE surfaced = FALSE")
        pending_insights = cursor.fetchone()[0]

        return {
            "total_relationships": total_relationships,
            "by_type": by_type,
            "unique_memories_linked": unique_memories,
            "pending_insights": pending_insights,
            "db_size_kb": self.db_path.stat().st_size / 1024 if self.db_path.exists() else 0,
        }

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def __enter__(self) -> "RelationshipStore":
        return self

    def __exit__(self, *args) -> None:
        self.close()


# Singleton instance for easy import
_relationship_store: Optional[RelationshipStore] = None


def get_relationship_store() -> RelationshipStore:
    """Get or create the singleton RelationshipStore instance."""
    global _relationship_store
    if _relationship_store is None:
        _relationship_store = RelationshipStore()
    return _relationship_store
