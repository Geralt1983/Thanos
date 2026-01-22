"""
Memory Service for Thanos Memory V2.

Core memory operations:
- add(): Store content with automatic fact extraction
- search(): Find relevant memories, ranked by similarity * heat * importance
- get_context_for_query(): Get formatted context for Claude prompts

ADHD helpers:
- whats_hot(): Current focus / top of mind
- whats_cold(): What am I neglecting / forgetting?
- pin(): Mark memory as critical (never decays)
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import NEON_DATABASE_URL, MEM0_CONFIG, DEFAULT_USER_ID, validate_config
from .heat import HeatService, get_heat_service

logger = logging.getLogger(__name__)

# Try to import mem0, but allow graceful degradation
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    logger.warning("mem0 not installed. Run: pip install mem0ai")


class MemoryService:
    """
    Core memory service with heat-based ranking.

    Uses mem0 for fact extraction and embedding generation,
    with custom heat decay for ADHD-friendly memory surfacing.
    """

    def __init__(self, database_url: str = None, user_id: str = None):
        self.database_url = database_url or NEON_DATABASE_URL
        self.user_id = user_id or DEFAULT_USER_ID
        self.heat_service = get_heat_service()

        if not self.database_url:
            raise ValueError("Database URL not configured")

        # Initialize mem0 if available
        self.memory = None
        if MEM0_AVAILABLE:
            try:
                self.memory = Memory.from_config(MEM0_CONFIG)
                logger.info("mem0 initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize mem0: {e}")

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

    def add(self, content: str, metadata: dict = None) -> Dict[str, Any]:
        """
        Add content to memory with automatic fact extraction.

        Args:
            content: The content to remember
            metadata: Optional metadata (source, client, project, tags)

        Returns:
            Result of memory addition
        """
        metadata = metadata or {}

        if self.memory:
            # Use mem0 for fact extraction and storage
            result = self.memory.add(
                messages=[{"role": "user", "content": content}],
                user_id=self.user_id,
                metadata=metadata
            )

            # Store extended metadata with heat
            if result and "results" in result:
                for mem_result in result["results"]:
                    memory_id = mem_result.get("id")
                    if memory_id:
                        self._store_metadata(memory_id, metadata)

            # Boost related entities
            if metadata.get("client"):
                self.heat_service.boost_related(metadata["client"], "mention")
            if metadata.get("project"):
                self.heat_service.boost_related(metadata["project"], "mention")

            return result
        else:
            # Fallback: Direct storage without mem0
            return self._direct_add(content, metadata)

    def _direct_add(self, content: str, metadata: dict) -> Dict[str, Any]:
        """Direct storage when mem0 is not available."""
        import uuid

        memory_id = str(uuid.uuid4())

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Insert into memories
                cur.execute("""
                    INSERT INTO memories (id, user_id, content, memory_type, created_at)
                    VALUES (%(id)s, %(user_id)s, %(content)s, %(type)s, NOW())
                    RETURNING id
                """, {
                    "id": memory_id,
                    "user_id": self.user_id,
                    "content": content,
                    "type": metadata.get("type", "note")
                })

                # Insert metadata
                self._store_metadata(memory_id, metadata, cur)

        return {"id": memory_id, "content": content}

    def _store_metadata(self, memory_id: str, metadata: dict, cursor=None):
        """Store extended metadata with initial heat."""
        def _insert(cur):
            cur.execute("""
                INSERT INTO memory_metadata (
                    memory_id, source, source_file, original_timestamp,
                    client, project, tags, heat, importance, created_at
                )
                VALUES (
                    %(memory_id)s, %(source)s, %(source_file)s, %(timestamp)s,
                    %(client)s, %(project)s, %(tags)s, 1.0, %(importance)s, NOW()
                )
                ON CONFLICT (memory_id) DO UPDATE SET
                    source = EXCLUDED.source,
                    client = EXCLUDED.client,
                    project = EXCLUDED.project,
                    tags = EXCLUDED.tags
            """, {
                "memory_id": memory_id,
                "source": metadata.get("source", "manual"),
                "source_file": metadata.get("source_file"),
                "timestamp": metadata.get("original_timestamp"),
                "client": metadata.get("client"),
                "project": metadata.get("project"),
                "tags": metadata.get("tags"),
                "importance": metadata.get("importance", 1.0)
            })

        if cursor:
            _insert(cursor)
        else:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    _insert(cur)

    def search(self, query: str, limit: int = 10, filters: dict = None) -> List[Dict[str, Any]]:
        """
        Search memories by semantic similarity, RE-RANKED BY HEAT.

        Args:
            query: Natural language search query
            limit: Maximum results to return
            filters: Optional filters (client, source, memory_type)

        Returns:
            List of memories ranked by effective_score (similarity * heat * importance)
        """
        if self.memory:
            # Get more results than needed for re-ranking
            raw_results = self.memory.search(
                query=query,
                user_id=self.user_id,
                limit=limit * 3
            )

            # mem0.search returns {'results': [...]} - extract the list
            if isinstance(raw_results, dict) and 'results' in raw_results:
                raw_results = raw_results['results']

            # Re-rank by heat
            ranked = self._apply_heat_ranking(raw_results)

            # Apply additional filters
            if filters:
                ranked = self._apply_filters(ranked, filters)

            # Boost accessed memories (top results only)
            for mem in ranked[:limit]:
                if "id" in mem:
                    self.heat_service.boost_on_access(mem["id"])

            return ranked[:limit]
        else:
            # Fallback: Direct search without mem0
            return self._direct_search(query, limit, filters)

    def _direct_search(self, query: str, limit: int, filters: dict = None) -> List[Dict[str, Any]]:
        """Direct search when mem0 is not available (text-based)."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Basic text search
                cur.execute("""
                    SELECT
                        m.id,
                        m.content,
                        m.memory_type,
                        m.created_at,
                        mm.heat,
                        mm.importance,
                        mm.client,
                        mm.project,
                        mm.source,
                        0.5 as score,
                        (0.5 * COALESCE(mm.heat, 1.0) * COALESCE(mm.importance, 1.0)) as effective_score
                    FROM memories m
                    LEFT JOIN memory_metadata mm ON m.id = mm.memory_id
                    WHERE m.user_id = %(user_id)s
                      AND m.content ILIKE %(pattern)s
                    ORDER BY effective_score DESC
                    LIMIT %(limit)s
                """, {
                    "user_id": self.user_id,
                    "pattern": f"%{query}%",
                    "limit": limit
                })

                return [dict(row) for row in cur.fetchall()]

    def _apply_heat_ranking(self, results: List[Dict]) -> List[Dict]:
        """Re-rank results by similarity * heat * importance."""
        if not results:
            return []

        memory_ids = [r.get("id") for r in results if r.get("id")]

        if not memory_ids:
            return results

        # Fetch heat data
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT memory_id, heat, importance
                    FROM memory_metadata
                    WHERE memory_id = ANY(%(ids)s::uuid[])
                """, {"ids": memory_ids})

                heat_map = {str(row["memory_id"]): row for row in cur.fetchall()}

        # Calculate effective scores
        for result in results:
            mem_id = str(result.get("id", ""))
            meta = heat_map.get(mem_id, {"heat": 0.5, "importance": 1.0})

            result["heat"] = meta.get("heat", 0.5)
            result["importance"] = meta.get("importance", 1.0)

            similarity = result.get("score", 0.5)
            result["effective_score"] = (
                similarity *
                result["heat"] *
                result["importance"]
            )

        # Sort by effective score
        return sorted(results, key=lambda x: x.get("effective_score", 0), reverse=True)

    def _apply_filters(self, results: List[Dict], filters: dict) -> List[Dict]:
        """Apply metadata filters to results."""
        filtered = results

        if filters.get("client"):
            filtered = [r for r in filtered if r.get("client") == filters["client"]]

        if filters.get("source"):
            filtered = [r for r in filtered if r.get("source") == filters["source"]]

        if filters.get("memory_type"):
            filtered = [r for r in filtered if r.get("memory_type") == filters["memory_type"]]

        return filtered

    def get_context_for_query(self, query: str, limit: int = 10) -> str:
        """
        Get formatted context string for Claude prompts.

        Args:
            query: What context is needed for
            limit: Maximum memories to include

        Returns:
            Formatted string of relevant memories
        """
        memories = self.search(query, limit=limit)

        if not memories:
            return "No relevant memories found."

        context_parts = []
        for mem in memories:
            heat = mem.get("heat", 1.0)
            heat_indicator = "🔥" if heat > 0.7 else "•" if heat > 0.3 else "❄️"

            content = mem.get("memory", mem.get("content", ""))
            score = mem.get("effective_score", 0)

            context_parts.append(
                f"{heat_indicator} {content} (relevance: {score:.2f})"
            )

        return "Relevant memories:\n" + "\n".join(context_parts)

    # ADHD Helper Methods

    def whats_hot(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        What's top of mind right now?

        Returns highest-heat memories for current focus context.
        """
        return self.heat_service.get_hot_memories(limit)

    def whats_cold(self, threshold: float = 0.2, limit: int = 10) -> List[Dict[str, Any]]:
        """
        What am I neglecting/forgetting?

        Returns lowest-heat memories that might need attention.
        """
        return self.heat_service.get_cold_memories(threshold, limit)

    def pin(self, memory_id: str) -> bool:
        """Pin a memory so it never decays."""
        return self.heat_service.pin_memory(memory_id)

    def unpin(self, memory_id: str) -> bool:
        """Unpin a memory to allow normal decay."""
        return self.heat_service.unpin_memory(memory_id)

    def get_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all memories for user."""
        if self.memory:
            return self.memory.get_all(user_id=self.user_id, limit=limit)

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM memories_with_heat
                    WHERE user_id = %(user_id)s
                    ORDER BY created_at DESC
                    LIMIT %(limit)s
                """, {"user_id": self.user_id, "limit": limit})

                return [dict(row) for row in cur.fetchall()]

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        if self.memory:
            self.memory.delete(memory_id)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM memories WHERE id = %(id)s
                """, {"id": memory_id})
                return cur.rowcount > 0

    def stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        heat_stats = self.heat_service.get_heat_stats()

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(DISTINCT client) as unique_clients,
                        COUNT(DISTINCT project) as unique_projects,
                        COUNT(DISTINCT source) as unique_sources
                    FROM memories m
                    LEFT JOIN memory_metadata mm ON m.id = mm.memory_id
                    WHERE m.user_id = %(user_id)s
                """, {"user_id": self.user_id})

                general_stats = dict(cur.fetchone())

        return {**general_stats, **heat_stats}


# Singleton instance
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """Get or create the singleton MemoryService instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service


# Convenience aliases
memory_service = None  # Will be set when init() is called


if __name__ == "__main__":
    # Test memory service
    service = MemoryService()
    print("Memory Service initialized")
    print(f"Stats: {service.stats()}")
