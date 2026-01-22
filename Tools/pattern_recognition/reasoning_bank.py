"""
ReasoningBank - Central Pattern Aggregator for Thanos.

Aggregates patterns from all memory systems:
- claude-mem observations
- claude-flow learned patterns
- WorkOS task/energy correlations
- Local struggle/value patterns

Provides:
- Pattern confidence scoring
- Cross-system pattern linking
- Pattern evolution tracking
- Hyperbolic embedding support via claude-flow
"""

import asyncio
import logging
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of patterns the ReasoningBank tracks."""
    BEHAVIORAL = "behavioral"       # How user behaves
    TEMPORAL = "temporal"           # Time-based patterns
    ENERGY = "energy"               # Energy/productivity correlations
    STRUGGLE = "struggle"           # Struggle patterns
    SUCCESS = "success"             # What leads to success
    PREFERENCE = "preference"       # User preferences
    RELATIONSHIP = "relationship"   # Interaction patterns
    TASK = "task"                   # Task completion patterns


@dataclass
class UnifiedPattern:
    """A pattern aggregated from multiple systems."""
    id: str
    pattern_type: str
    description: str
    confidence: float = 0.5

    # Source tracking
    source_systems: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    evidence_count: int = 1

    # Temporal
    first_observed: Optional[datetime] = None
    last_observed: Optional[datetime] = None
    observation_count: int = 1

    # Strength metrics
    consistency_score: float = 0.5  # How consistently this pattern appears
    impact_score: float = 0.5       # How much this pattern impacts outcomes

    # Embeddings (for semantic search)
    embedding_id: Optional[str] = None
    hyperbolic_embedding: Optional[List[float]] = None

    # Metadata
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.first_observed:
            d['first_observed'] = self.first_observed.isoformat()
        if self.last_observed:
            d['last_observed'] = self.last_observed.isoformat()
        return d


class ReasoningBank:
    """
    Central pattern aggregator across all Thanos memory systems.

    Consolidates patterns from:
    - claude-mem: Observations, decisions, discoveries
    - claude-flow: Learned task patterns, trajectories
    - WorkOS: Energy-task correlations, client patterns
    - Local: Struggles, values, relationships

    Provides unified pattern access with confidence scoring.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        claude_mem_db: Optional[str] = None,
        swarm_db: Optional[str] = None,
        workos_cache: Optional[str] = None
    ):
        self.db_path = db_path or Path.home() / "Projects" / "Thanos" / "State" / "reasoning_bank.db"
        self.claude_mem_db = claude_mem_db or Path.home() / ".claude-mem" / "claude-mem.db"
        self.swarm_db = swarm_db or Path.home() / "Projects" / "Thanos" / ".swarm" / "memory.db"
        self.workos_cache = workos_cache or Path.home() / ".thanos-cache" / "workos.db"

        self._init_db()
        logger.info("ReasoningBank initialized")

    def _init_db(self):
        """Initialize the ReasoningBank database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS unified_patterns (
                id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                description TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                source_systems TEXT,  -- JSON array
                source_ids TEXT,      -- JSON array
                evidence_count INTEGER DEFAULT 1,
                first_observed TEXT,
                last_observed TEXT,
                observation_count INTEGER DEFAULT 1,
                consistency_score REAL DEFAULT 0.5,
                impact_score REAL DEFAULT 0.5,
                embedding_id TEXT,
                hyperbolic_embedding BLOB,
                metadata TEXT,        -- JSON
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_patterns_type ON unified_patterns(pattern_type);
            CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON unified_patterns(confidence DESC);
            CREATE INDEX IF NOT EXISTS idx_patterns_last_observed ON unified_patterns(last_observed DESC);

            CREATE TABLE IF NOT EXISTS pattern_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_a_id TEXT NOT NULL,
                pattern_b_id TEXT NOT NULL,
                link_type TEXT NOT NULL,  -- supports, contradicts, evolves_into, correlates
                strength REAL DEFAULT 0.5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pattern_a_id) REFERENCES unified_patterns(id),
                FOREIGN KEY (pattern_b_id) REFERENCES unified_patterns(id),
                UNIQUE(pattern_a_id, pattern_b_id, link_type)
            );

            CREATE TABLE IF NOT EXISTS consolidation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT DEFAULT CURRENT_TIMESTAMP,
                patterns_processed INTEGER,
                patterns_merged INTEGER,
                patterns_created INTEGER,
                duration_ms REAL,
                metadata TEXT
            );
        """)

        conn.commit()
        conn.close()

    async def consolidate(self, force: bool = False) -> Dict[str, Any]:
        """
        Consolidate patterns from all source systems.

        This is the main learning loop that:
        1. Extracts patterns from each source system
        2. Matches similar patterns across systems
        3. Merges or creates unified patterns
        4. Updates confidence scores based on evidence

        Args:
            force: Force full reconsolidation (default: incremental)

        Returns:
            Consolidation stats
        """
        import time
        start_time = time.time()

        stats = {
            'patterns_processed': 0,
            'patterns_merged': 0,
            'patterns_created': 0,
            'by_source': {}
        }

        # Extract patterns from each source
        sources = {
            'claude-mem': self._extract_claude_mem_patterns,
            'claude-flow': self._extract_claude_flow_patterns,
            'workos': self._extract_workos_patterns
        }

        all_patterns = []
        for source_name, extractor in sources.items():
            try:
                patterns = await extractor()
                all_patterns.extend(patterns)
                stats['by_source'][source_name] = len(patterns)
                stats['patterns_processed'] += len(patterns)
            except Exception as e:
                logger.warning(f"Failed to extract from {source_name}: {e}")
                stats['by_source'][source_name] = 0

        # Merge and store patterns
        for pattern in all_patterns:
            merged = await self._merge_or_create(pattern)
            if merged:
                stats['patterns_merged'] += 1
            else:
                stats['patterns_created'] += 1

        # Log consolidation run
        duration_ms = (time.time() - start_time) * 1000
        self._log_consolidation(stats, duration_ms)

        stats['duration_ms'] = round(duration_ms, 2)
        return stats

    async def _extract_claude_mem_patterns(self) -> List[UnifiedPattern]:
        """Extract patterns from claude-mem observations."""
        patterns = []

        if not Path(self.claude_mem_db).exists():
            return patterns

        try:
            conn = sqlite3.connect(str(self.claude_mem_db))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Extract decision patterns
            cursor.execute("""
                SELECT id, title, narrative, type, concepts, created_at
                FROM observations
                WHERE type IN ('decision', 'discovery', 'pattern')
                ORDER BY created_at DESC
                LIMIT 100
            """)

            for row in cursor.fetchall():
                concepts = json.loads(row['concepts']) if row['concepts'] else []
                pattern_type = self._map_observation_type(row['type'], concepts)

                patterns.append(UnifiedPattern(
                    id=f"cm-{row['id']}",
                    pattern_type=pattern_type,
                    description=row['narrative'] or row['title'],
                    confidence=0.7,
                    source_systems=['claude-mem'],
                    source_ids=[str(row['id'])],
                    first_observed=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_observed=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    metadata={'title': row['title'], 'concepts': concepts}
                ))

            conn.close()
        except Exception as e:
            logger.warning(f"claude-mem extraction failed: {e}")

        return patterns

    async def _extract_claude_flow_patterns(self) -> List[UnifiedPattern]:
        """Extract patterns from claude-flow swarm memory."""
        patterns = []

        if not Path(self.swarm_db).exists():
            return patterns

        try:
            conn = sqlite3.connect(str(self.swarm_db))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, type, pattern_data, confidence, usage_count, created_at, last_used
                FROM patterns
                ORDER BY confidence DESC
                LIMIT 100
            """)

            for row in cursor.fetchall():
                data = json.loads(row['pattern_data']) if row['pattern_data'] else {}

                patterns.append(UnifiedPattern(
                    id=f"cf-{row['id']}",
                    pattern_type=row['type'] or 'behavioral',
                    description=data.get('description', str(data)),
                    confidence=row['confidence'] or 0.5,
                    source_systems=['claude-flow'],
                    source_ids=[str(row['id'])],
                    observation_count=row['usage_count'] or 1,
                    first_observed=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_observed=datetime.fromisoformat(row['last_used']) if row['last_used'] else None,
                    metadata=data
                ))

            conn.close()
        except Exception as e:
            logger.warning(f"claude-flow extraction failed: {e}")

        return patterns

    async def _extract_workos_patterns(self) -> List[UnifiedPattern]:
        """Extract patterns from WorkOS task/energy data."""
        patterns = []

        if not Path(self.workos_cache).exists():
            return patterns

        try:
            conn = sqlite3.connect(str(self.workos_cache))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Extract task completion patterns
            cursor.execute("""
                SELECT cognitive_load, drain_type, COUNT(*) as count,
                       AVG(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completion_rate
                FROM tasks
                WHERE cognitive_load IS NOT NULL
                GROUP BY cognitive_load, drain_type
                HAVING count > 5
            """)

            for row in cursor.fetchall():
                patterns.append(UnifiedPattern(
                    id=f"wo-task-{row['cognitive_load']}-{row['drain_type']}",
                    pattern_type='task',
                    description=f"Tasks with {row['cognitive_load']} cognitive load and {row['drain_type']} drain: {row['completion_rate']*100:.0f}% completion rate",
                    confidence=min(row['count'] / 20, 1.0),  # More evidence = higher confidence
                    source_systems=['workos'],
                    evidence_count=row['count'],
                    consistency_score=row['completion_rate'],
                    metadata={
                        'cognitive_load': row['cognitive_load'],
                        'drain_type': row['drain_type'],
                        'sample_size': row['count']
                    }
                ))

            conn.close()
        except Exception as e:
            logger.warning(f"workos extraction failed: {e}")

        return patterns

    def _map_observation_type(self, obs_type: str, concepts: List[str]) -> str:
        """Map observation type and concepts to pattern type."""
        if obs_type == 'decision':
            return 'preference'
        if 'pattern' in concepts or 'how-it-works' in concepts:
            return 'behavioral'
        if 'problem-solution' in concepts:
            return 'success'
        if 'gotcha' in concepts:
            return 'struggle'
        return 'behavioral'

    async def _merge_or_create(self, pattern: UnifiedPattern) -> bool:
        """
        Merge pattern with existing or create new.

        Returns True if merged, False if created.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check for existing similar pattern (simple text match for now)
        cursor.execute("""
            SELECT id, confidence, observation_count, source_systems
            FROM unified_patterns
            WHERE pattern_type = ? AND description LIKE ?
            LIMIT 1
        """, (pattern.pattern_type, f'%{pattern.description[:50]}%'))

        existing = cursor.fetchone()

        if existing:
            # Merge: update confidence and evidence
            new_confidence = min((existing[1] + pattern.confidence) / 2 * 1.1, 1.0)
            new_count = existing[2] + 1
            existing_sources = json.loads(existing[3]) if existing[3] else []
            merged_sources = list(set(existing_sources + pattern.source_systems))

            cursor.execute("""
                UPDATE unified_patterns
                SET confidence = ?, observation_count = ?, source_systems = ?,
                    last_observed = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                new_confidence,
                new_count,
                json.dumps(merged_sources),
                datetime.now().isoformat(),
                existing[0]
            ))
            conn.commit()
            conn.close()
            return True

        # Create new pattern
        cursor.execute("""
            INSERT INTO unified_patterns
            (id, pattern_type, description, confidence, source_systems, source_ids,
             evidence_count, first_observed, last_observed, observation_count,
             consistency_score, impact_score, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern.id,
            pattern.pattern_type,
            pattern.description,
            pattern.confidence,
            json.dumps(pattern.source_systems),
            json.dumps(pattern.source_ids),
            pattern.evidence_count,
            pattern.first_observed.isoformat() if pattern.first_observed else None,
            pattern.last_observed.isoformat() if pattern.last_observed else None,
            pattern.observation_count,
            pattern.consistency_score,
            pattern.impact_score,
            json.dumps(pattern.metadata) if pattern.metadata else None
        ))

        conn.commit()
        conn.close()
        return False

    def _log_consolidation(self, stats: Dict[str, Any], duration_ms: float):
        """Log consolidation run."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO consolidation_log
            (patterns_processed, patterns_merged, patterns_created, duration_ms, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            stats['patterns_processed'],
            stats['patterns_merged'],
            stats['patterns_created'],
            duration_ms,
            json.dumps(stats['by_source'])
        ))

        conn.commit()
        conn.close()

    async def search(
        self,
        query: str,
        pattern_types: Optional[List[str]] = None,
        min_confidence: float = 0.3,
        limit: int = 20
    ) -> List[UnifiedPattern]:
        """
        Search patterns by description.

        Args:
            query: Search query
            pattern_types: Filter by pattern types
            min_confidence: Minimum confidence threshold
            limit: Maximum results

        Returns:
            List of matching patterns
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        sql = """
            SELECT * FROM unified_patterns
            WHERE description LIKE ?
            AND confidence >= ?
        """
        params = [f'%{query}%', min_confidence]

        if pattern_types:
            placeholders = ','.join(['?' for _ in pattern_types])
            sql += f" AND pattern_type IN ({placeholders})"
            params.extend(pattern_types)

        sql += " ORDER BY confidence DESC, observation_count DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)

        patterns = []
        for row in cursor.fetchall():
            patterns.append(UnifiedPattern(
                id=row['id'],
                pattern_type=row['pattern_type'],
                description=row['description'],
                confidence=row['confidence'],
                source_systems=json.loads(row['source_systems']) if row['source_systems'] else [],
                source_ids=json.loads(row['source_ids']) if row['source_ids'] else [],
                evidence_count=row['evidence_count'],
                first_observed=datetime.fromisoformat(row['first_observed']) if row['first_observed'] else None,
                last_observed=datetime.fromisoformat(row['last_observed']) if row['last_observed'] else None,
                observation_count=row['observation_count'],
                consistency_score=row['consistency_score'],
                impact_score=row['impact_score'],
                metadata=json.loads(row['metadata']) if row['metadata'] else None
            ))

        conn.close()
        return patterns

    async def get_top_patterns(
        self,
        pattern_type: Optional[str] = None,
        limit: int = 10
    ) -> List[UnifiedPattern]:
        """Get top patterns by confidence."""
        return await self.search(
            query='%',  # Match all
            pattern_types=[pattern_type] if pattern_type else None,
            min_confidence=0.0,
            limit=limit
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get ReasoningBank statistics."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Total patterns
        cursor.execute("SELECT COUNT(*) FROM unified_patterns")
        total = cursor.fetchone()[0]

        # By type
        cursor.execute("""
            SELECT pattern_type, COUNT(*), AVG(confidence)
            FROM unified_patterns
            GROUP BY pattern_type
        """)
        by_type = {row[0]: {'count': row[1], 'avg_confidence': round(row[2], 2)} for row in cursor.fetchall()}

        # Recent consolidations
        cursor.execute("""
            SELECT run_at, patterns_processed, patterns_merged, patterns_created
            FROM consolidation_log
            ORDER BY run_at DESC
            LIMIT 5
        """)
        recent_runs = [dict(zip(['run_at', 'processed', 'merged', 'created'], row)) for row in cursor.fetchall()]

        conn.close()

        return {
            'total_patterns': total,
            'by_type': by_type,
            'recent_consolidations': recent_runs
        }


# Singleton instance
_reasoning_bank: Optional[ReasoningBank] = None


def get_reasoning_bank() -> ReasoningBank:
    """Get or create the singleton ReasoningBank."""
    global _reasoning_bank
    if _reasoning_bank is None:
        _reasoning_bank = ReasoningBank()
    return _reasoning_bank
