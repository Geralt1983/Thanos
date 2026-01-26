"""
Unified Memory Query Layer for Thanos.

Provides a single interface to query across all 4 memory systems:
1. claude-mem (semantic long-term memory)
2. claude-flow (pattern learning, swarm memory)
3. Local state (activities, struggles, values)
4. WorkOS (tasks, habits, energy, client memory)

This layer federates queries across systems and aggregates results
with relevance scoring and deduplication.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import sqlite3

logger = logging.getLogger(__name__)


@dataclass
class UnifiedMemoryResult:
    """A unified result from any memory system."""
    id: str
    content: str
    source_system: str  # claude-mem, claude-flow, local, workos
    relevance_score: float = 0.0
    timestamp: Optional[datetime] = None

    # Context
    memory_type: Optional[str] = None  # observation, pattern, activity, task, etc.
    project: Optional[str] = None
    domain: Optional[str] = None

    # Metadata
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.timestamp:
            d['timestamp'] = self.timestamp.isoformat()
        return d


@dataclass
class UnifiedQueryResult:
    """Aggregated results from unified memory query."""
    query: str
    results: List[UnifiedMemoryResult] = field(default_factory=list)
    systems_queried: List[str] = field(default_factory=list)
    total_matches: int = 0
    execution_time_ms: float = 0.0

    # Per-system breakdown
    results_by_system: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'query': self.query,
            'results': [r.to_dict() for r in self.results],
            'systems_queried': self.systems_queried,
            'total_matches': self.total_matches,
            'execution_time_ms': self.execution_time_ms,
            'results_by_system': self.results_by_system
        }


class UnifiedMemoryService:
    """
    Unified query interface across all Thanos memory systems.

    Provides:
    - Federated search across claude-mem, claude-flow, local, WorkOS
    - Relevance-scored result aggregation
    - Deduplication across systems
    - System health monitoring
    """

    def __init__(
        self,
        claude_mem_db: Optional[str] = None,
        claude_flow_db: Optional[str] = None,
        swarm_db: Optional[str] = None,
        local_db: Optional[str] = None,
        workos_cache: Optional[str] = None
    ):
        # Database paths
        self.claude_mem_db = claude_mem_db or Path.home() / ".claude-mem" / "claude-mem.db"
        self.claude_flow_db = claude_flow_db or Path.home() / ".claude-flow" / "memory.db"
        self.swarm_db = swarm_db or Path.home() / "Projects" / "Thanos" / ".swarm" / "memory.db"
        self.local_db = local_db or Path.home() / "Projects" / "Thanos" / "Tools" / "State" / "memory.db"
        self.workos_cache = workos_cache or Path.home() / ".thanos-cache" / "workos.db"

        # System availability
        self._systems_available = {}
        self._check_systems()

        logger.info(f"UnifiedMemoryService initialized. Systems: {self._systems_available}")

    def _check_systems(self):
        """Check which memory systems are available."""
        self._systems_available = {
            'claude-mem': Path(self.claude_mem_db).exists(),
            'claude-flow': Path(self.claude_flow_db).exists() or Path(self.swarm_db).exists(),
            'local': Path(self.local_db).exists(),
            'workos': Path(self.workos_cache).exists()
        }

    @property
    def available_systems(self) -> List[str]:
        """Get list of available memory systems."""
        return [k for k, v in self._systems_available.items() if v]

    async def search(
        self,
        query: str,
        systems: Optional[List[str]] = None,
        limit: int = 20,
        time_range: Optional[tuple] = None
    ) -> UnifiedQueryResult:
        """
        Search across all memory systems.

        Args:
            query: Search query (natural language or keywords)
            systems: Specific systems to query (default: all available)
            limit: Maximum results per system
            time_range: Optional (start_date, end_date) filter

        Returns:
            UnifiedQueryResult with aggregated results
        """
        import time
        start_time = time.time()

        target_systems = systems or self.available_systems
        results = []
        results_by_system = {}

        # Query each system in parallel
        tasks = []
        for system in target_systems:
            if system in self._systems_available and self._systems_available[system]:
                tasks.append(self._query_system(system, query, limit, time_range))

        system_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        for system, sys_results in zip(target_systems, system_results):
            if isinstance(sys_results, Exception):
                logger.warning(f"Query failed for {system}: {sys_results}")
                results_by_system[system] = 0
                continue

            results.extend(sys_results)
            results_by_system[system] = len(sys_results)

        # Deduplicate and sort by relevance
        unique_results = self._deduplicate_results(results)
        sorted_results = sorted(unique_results, key=lambda r: r.relevance_score, reverse=True)

        execution_time = (time.time() - start_time) * 1000

        return UnifiedQueryResult(
            query=query,
            results=sorted_results[:limit * 2],  # Allow more results from unified search
            systems_queried=target_systems,
            total_matches=len(sorted_results),
            execution_time_ms=round(execution_time, 2),
            results_by_system=results_by_system
        )

    async def _query_system(
        self,
        system: str,
        query: str,
        limit: int,
        time_range: Optional[tuple]
    ) -> List[UnifiedMemoryResult]:
        """Query a specific memory system."""
        if system == 'claude-mem':
            return await self._query_claude_mem(query, limit, time_range)
        elif system == 'claude-flow':
            return await self._query_claude_flow(query, limit, time_range)
        elif system == 'local':
            return await self._query_local(query, limit, time_range)
        elif system == 'workos':
            return await self._query_workos(query, limit, time_range)
        return []

    async def _query_claude_mem(
        self,
        query: str,
        limit: int,
        time_range: Optional[tuple]
    ) -> List[UnifiedMemoryResult]:
        """Query claude-mem SQLite database."""
        results = []
        try:
            conn = sqlite3.connect(str(self.claude_mem_db))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # FTS5 search on observations
            sql = """
                SELECT o.id, o.title, o.narrative, o.type, o.created_at, o.project
                FROM observations o
                JOIN observations_fts fts ON o.id = fts.rowid
                WHERE observations_fts MATCH ?
                ORDER BY o.created_at_epoch DESC
                LIMIT ?
            """
            cursor.execute(sql, (query, limit))

            for row in cursor.fetchall():
                results.append(UnifiedMemoryResult(
                    id=f"cm-{row['id']}",
                    content=row['narrative'] or row['title'],
                    source_system='claude-mem',
                    relevance_score=0.8,  # Base score for FTS match
                    timestamp=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    memory_type=row['type'],
                    project=row['project'],
                    metadata={'title': row['title']}
                ))

            conn.close()
        except Exception as e:
            logger.warning(f"claude-mem query failed: {e}")

        return results

    async def _query_claude_flow(
        self,
        query: str,
        limit: int,
        time_range: Optional[tuple]
    ) -> List[UnifiedMemoryResult]:
        """Query claude-flow/swarm pattern database."""
        results = []
        try:
            # Query swarm patterns
            if Path(self.swarm_db).exists():
                conn = sqlite3.connect(str(self.swarm_db))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Search patterns
                sql = """
                    SELECT id, type, pattern_data, confidence, created_at
                    FROM patterns
                    WHERE pattern_data LIKE ?
                    ORDER BY confidence DESC, created_at DESC
                    LIMIT ?
                """
                cursor.execute(sql, (f'%{query}%', limit))

                for row in cursor.fetchall():
                    pattern_data = json.loads(row['pattern_data']) if row['pattern_data'] else {}
                    results.append(UnifiedMemoryResult(
                        id=f"cf-{row['id']}",
                        content=pattern_data.get('description', str(pattern_data)),
                        source_system='claude-flow',
                        relevance_score=row['confidence'] or 0.5,
                        timestamp=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                        memory_type='pattern',
                        metadata={'type': row['type'], 'confidence': row['confidence']}
                    ))

                conn.close()
        except Exception as e:
            logger.warning(f"claude-flow query failed: {e}")

        return results

    async def _query_local(
        self,
        query: str,
        limit: int,
        time_range: Optional[tuple]
    ) -> List[UnifiedMemoryResult]:
        """Query local memory database."""
        results = []
        try:
            if Path(self.local_db).exists():
                conn = sqlite3.connect(str(self.local_db))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Search activities
                sql = """
                    SELECT id, timestamp, activity_type, title, content, project, domain
                    FROM activities
                    WHERE title LIKE ? OR content LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """
                cursor.execute(sql, (f'%{query}%', f'%{query}%', limit))

                for row in cursor.fetchall():
                    results.append(UnifiedMemoryResult(
                        id=f"local-{row['id']}",
                        content=row['content'] or row['title'],
                        source_system='local',
                        relevance_score=0.7,
                        timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
                        memory_type=row['activity_type'],
                        project=row['project'],
                        domain=row['domain'],
                        metadata={'title': row['title']}
                    ))

                conn.close()
        except Exception as e:
            logger.warning(f"local query failed: {e}")

        return results

    async def _query_workos(
        self,
        query: str,
        limit: int,
        time_range: Optional[tuple]
    ) -> List[UnifiedMemoryResult]:
        """Query WorkOS cache database."""
        results = []
        try:
            if Path(self.workos_cache).exists():
                conn = sqlite3.connect(str(self.workos_cache))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Search tasks
                sql = """
                    SELECT id, title, description, status, created_at, client_id
                    FROM tasks
                    WHERE title LIKE ? OR description LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """
                cursor.execute(sql, (f'%{query}%', f'%{query}%', limit))

                for row in cursor.fetchall():
                    results.append(UnifiedMemoryResult(
                        id=f"workos-{row['id']}",
                        content=row['description'] or row['title'],
                        source_system='workos',
                        relevance_score=0.75,
                        timestamp=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                        memory_type='task',
                        metadata={'title': row['title'], 'status': row['status']}
                    ))

                conn.close()
        except Exception as e:
            logger.warning(f"workos query failed: {e}")

        return results

    def _deduplicate_results(
        self,
        results: List[UnifiedMemoryResult]
    ) -> List[UnifiedMemoryResult]:
        """Deduplicate results based on content similarity."""
        seen_content = {}
        unique = []

        for r in results:
            # Simple content hash for deduplication
            content_key = r.content[:100].lower().strip() if r.content else r.id

            if content_key not in seen_content:
                seen_content[content_key] = r
                unique.append(r)
            else:
                # Keep the one with higher relevance
                existing = seen_content[content_key]
                if r.relevance_score > existing.relevance_score:
                    unique.remove(existing)
                    unique.append(r)
                    seen_content[content_key] = r

        return unique

    async def get_user_profile_data(self) -> Dict[str, Any]:
        """
        Aggregate user profile data from all systems.

        Returns dict with:
        - patterns: Learned behavioral patterns
        - values: Detected user values
        - struggles: Common struggle types
        - energy_patterns: Energy/productivity correlations
        - relationships: Key relationships
        """
        profile = {
            'patterns': [],
            'values': [],
            'struggles': [],
            'energy_patterns': {},
            'relationships': [],
            'projects': [],
            'stats': {}
        }

        # Query each system for profile data
        try:
            # Local values and struggles
            if Path(self.local_db).exists():
                conn = sqlite3.connect(str(self.local_db))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get values
                cursor.execute("SELECT * FROM user_values WHERE is_active = 1 ORDER BY emotional_weight DESC LIMIT 20")
                for row in cursor.fetchall():
                    profile['values'].append(dict(row))

                # Get struggle patterns
                cursor.execute("""
                    SELECT struggle_type, COUNT(*) as count, AVG(confidence) as avg_confidence
                    FROM struggles
                    GROUP BY struggle_type
                    ORDER BY count DESC
                """)
                for row in cursor.fetchall():
                    profile['struggles'].append(dict(row))

                # Get relationships
                cursor.execute("SELECT * FROM memory_relationships ORDER BY importance DESC LIMIT 20")
                for row in cursor.fetchall():
                    profile['relationships'].append(dict(row))

                conn.close()

            # Claude-flow patterns
            if Path(self.swarm_db).exists():
                conn = sqlite3.connect(str(self.swarm_db))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM patterns ORDER BY confidence DESC LIMIT 30")
                for row in cursor.fetchall():
                    profile['patterns'].append({
                        'id': row['id'],
                        'type': row['type'],
                        'data': json.loads(row['pattern_data']) if row['pattern_data'] else {},
                        'confidence': row['confidence']
                    })

                conn.close()

        except Exception as e:
            logger.warning(f"Profile data aggregation failed: {e}")

        return profile

    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all memory systems."""
        status = {}

        for system, available in self._systems_available.items():
            if not available:
                status[system] = {'available': False, 'size_mb': 0}
                continue

            # Get database sizes
            if system == 'claude-mem':
                path = self.claude_mem_db
            elif system == 'claude-flow':
                path = self.swarm_db
            elif system == 'local':
                path = self.local_db
            elif system == 'workos':
                path = self.workos_cache
            else:
                continue

            size_mb = Path(path).stat().st_size / (1024 * 1024) if Path(path).exists() else 0
            status[system] = {
                'available': True,
                'path': str(path),
                'size_mb': round(size_mb, 2)
            }

        return status


# Singleton instance
_unified_service: Optional[UnifiedMemoryService] = None


def get_unified_memory_service() -> UnifiedMemoryService:
    """Get or create the singleton UnifiedMemoryService."""
    global _unified_service
    if _unified_service is None:
        _unified_service = UnifiedMemoryService()
    return _unified_service
