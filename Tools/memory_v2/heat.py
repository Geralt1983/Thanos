"""
Heat Decay Service for Thanos Memory V2.

Implements heat-based memory decay for ADHD support:
- Recent memories have higher heat
- Accessed memories get boosted
- Cold memories surface via "what am I forgetting?"
- Critical memories can be pinned (never decay)

Heat Score:
- Range: 0.05 (floor) to 2.0 (ceiling)
- New memories: 1.0
- Daily decay: heat *= 0.97
- Access boost: heat += 0.15
- Mention boost: heat += 0.10
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import NEON_DATABASE_URL, HEAT_CONFIG

logger = logging.getLogger(__name__)


class HeatService:
    """Manages heat scores for memory decay.

    Note: After migration to thanos_memories, heat is stored in payload.
    This service gracefully degrades until heat is fully integrated.
    """

    def __init__(self, database_url: str = None):
        self.database_url = database_url or NEON_DATABASE_URL
        self.config = HEAT_CONFIG
        self._degraded = True  # No memory_metadata table

        if not self.database_url:
            raise ValueError("Database URL not configured")

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = psycopg2.connect(self.database_url)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def apply_decay(self) -> int:
        """
        Apply daily decay to all non-pinned memories.

        Run via cron: 0 3 * * * python -c "from Tools.memory_v2.heat import apply_decay; apply_decay()"

        Returns:
            Number of memories decayed
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE memory_metadata
                    SET heat = GREATEST(%(min_heat)s, heat * %(decay_rate)s),
                        last_accessed = last_accessed  -- Don't update last_accessed
                    WHERE pinned = FALSE
                      AND last_accessed < NOW() - INTERVAL '%(interval)s hours'
                    RETURNING memory_id
                """, {
                    "min_heat": self.config["min_heat"],
                    "decay_rate": self.config["decay_rate"],
                    "interval": self.config["decay_interval_hours"]
                })

                affected = cur.rowcount
                logger.info(f"Applied decay to {affected} memories")
                return affected

    def boost_on_access(self, memory_id: str) -> float:
        """
        Boost heat when a memory is accessed/retrieved.

        Args:
            memory_id: UUID of the memory

        Returns:
            New heat value
        """
        if self._degraded:
            return 1.0  # Default heat when degraded

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE memory_metadata
                    SET heat = LEAST(%(max_heat)s, heat + %(boost)s),
                        last_accessed = NOW(),
                        access_count = access_count + 1
                    WHERE memory_id = %(id)s
                    RETURNING heat
                """, {
                    "max_heat": self.config["max_heat"],
                    "boost": self.config["access_boost"],
                    "id": memory_id
                })

                result = cur.fetchone()
                if result:
                    logger.debug(f"Boosted memory {memory_id} to heat {result[0]}")
                    return result[0]
                return None

    def boost_related(self, entity: str, boost_type: str = "mention") -> int:
        """
        Boost memories related to an entity (client, project, tag).

        Called when entity is discussed in new input.

        Args:
            entity: Client name, project name, or tag
            boost_type: "mention" or "access"

        Returns:
            Number of memories boosted
        """
        if self._degraded:
            return 0

        boost = (self.config["mention_boost"] if boost_type == "mention"
                 else self.config["access_boost"])

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE memory_metadata
                    SET heat = LEAST(%(max_heat)s, heat + %(boost)s)
                    WHERE (client ILIKE %(entity)s
                           OR project ILIKE %(entity)s
                           OR %(entity)s = ANY(tags))
                      AND pinned = FALSE
                    RETURNING memory_id
                """, {
                    "max_heat": self.config["max_heat"],
                    "boost": boost,
                    "entity": entity
                })

                affected = cur.rowcount
                logger.info(f"Boosted {affected} memories related to '{entity}'")
                return affected

    def pin_memory(self, memory_id: str) -> bool:
        """
        Pin a memory so it never decays.

        Args:
            memory_id: UUID of the memory

        Returns:
            Success status
        """
        if self._degraded:
            return False

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE memory_metadata
                    SET pinned = TRUE
                    WHERE memory_id = %(id)s
                    RETURNING memory_id
                """, {"id": memory_id})

                result = cur.fetchone()
                if result:
                    logger.info(f"Pinned memory {memory_id}")
                    return True
                return False

    def unpin_memory(self, memory_id: str) -> bool:
        """Unpin a memory to allow decay."""
        if self._degraded:
            return False

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE memory_metadata
                    SET pinned = FALSE
                    WHERE memory_id = %(id)s
                    RETURNING memory_id
                """, {"id": memory_id})

                return cur.fetchone() is not None

    def set_importance(self, memory_id: str, importance: float) -> bool:
        """
        Set manual importance multiplier for a memory.

        Args:
            memory_id: UUID of the memory
            importance: Multiplier (typically 0.5 - 2.0)
        """
        if self._degraded:
            return False

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE memory_metadata
                    SET importance = %(importance)s
                    WHERE memory_id = %(id)s
                    RETURNING memory_id
                """, {"id": memory_id, "importance": importance})

                return cur.fetchone() is not None

    def get_hot_memories(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get highest-heat memories (what's top of mind).

        Args:
            limit: Maximum results

        Returns:
            List of memories with heat data
        """
        if self._degraded:
            return []

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        m.id,
                        m.content,
                        m.memory_type,
                        m.created_at,
                        mm.heat,
                        mm.importance,
                        mm.access_count,
                        mm.last_accessed,
                        mm.pinned,
                        mm.client,
                        mm.project,
                        mm.source
                    FROM memories m
                    JOIN memory_metadata mm ON m.id = mm.memory_id
                    ORDER BY mm.heat DESC, mm.last_accessed DESC
                    LIMIT %(limit)s
                """, {"limit": limit})

                return [dict(row) for row in cur.fetchall()]

    def get_cold_memories(self, threshold: float = 0.2, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get neglected memories (what am I forgetting?).

        Args:
            threshold: Heat threshold (memories below this)
            limit: Maximum results

        Returns:
            List of cold memories
        """
        if self._degraded:
            return []

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        m.id,
                        m.content,
                        m.memory_type,
                        m.created_at,
                        mm.heat,
                        mm.importance,
                        mm.access_count,
                        mm.last_accessed,
                        mm.pinned,
                        mm.client,
                        mm.project,
                        mm.source
                    FROM memories m
                    JOIN memory_metadata mm ON m.id = mm.memory_id
                    WHERE mm.heat < %(threshold)s
                      AND mm.pinned = FALSE
                    ORDER BY mm.heat ASC
                    LIMIT %(limit)s
                """, {"threshold": threshold, "limit": limit})

                return [dict(row) for row in cur.fetchall()]

    def get_cold_clients(self, threshold: float = 0.3) -> List[str]:
        """
        Find clients that haven't been engaged with recently.

        Returns:
            List of client names with cold memories
        """
        if self._degraded:
            return []

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT mm.client
                    FROM memory_metadata mm
                    WHERE mm.client IS NOT NULL
                      AND mm.heat < %(threshold)s
                      AND mm.pinned = FALSE
                    ORDER BY mm.client
                """, {"threshold": threshold})

                return [row[0] for row in cur.fetchall()]

    def get_heat_stats(self) -> Dict[str, Any]:
        """Get statistics about memory heat distribution."""
        if self._degraded:
            return {"total_memories": 0, "avg_heat": 1.0, "hot_count": 0, "cold_count": 0}

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) as total_memories,
                        AVG(heat) as avg_heat,
                        MIN(heat) as min_heat,
                        MAX(heat) as max_heat,
                        COUNT(*) FILTER (WHERE heat > 0.7) as hot_count,
                        COUNT(*) FILTER (WHERE heat < 0.3) as cold_count,
                        COUNT(*) FILTER (WHERE pinned = TRUE) as pinned_count
                    FROM memory_metadata
                """)

                return dict(cur.fetchone())

    def heat_report(self) -> str:
        """Generate a formatted heat report."""
        hot = self.get_hot_memories(5)
        cold = self.get_cold_memories(0.3, 5)
        stats = self.get_heat_stats()

        lines = []
        lines.append("🔥 MEMORY HEAT REPORT")
        lines.append("=" * 40)
        lines.append(f"Total: {stats['total_memories']} | Avg Heat: {stats['avg_heat']:.2f}")
        lines.append(f"Hot: {stats['hot_count']} | Cold: {stats['cold_count']} | Pinned: {stats['pinned_count']}")
        lines.append("")

        lines.append("🔥 HOT (Active Focus):")
        for m in hot:
            content = m['content'][:50] + "..." if len(m['content']) > 50 else m['content']
            lines.append(f"  {m['heat']:.2f} | {content}")

        lines.append("")
        lines.append("❄️ COLD (Neglected):")
        for m in cold:
            content = m['content'][:50] + "..." if len(m['content']) > 50 else m['content']
            lines.append(f"  {m['heat']:.2f} | {content}")

        return "\n".join(lines)


# Singleton instance
_heat_service: Optional[HeatService] = None


def get_heat_service() -> HeatService:
    """Get or create the singleton HeatService instance."""
    global _heat_service
    if _heat_service is None:
        _heat_service = HeatService()
    return _heat_service


def apply_decay():
    """Convenience function for cron job."""
    service = get_heat_service()
    count = service.apply_decay()
    print(f"Applied decay to {count} memories at {datetime.now()}")
    return count


if __name__ == "__main__":
    # Test heat service
    service = HeatService()
    print(service.heat_report())
