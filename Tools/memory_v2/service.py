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
import hashlib
from datetime import datetime
from functools import lru_cache
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import NEON_DATABASE_URL, MEM0_CONFIG, DEFAULT_USER_ID, OPENAI_API_KEY, validate_config

# Try to import relationship store, but allow graceful degradation
try:
    from ..relationships import RelationshipStore, RelationType, get_relationship_store
    RELATIONSHIPS_AVAILABLE = True
except ImportError:
    RELATIONSHIPS_AVAILABLE = False
    RelationshipStore = None
    RelationType = None
    get_relationship_store = None
    logger.warning("Relationship store not available")

# Query embedding cache - avoids repeated OpenAI API calls
@lru_cache(maxsize=256)
def _cached_query_embedding(query: str) -> Tuple[float, ...]:
    """Cache query embeddings to reduce OpenAI API latency."""
    import openai
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    return tuple(response.data[0].embedding)

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

    IMPORTANT: Read skill before use:
    - File: .claude/skills/memory-v2/skill.md
    - Or search: ms.search("MEMORY V2 SKILL READ BEFORE")
    """

    # Class-level flag for skill reminder (once per session)
    _skill_reminded = False

    def __init__(self, database_url: str = None, user_id: str = None):
        self.database_url = database_url or NEON_DATABASE_URL
        self.user_id = user_id or DEFAULT_USER_ID
        self.heat_service = get_heat_service()
        self._persistent_conn = None  # Reuse connection for speed

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

        # Initialize relationship store if available
        self.relationships = None
        if RELATIONSHIPS_AVAILABLE:
            try:
                self.relationships = get_relationship_store()
                logger.info("Relationship store initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize relationship store: {e}")

    def _ensure_skill_reminder(self):
        """Show skill reminder on first use per session."""
        if not MemoryService._skill_reminded:
            MemoryService._skill_reminded = True
            logger.info("📚 Memory V2: Skill patterns available. Search 'MEMORY V2 SKILL' for docs.")

    @contextmanager
    def _get_connection(self):
        """Get database connection, reusing persistent connection when possible."""
        # Reuse persistent connection for speed (avoids ~300ms TCP handshake to Neon)
        if self._persistent_conn is None or self._persistent_conn.closed:
            self._persistent_conn = psycopg2.connect(self.database_url)
        conn = self._persistent_conn
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        # Note: Don't close - we're reusing this connection

    def add(self, content: str, metadata: dict = None) -> Dict[str, Any]:
        """
        Add content to memory with automatic fact extraction.

        Args:
            content: The content to remember
            metadata: Optional metadata (source, client, project, tags, relationships)
                     relationships format: [{'type': 'relates_to', 'target': 'mem_123'}]

        Returns:
            Result of memory addition
        """
        self._ensure_skill_reminder()
        metadata = metadata or {}

        # Extract relationships from metadata (don't pass to mem0)
        relationships = metadata.pop("relationships", None)

        if self.memory:
            # Use mem0 for fact extraction and storage
            result = self.memory.add(
                messages=[{"role": "user", "content": content}],
                user_id=self.user_id,
                metadata=metadata
            )

            # Store extended metadata with heat and relationships
            if result and "results" in result:
                for mem_result in result["results"]:
                    memory_id = mem_result.get("id")
                    if memory_id:
                        self._store_metadata(memory_id, metadata)
                        # Store relationships if provided
                        if relationships:
                            self._store_relationships(memory_id, relationships)

            # Boost related entities
            if metadata.get("client"):
                self.heat_service.boost_related(metadata["client"], "mention")
            if metadata.get("project"):
                self.heat_service.boost_related(metadata["project"], "mention")

            return result
        else:
            # Fallback: Generate embedding manually via OpenAI
            logger.warning("mem0 unavailable, using direct OpenAI embedding")
            # Re-add relationships to metadata for fallback path
            if relationships:
                metadata["relationships"] = relationships
            return self._direct_add_with_embedding(content, metadata)

    def _direct_add_with_embedding(self, content: str, metadata: dict) -> Dict[str, Any]:
        """Direct storage with manual OpenAI embedding when mem0 unavailable."""
        import uuid
        import openai
        from .config import OPENAI_API_KEY

        if not OPENAI_API_KEY:
            raise ValueError("Cannot store memory: mem0 unavailable and OPENAI_API_KEY not set")

        memory_id = str(uuid.uuid4())

        # Extract relationships from metadata (don't store in payload)
        relationships = metadata.pop("relationships", None)

        # Generate embedding via OpenAI
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=content
        )
        embedding = response.data[0].embedding

        # Build payload matching mem0 format with all metadata
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()

        payload = {
            "data": content,
            "hash": content_hash,
            "user_id": self.user_id,
            "created_at": datetime.now().isoformat(),
            # Heat tracking for tiered memory
            "heat": 1.0,  # New memories are hot
            "importance": metadata.get("importance", 1.0),
            "pinned": metadata.get("pinned", False),
            "access_count": 0,
            "last_accessed": datetime.now().isoformat(),
        }
        # Copy all metadata into payload
        for key, value in metadata.items():
            if value is not None:
                payload[key] = value

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Insert into thanos_memories (mem0's table)
                cur.execute("""
                    INSERT INTO thanos_memories (id, vector, payload)
                    VALUES (%(id)s, %(vector)s, %(payload)s)
                    RETURNING id
                """, {
                    "id": memory_id,
                    "vector": embedding,
                    "payload": psycopg2.extras.Json(payload)
                })

        # Store relationships if provided
        if relationships:
            self._store_relationships(memory_id, relationships)

        logger.info(f"Stored memory with direct embedding: {memory_id}")
        return {"id": memory_id, "content": content, "embedding_dims": len(embedding)}

    def add_document(self, content: str, metadata: dict = None) -> Dict[str, Any]:
        """
        Add a document to memory with direct embedding storage.

        Unlike add(), this bypasses mem0's fact extraction and stores
        the full document content directly. Use for:
        - PDF documents
        - Long-form content
        - Content that should be stored verbatim

        Args:
            content: Document content to store
            metadata: Document metadata (source, filename, type, relationships, etc.)
                     relationships format: [{'type': 'relates_to', 'target': 'mem_123'}]

        Returns:
            Result with memory_id
        """
        metadata = metadata or {}

        # Always use direct embedding for documents
        result = self._direct_add_with_embedding(content, metadata)

        # Boost related entities
        if metadata.get("client"):
            self.heat_service.boost_related(metadata["client"], "mention")
        if metadata.get("project"):
            self.heat_service.boost_related(metadata["project"], "mention")

        return result

    def _store_metadata(self, memory_id: str, metadata: dict, cursor=None):
        """Store extended metadata.

        Note: mem0 stores metadata in payload column of thanos_memories.
        This is now a no-op since we migrated to unified storage.
        """
        # Metadata is stored in payload by mem0, no separate table needed
        pass

    def _store_relationships(self, memory_id: str, relationships: List[Dict[str, Any]]) -> None:
        """
        Store relationships for a memory.

        Args:
            memory_id: The source memory ID
            relationships: List of relationship dicts with 'type' and 'target' keys
                          Example: [{'type': 'relates_to', 'target': 'mem_123'}]
        """
        if not self.relationships or not relationships:
            return

        for rel in relationships:
            rel_type_str = rel.get("type")
            target_id = rel.get("target")

            if not rel_type_str or not target_id:
                logger.warning(f"Skipping invalid relationship: {rel}")
                continue

            # Convert string type to RelationType enum
            try:
                # Handle both snake_case and UPPER_CASE
                rel_type_key = rel_type_str.upper()
                rel_type = RelationType[rel_type_key]
            except (KeyError, AttributeError):
                logger.warning(f"Unknown relationship type: {rel_type_str}, defaulting to RELATED_TO")
                rel_type = RelationType.RELATED_TO

            # Store the relationship
            try:
                strength = rel.get("strength", 1.0)
                metadata = {k: v for k, v in rel.items() if k not in ["type", "target", "strength"]}

                self.relationships.link_memories(
                    source_id=memory_id,
                    target_id=target_id,
                    rel_type=rel_type,
                    strength=strength,
                    metadata=metadata if metadata else None
                )
                logger.info(f"Stored relationship: {memory_id} -> {rel_type.value} -> {target_id}")
            except Exception as e:
                logger.error(f"Failed to store relationship: {e}")

    def search(
        self,
        query: str,
        limit: int = 10,
        client: str = None,
        project: str = None,
        domain: str = None,
        source: str = None,
        filters: dict = None
    ) -> List[Dict[str, Any]]:
        """
        Search memories by semantic similarity, RE-RANKED BY HEAT.

        Uses direct vector search with cached embeddings for speed.
        (mem0 is used for add/fact-extraction, not search)

        Ranking Formula:
            effective_score = (0.6 * similarity) + (0.3 * heat) + (0.1 * importance)

        Args:
            query: Natural language search query
            limit: Maximum results to return
            client: Filter to specific client (e.g., "Orlando", "Kentucky")
            project: Filter to specific project (e.g., "ScottCare", "VersaCare")
            domain: Filter to domain ("work" or "personal")
            source: Filter by source ("telegram", "hey_pocket", "manual")
            filters: Optional legacy filters dict (client, source, memory_type)

        Returns:
            List of memories ranked by effective_score

        Examples:
            ms.search("API integration")  # Search all memories
            ms.search("API integration", client="Orlando")  # Within client context
            ms.search("authentication", project="VersaCare")  # Within project
            ms.search("family", domain="personal")  # Personal memories only
        """
        # Skill reminder on first use
        self._ensure_skill_reminder()

        # Build consolidated filters
        search_filters = filters.copy() if filters else {}
        if client:
            search_filters["client"] = client
        if project:
            search_filters["project"] = project
        if domain:
            search_filters["domain"] = domain
        if source:
            search_filters["source"] = source

        # Always use direct search with cached embeddings for speed
        # mem0.search() calls OpenAI per-query without caching
        return self._direct_search(query, limit, search_filters)

    def _direct_search(self, query: str, limit: int, filters: dict = None) -> List[Dict[str, Any]]:
        """Direct semantic search with cached embeddings and SQL-level filtering."""
        if not OPENAI_API_KEY:
            logger.warning("No OPENAI_API_KEY, falling back to text search")
            return self._text_search(query, limit, filters)

        # Use cached embedding (LRU cache avoids repeated API calls)
        query_embedding = list(_cached_query_embedding(query))

        # Build dynamic WHERE clause for filters (SQL-level filtering is faster)
        where_clauses = ["payload->>'user_id' = %(user_id)s"]
        params = {
            "user_id": self.user_id,
            "embedding": query_embedding,
            "limit": limit * 3  # Fetch more for re-ranking
        }

        filters = filters or {}
        if filters.get("client"):
            where_clauses.append("payload->>'client' = %(filter_client)s")
            params["filter_client"] = filters["client"]
        if filters.get("project"):
            where_clauses.append("payload->>'project' = %(filter_project)s")
            params["filter_project"] = filters["project"]
        if filters.get("domain"):
            where_clauses.append("payload->>'domain' = %(filter_domain)s")
            params["filter_domain"] = filters["domain"]
        if filters.get("source"):
            where_clauses.append("payload->>'source' = %(filter_source)s")
            params["filter_source"] = filters["source"]
        if filters.get("memory_type"):
            where_clauses.append("payload->>'type' = %(filter_type)s")
            params["filter_type"] = filters["memory_type"]

        where_sql = " AND ".join(where_clauses)

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Vector similarity search on thanos_memories with SQL-level filters
                cur.execute(f"""
                    SELECT
                        id,
                        payload->>'data' as memory,
                        payload->>'data' as content,
                        payload->>'type' as memory_type,
                        (payload->>'created_at')::timestamp as created_at,
                        payload->>'client' as client,
                        payload->>'project' as project,
                        payload->>'domain' as domain,
                        payload->>'source' as source,
                        (vector <=> %(embedding)s::vector) as score
                    FROM thanos_memories
                    WHERE {where_sql}
                    ORDER BY vector <=> %(embedding)s::vector
                    LIMIT %(limit)s
                """, params)

                results = [dict(row) for row in cur.fetchall()]

        # Apply heat ranking (converts distance to similarity, uses weighted addition)
        ranked = self._apply_heat_ranking(results)

        # Boost accessed memories
        for mem in ranked[:limit]:
            if "id" in mem:
                self.heat_service.boost_on_access(mem["id"])

        return ranked[:limit]

    def _text_search(self, query: str, limit: int, filters: dict = None) -> List[Dict[str, Any]]:
        """Fallback text search when no embedding available."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        id,
                        payload->>'data' as memory,
                        payload->>'data' as content,
                        payload->>'type' as memory_type,
                        (payload->>'created_at')::timestamp as created_at,
                        payload->>'client' as client,
                        payload->>'source' as source,
                        0.5 as score
                    FROM thanos_memories
                    WHERE payload->>'user_id' = %(user_id)s
                      AND payload->>'data' ILIKE %(pattern)s
                    LIMIT %(limit)s
                """, {
                    "user_id": self.user_id,
                    "pattern": f"%{query}%",
                    "limit": limit
                })

                return [dict(row) for row in cur.fetchall()]

    def _apply_heat_ranking(self, results: List[Dict]) -> List[Dict]:
        """Re-rank results by weighted combination of similarity, heat, and importance.

        Formula: effective_score = (0.6 * similarity) + (0.3 * heat) + (0.1 * importance)

        This weighted addition ensures:
        - Similarity dominates (60%) - semantic match is primary
        - Heat adjusts ranking (30%) - recent/active memories rank higher
        - Importance is tiebreaker (10%) - manual boost for critical items

        Previous multiplicative formula (similarity * heat * importance) could bury
        semantically perfect matches if they were cold (0.95 * 0.1 = 0.095).

        Heat data is stored in payload for thanos_memories table.
        Falls back to defaults if not present.
        """
        if not results:
            return []

        # Calculate effective scores using payload data or defaults
        for result in results:
            # Try to get heat/importance from payload (thanos_memories format)
            payload = result.get("payload", {})
            if isinstance(payload, str):
                import json
                try:
                    payload = json.loads(payload)
                except:
                    payload = {}

            result["heat"] = payload.get("heat", result.get("heat", 1.0))
            result["importance"] = payload.get("importance", result.get("importance", 1.0))

            # mem0 returns cosine DISTANCE (lower = better match)
            # Convert to similarity (higher = better) for intuitive ranking
            raw_score = result.get("score", 0.5)
            similarity = 1 - raw_score

            # Weighted addition: similarity dominates, heat adjusts, importance is tiebreaker
            # Normalize heat to 0-1 range (heat ranges 0.05-2.0, so divide by 2)
            normalized_heat = min(result["heat"] / 2.0, 1.0)
            # Normalize importance (typically 0.5-2.0, so divide by 2)
            normalized_importance = min(result["importance"] / 2.0, 1.0)

            result["effective_score"] = (
                (0.6 * similarity) +
                (0.3 * normalized_heat) +
                (0.1 * normalized_importance)
            )
            # Store components for debugging
            result["similarity"] = similarity

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
        self._ensure_skill_reminder()
        return self.heat_service.get_hot_memories(limit)

    def whats_cold(
        self,
        threshold: float = 0.3,
        limit: int = 10,
        min_age_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        What am I neglecting/forgetting?

        Returns lowest-heat memories that might need attention.
        Excludes very recent memories (they're cold because they're new, not neglected).

        Args:
            threshold: Heat threshold (memories below this)
            limit: Maximum results
            min_age_days: Exclude memories newer than this (default 7 days)
        """
        self._ensure_skill_reminder()
        return self.heat_service.get_cold_memories(threshold, limit, min_age_days)

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
                    SELECT
                        id,
                        payload->>'data' as memory,
                        payload->>'type' as memory_type,
                        payload->>'source' as source,
                        payload->>'client' as client,
                        payload->>'created_at' as created_at
                    FROM thanos_memories
                    WHERE payload->>'user_id' = %(user_id)s
                    ORDER BY (payload->>'created_at')::timestamp DESC NULLS LAST
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
                    DELETE FROM thanos_memories WHERE id = %(id)s
                """, {"id": memory_id})
                return cur.rowcount > 0

    def stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(DISTINCT payload->>'client') as unique_clients,
                        COUNT(DISTINCT payload->>'project') as unique_projects,
                        COUNT(DISTINCT payload->>'source') as unique_sources
                    FROM thanos_memories
                    WHERE payload->>'user_id' = %(user_id)s
                """, {"user_id": self.user_id})

                return dict(cur.fetchone())


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
