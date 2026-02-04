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
import os
from datetime import datetime, timedelta, timezone
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
        self._persistent_conn = None  # Reuse connection for speed

        if not self.database_url:
            raise ValueError("Database URL not configured")

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        connect_timeout = int(os.getenv("MEMORY_DB_CONNECT_TIMEOUT", "10"))
        statement_timeout_ms = int(os.getenv("MEMORY_DB_STATEMENT_TIMEOUT_MS", "60000"))
        conn = psycopg2.connect(
            self.database_url,
            connect_timeout=connect_timeout,
        )
        if statement_timeout_ms > 0:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = %s", (statement_timeout_ms,))
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def apply_decay(self, use_advanced_formula: bool = True) -> int:
        """
        Apply time-based decay to all non-pinned memories.

        Two decay formulas available:
        1. Simple: heat *= decay_rate (0.97)
        2. Advanced: heat = base_score * decay_factor^days * log(access_count + 1)
        
        Advanced formula balances:
        - Time decay (exponential based on age)
        - Access frequency (logarithmic boost for popular memories)
        
        Run via cron: 0 3 * * * python -c "from Tools.memory_v2.heat import apply_decay; apply_decay()"

        Args:
            use_advanced_formula: Use advanced time+access formula (default True)

        Returns:
            Number of memories decayed
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                partition_count = int(os.getenv("MEMORY_DB_DECAY_PARTITIONS", "1"))
                if partition_count < 1:
                    partition_count = 1
                partition_idx = int(
                    os.getenv(
                        "MEMORY_DB_DECAY_PARTITION",
                        str(datetime.now(timezone.utc).timetuple().tm_yday % partition_count)
                    )
                ) if partition_count > 1 else 0
                partition_filter = ""
                if partition_count > 1:
                    partition_filter = """
                      AND MOD(ABS(hashtext(id::text)), %(partition_count)s) = %(partition_idx)s
                    """

                if use_advanced_formula:
                    # Advanced formula: heat = base_score * decay_factor^days * log(access_count + 1)
                    # Batch to avoid long-running full-table updates.
                    batch_size = int(os.getenv("MEMORY_DB_DECAY_BATCH_SIZE", "2000"))
                    affected = 0
                    last_id = None
                    while True:
                        if last_id:
                            cur.execute(f"""
                                SELECT id
                                FROM thanos_memories
                                WHERE COALESCE((payload->>'pinned')::boolean, FALSE) = FALSE
                                  AND id > %(last_id)s
                                  {partition_filter}
                                ORDER BY id
                                LIMIT %(batch_size)s
                            """, {
                                "last_id": last_id,
                                "batch_size": batch_size,
                                "partition_count": partition_count,
                                "partition_idx": partition_idx,
                            })
                        else:
                            cur.execute(f"""
                                SELECT id
                                FROM thanos_memories
                                WHERE COALESCE((payload->>'pinned')::boolean, FALSE) = FALSE
                                {partition_filter}
                                ORDER BY id
                                LIMIT %(batch_size)s
                            """, {
                                "batch_size": batch_size,
                                "partition_count": partition_count,
                                "partition_idx": partition_idx,
                            })

                        ids = [row[0] for row in cur.fetchall()]
                        if not ids:
                            break

                        cur.execute("""
                            UPDATE thanos_memories
                            SET payload = payload
                                || jsonb_build_object(
                                    'heat', GREATEST(%(min_heat)s,
                                        COALESCE((payload->>'importance')::float, 1.0) *
                                        POWER(%(decay_rate)s,
                                            EXTRACT(EPOCH FROM (NOW() - COALESCE((payload->>'created_at')::timestamp, NOW()))) / 86400
                                        ) *
                                        LOG(COALESCE((payload->>'access_count')::int, 0) + 2)
                                    )
                                )
                            WHERE id = ANY(%(ids)s::uuid[])
                            RETURNING id
                        """, {
                            "min_heat": self.config["min_heat"],
                            "decay_rate": self.config["decay_rate"],
                            "ids": ids,
                        })
                        affected += cur.rowcount
                        last_id = ids[-1]
                        conn.commit()
                else:
                    # Simple formula: heat *= decay_rate
                    cur.execute(f"""
                        UPDATE thanos_memories
                        SET payload = payload
                            || jsonb_build_object(
                                'heat', GREATEST(%(min_heat)s,
                                    COALESCE((payload->>'heat')::float, 1.0) * %(decay_rate)s
                                )
                            )
                        WHERE COALESCE((payload->>'pinned')::boolean, FALSE) = FALSE
                          AND (payload->>'last_accessed')::timestamp < NOW() - INTERVAL '24 hours'
                          {partition_filter}
                        RETURNING id
                    """, {
                        "min_heat": self.config["min_heat"],
                        "decay_rate": self.config["decay_rate"],
                        "partition_count": partition_count,
                        "partition_idx": partition_idx
                    })

                if not use_advanced_formula:
                    affected = cur.rowcount
                formula = "advanced (time+access)" if use_advanced_formula else "simple"
                logger.info(f"Applied {formula} decay to {affected} memories")
                return affected

    def boost_on_access(self, memory_id: str) -> float:
        """
        Boost heat when a memory is accessed/retrieved.

        Args:
            memory_id: UUID of the memory

        Returns:
            New heat value
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Update heat in payload JSON
                cur.execute("""
                    UPDATE thanos_memories
                    SET payload = payload
                        || jsonb_build_object(
                            'heat', LEAST(%(max_heat)s,
                                COALESCE((payload->>'heat')::float, 0.5) + %(boost)s
                            ),
                            'last_accessed', NOW()::text,
                            'access_count', COALESCE((payload->>'access_count')::int, 0) + 1
                        )
                    WHERE id = %(id)s
                    RETURNING (payload->>'heat')::float
                """, {
                    "max_heat": self.config["max_heat"],
                    "boost": self.config["access_boost"],
                    "id": memory_id
                })

                result = cur.fetchone()
                if result:
                    logger.debug(f"Boosted memory {memory_id} to heat {result[0]}")
                    return result[0]
                return 1.0  # Default if memory not found

    def batch_boost_on_access(self, memory_ids: List[str]) -> int:
        """
        Boost heat for multiple memories in a single operation.

        More efficient than calling boost_on_access() repeatedly when
        boosting search results or related memories.

        Args:
            memory_ids: List of memory UUIDs to boost

        Returns:
            Number of memories boosted

        Examples:
            hs.batch_boost_on_access(["uuid1", "uuid2", "uuid3"])
            # Boost all search results
            result_ids = [r['id'] for r in search_results]
            hs.batch_boost_on_access(result_ids)
        """
        if not memory_ids:
            return 0

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Update heat in payload JSON for all specified IDs
                cur.execute("""
                    UPDATE thanos_memories
                    SET payload = payload
                        || jsonb_build_object(
                            'heat', LEAST(%(max_heat)s,
                                COALESCE((payload->>'heat')::float, 0.5) + %(boost)s
                            ),
                            'last_accessed', NOW()::text,
                            'access_count', COALESCE((payload->>'access_count')::int, 0) + 1
                        )
                    WHERE id = ANY(%(ids)s::uuid[])
                    RETURNING id
                """, {
                    "max_heat": self.config["max_heat"],
                    "boost": self.config["access_boost"],
                    "ids": memory_ids
                })

                affected = cur.rowcount
                logger.debug(f"Batch boosted {affected} memories")
                return affected

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
        boost = (self.config["mention_boost"] if boost_type == "mention"
                 else self.config["access_boost"])

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Update heat in payload for related memories
                cur.execute("""
                    UPDATE thanos_memories
                    SET payload = payload
                        || jsonb_build_object(
                            'heat', LEAST(%(max_heat)s,
                                COALESCE((payload->>'heat')::float, 0.5) + %(boost)s
                            )
                        )
                    WHERE (payload->>'client' ILIKE %(entity)s
                           OR payload->>'project' ILIKE %(entity)s)
                      AND COALESCE((payload->>'pinned')::boolean, FALSE) = FALSE
                    RETURNING id
                """, {
                    "max_heat": self.config["max_heat"],
                    "boost": boost,
                    "entity": f"%{entity}%"
                })

                affected = cur.rowcount
                logger.info(f"Boosted {affected} memories related to '{entity}'")
                return affected

    def boost_by_filter(
        self,
        filter_key: str,
        filter_value: str,
        boost: float = 0.1
    ) -> int:
        """
        Boost heat for all memories matching a metadata filter.

        Useful when switching context to a client/project - boost all related
        memories to surface them in searches.

        Args:
            filter_key: Payload key to match (e.g., "client", "project", "domain")
            filter_value: Value to match (e.g., "Orlando", "ScottCare", "work")
            boost: Heat amount to add (default 0.1)

        Returns:
            Number of memories boosted

        Examples:
            hs.boost_by_filter("client", "Orlando", boost=0.15)  # Working on Orlando
            hs.boost_by_filter("project", "VersaCare", boost=0.2)  # Deep diving VersaCare
            hs.boost_by_filter("domain", "work")  # Starting work day
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Use parameterized query for the value, but we need to inject the key
                # since JSONB path can't be parameterized directly
                # Validate filter_key to prevent injection (only allow known keys)
                allowed_keys = {"client", "project", "domain", "source", "type", "category"}
                if filter_key not in allowed_keys:
                    logger.warning(f"Invalid filter_key '{filter_key}'. Allowed: {allowed_keys}")
                    return 0

                cur.execute(f"""
                    UPDATE thanos_memories
                    SET payload = payload
                        || jsonb_build_object(
                            'heat', LEAST(%(max_heat)s,
                                COALESCE((payload->>'heat')::float, 0.5) + %(boost)s
                            ),
                            'last_accessed', NOW()::text
                        )
                    WHERE payload->>'{filter_key}' = %(filter_value)s
                      AND COALESCE((payload->>'pinned')::boolean, FALSE) = FALSE
                    RETURNING id
                """, {
                    "max_heat": self.config["max_heat"],
                    "boost": boost,
                    "filter_value": filter_value
                })

                affected = cur.rowcount
                logger.info(f"Boosted {affected} memories where {filter_key}='{filter_value}' by {boost}")
                return affected

    def pin_memory(self, memory_id: str) -> bool:
        """
        Pin a memory so it never decays.

        Args:
            memory_id: UUID of the memory

        Returns:
            Success status
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE thanos_memories
                    SET payload = payload || jsonb_build_object('pinned', true, 'heat', 2.0)
                    WHERE id = %(id)s
                    RETURNING id
                """, {"id": memory_id})

                result = cur.fetchone()
                if result:
                    logger.info(f"Pinned memory {memory_id}")
                    return True
                return False

    def unpin_memory(self, memory_id: str) -> bool:
        """Unpin a memory to allow decay."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE thanos_memories
                    SET payload = payload || jsonb_build_object('pinned', false)
                    WHERE id = %(id)s
                    RETURNING id
                """, {"id": memory_id})

                return cur.fetchone() is not None

    def set_importance(self, memory_id: str, importance: float) -> bool:
        """
        Set manual importance multiplier for a memory.

        Args:
            memory_id: UUID of the memory
            importance: Multiplier (typically 0.5 - 2.0)
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE thanos_memories
                    SET payload = payload || jsonb_build_object('importance', %(importance)s)
                    WHERE id = %(id)s
                    RETURNING id
                """, {"id": memory_id, "importance": importance})

                return cur.fetchone() is not None

    def get_hot_memories(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get highest-heat memories (what's top of mind).

        Uses stored heat field where available, falls back to recency-based
        heat calculation for legacy memories without heat tracking.

        Args:
            limit: Maximum results

        Returns:
            List of memories with heat data
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Query thanos_memories, using stored heat or recency-based fallback
                cur.execute("""
                    SELECT
                        id,
                        payload->>'data' as memory,
                        payload->>'data' as content,
                        payload->>'source' as source,
                        payload->>'client' as client,
                        payload->>'project' as project,
                        payload->>'type' as memory_type,
                        (payload->>'created_at')::timestamp as created_at,
                        COALESCE(
                            (payload->>'heat')::float,
                            -- Fallback: calculate heat from recency for legacy data
                            CASE
                                WHEN (payload->>'created_at')::timestamp > NOW() - INTERVAL '6 hours' THEN 1.0
                                WHEN (payload->>'created_at')::timestamp > NOW() - INTERVAL '24 hours' THEN 0.85
                                WHEN (payload->>'created_at')::timestamp > NOW() - INTERVAL '48 hours' THEN 0.7
                                WHEN (payload->>'created_at')::timestamp > NOW() - INTERVAL '7 days' THEN 0.5
                                ELSE 0.3
                            END
                        ) as heat,
                        COALESCE((payload->>'importance')::float, 1.0) as importance,
                        COALESCE((payload->>'pinned')::boolean, FALSE) as pinned,
                        COALESCE((payload->>'access_count')::int, 0) as access_count
                    FROM thanos_memories
                    ORDER BY
                        COALESCE(
                            (payload->>'heat')::float,
                            CASE
                                WHEN (payload->>'created_at')::timestamp > NOW() - INTERVAL '6 hours' THEN 1.0
                                WHEN (payload->>'created_at')::timestamp > NOW() - INTERVAL '24 hours' THEN 0.85
                                ELSE 0.5
                            END
                        ) DESC,
                        (payload->>'created_at')::timestamp DESC
                    LIMIT %(limit)s
                """, {"limit": limit})

                return [dict(row) for row in cur.fetchall()]

    def get_cold_memories(
        self,
        threshold: float = 0.3,
        limit: int = 20,
        min_age_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get neglected memories (what am I forgetting?).

        Returns memories that are both:
        1. Below the heat threshold (cold)
        2. Older than min_age_days (not just new)

        This prevents surfacing very recent memories that are cold simply
        because they're new - they're cold because they're neglected.

        Args:
            threshold: Heat threshold (memories below this are "cold")
            limit: Maximum results
            min_age_days: Exclude memories newer than this (default 7 days)
                         New memories haven't had time to be "neglected"

        Returns:
            List of cold memories sorted by heat (coldest first)

        Examples:
            hs.get_cold_memories()  # Default: cold memories > 7 days old
            hs.get_cold_memories(min_age_days=3)  # More aggressive surfacing
            hs.get_cold_memories(threshold=0.5, limit=20)  # Include warmer memories
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Query thanos_memories for memories below heat threshold and older than min_age_days
                cur.execute("""
                    SELECT
                        id,
                        payload->>'data' as memory,
                        payload->>'data' as content,
                        payload->>'source' as source,
                        payload->>'client' as client,
                        payload->>'project' as project,
                        payload->>'type' as memory_type,
                        (payload->>'created_at')::timestamp as created_at,
                        COALESCE((payload->>'heat')::float,
                            CASE
                                WHEN (payload->>'created_at')::timestamp > NOW() - INTERVAL '7 days' THEN 0.3
                                WHEN (payload->>'created_at')::timestamp > NOW() - INTERVAL '14 days' THEN 0.2
                                WHEN (payload->>'created_at')::timestamp > NOW() - INTERVAL '30 days' THEN 0.1
                                ELSE 0.05
                            END
                        ) as heat,
                        COALESCE((payload->>'importance')::float, 1.0) as importance,
                        COALESCE((payload->>'pinned')::boolean, FALSE) as pinned
                    FROM thanos_memories
                    WHERE (payload->>'created_at')::timestamp < NOW() - INTERVAL '1 day' * %(min_age_days)s
                      AND COALESCE((payload->>'pinned')::boolean, FALSE) = FALSE
                      AND COALESCE((payload->>'heat')::float, 0.1) < %(threshold)s
                    ORDER BY COALESCE((payload->>'heat')::float, 0.1) ASC,
                             (payload->>'created_at')::timestamp DESC
                    LIMIT %(limit)s
                """, {"limit": limit, "min_age_days": min_age_days, "threshold": threshold})

                return [dict(row) for row in cur.fetchall()]

    def get_cold_clients(self, threshold: float = 0.3) -> List[str]:
        """
        Find clients that haven't been engaged with recently.

        Returns:
            List of client names with cold memories (no recent entries)
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Find clients with no memories in last 14 days
                cur.execute("""
                    SELECT DISTINCT payload->>'client' as client
                    FROM thanos_memories
                    WHERE payload->>'client' IS NOT NULL
                      AND payload->>'client' != ''
                      AND (payload->>'created_at')::timestamp < NOW() - INTERVAL '14 days'
                      AND payload->>'client' NOT IN (
                          SELECT DISTINCT payload->>'client'
                          FROM thanos_memories
                          WHERE payload->>'client' IS NOT NULL
                            AND (payload->>'created_at')::timestamp > NOW() - INTERVAL '14 days'
                      )
                    ORDER BY client
                """)

                return [row[0] for row in cur.fetchall() if row[0]]

    def get_heat_stats(self) -> Dict[str, Any]:
        """Get statistics about memory heat distribution."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) as total_memories,
                        COUNT(*) FILTER (WHERE (payload->>'created_at')::timestamp > NOW() - INTERVAL '48 hours') as hot_count,
                        COUNT(*) FILTER (WHERE (payload->>'created_at')::timestamp < NOW() - INTERVAL '7 days') as cold_count,
                        COUNT(*) FILTER (WHERE (payload->>'pinned')::boolean = TRUE) as pinned_count,
                        COUNT(DISTINCT payload->>'client') FILTER (WHERE payload->>'client' IS NOT NULL AND payload->>'client' != '') as client_count
                    FROM thanos_memories
                """)

                row = cur.fetchone()
                # Calculate synthetic avg_heat based on age distribution
                total = row['total_memories'] or 1
                hot = row['hot_count'] or 0
                cold = row['cold_count'] or 0
                warm = total - hot - cold
                avg_heat = (hot * 0.9 + warm * 0.5 + cold * 0.15) / total if total > 0 else 0.5

                return {
                    "total_memories": row['total_memories'],
                    "avg_heat": round(avg_heat, 2),
                    "hot_count": row['hot_count'],
                    "cold_count": row['cold_count'],
                    "pinned_count": row['pinned_count'],
                    "client_count": row['client_count'],
                    "min_heat": 0.05,
                    "max_heat": 1.0
                }

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
            content = (m.get('content') or m.get('memory') or '')[:50]
            if len(m.get('content') or m.get('memory') or '') > 50:
                content += "..."
            heat = m.get('heat', 0.5)
            lines.append(f"  {heat:.2f} | {content}")

        lines.append("")
        lines.append("❄️ COLD (Neglected):")
        for m in cold:
            content = (m.get('content') or m.get('memory') or '')[:50]
            if len(m.get('content') or m.get('memory') or '') > 50:
                content += "..."
            heat = m.get('heat', 0.1)
            lines.append(f"  {heat:.2f} | {content}")

        return "\n".join(lines)


# Singleton instance
_heat_service: Optional[HeatService] = None


def get_heat_service() -> HeatService:
    """Get or create the singleton HeatService instance."""
    global _heat_service
    if _heat_service is None:
        _heat_service = HeatService()
    return _heat_service


def apply_decay(use_advanced_formula: bool = True):
    """
    Convenience function for cron job.
    
    Args:
        use_advanced_formula: Use advanced time+access decay formula (default True)
    
    Cron examples:
        # Advanced formula (recommended)
        0 3 * * * cd /path/to/Thanos && .venv/bin/python -c "from Tools.memory_v2.heat import apply_decay; apply_decay()"
        
        # Simple formula
        0 3 * * * cd /path/to/Thanos && .venv/bin/python -c "from Tools.memory_v2.heat import apply_decay; apply_decay(False)"
    """
    service = get_heat_service()
    count = service.apply_decay(use_advanced_formula=use_advanced_formula)
    formula = "advanced" if use_advanced_formula else "simple"
    print(f"Applied {formula} decay to {count} memories at {datetime.now()}")
    return count


if __name__ == "__main__":
    # Test heat service
    service = HeatService()
    print(service.heat_report())
