"""
Unified Memory Router for Thanos.

Routes ALL memory operations through Memory V2 (mem0 + Neon + heat) as the primary backend.
Legacy systems (Tools/memory, MemOS) are available as explicit fallbacks only.

Usage:
    from Tools.memory_router import get_memory, add_memory, search_memory

    # All operations go through V2 by default
    add_memory("Meeting notes with Orlando", metadata={"client": "Orlando"})
    results = search_memory("Orlando project status")
    context = get_context("What's blocking Memphis?")

    # ADHD helpers
    hot = whats_hot()   # Current focus
    cold = whats_cold() # What am I neglecting?

Architecture Decision:
    - Memory V2 is the canonical source of truth
    - Legacy backends are fallback-only (opt-in)
    - All new integrations should use this router
    - See: docs/adr/012-memory-v2-voyage-neon-heat.md
"""

import logging
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryBackend(Enum):
    """Available memory backends."""
    V2 = "memory_v2"           # Default: mem0 + Neon + heat
    LEGACY_CHROMA = "chroma"   # Fallback: SQLite + ChromaDB
    MEMOS = "memos"            # Fallback: MemOS hybrid


# Singleton instances
_v2_service = None
_legacy_service = None
_memos_service = None


def _get_v2_service():
    """Get Memory V2 service (primary)."""
    global _v2_service
    if _v2_service is None:
        try:
            from Tools.memory_v2.service import get_memory_service
            _v2_service = get_memory_service()
            logger.info("Memory V2 service initialized")
        except Exception as e:
            logger.error(f"Failed to init Memory V2: {e}")
            raise
    return _v2_service


def _get_legacy_service():
    """Get legacy SQLite+ChromaDB service (fallback only)."""
    global _legacy_service
    if _legacy_service is None:
        try:
            from Tools.memory.service import get_memory_service
            _legacy_service = get_memory_service()
            logger.info("Legacy memory service initialized (fallback)")
        except Exception as e:
            logger.warning(f"Legacy service unavailable: {e}")
    return _legacy_service


def _get_memos_service():
    """Get MemOS service (fallback only)."""
    global _memos_service
    if _memos_service is None:
        try:
            from memory.services.memory_service import memory_service
            _memos_service = memory_service
            logger.info("MemOS service initialized (fallback)")
        except Exception as e:
            logger.warning(f"MemOS service unavailable: {e}")
    return _memos_service


# =============================================================================
# PRIMARY API - Routes to Memory V2
# =============================================================================

def add_memory(
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    backend: MemoryBackend = MemoryBackend.V2
) -> Dict[str, Any]:
    """
    Add content to memory.

    Uses Memory V2 by default for:
    - Automatic fact extraction via mem0
    - Heat initialization for ranking
    - Deduplication

    Args:
        content: Content to remember
        metadata: Optional metadata (source, client, project, tags)
        backend: Which backend to use (default: V2)

    Returns:
        Result dict with memory ID and status
    """
    if backend == MemoryBackend.V2:
        service = _get_v2_service()
        return service.add(content, metadata)
    elif backend == MemoryBackend.LEGACY_CHROMA:
        service = _get_legacy_service()
        if service:
            import asyncio
            return asyncio.run(service.capture_activity(
                activity_type="memory",
                title=content[:100],
                content=content,
                source=metadata.get("source", "manual") if metadata else "manual",
                metadata=metadata
            ))
        raise RuntimeError("Legacy service unavailable")
    elif backend == MemoryBackend.MEMOS:
        service = _get_memos_service()
        if service:
            return service.add(content, metadata)
        raise RuntimeError("MemOS service unavailable")
    else:
        raise ValueError(f"Unknown backend: {backend}")


def search_memory(
    query: str,
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    backend: MemoryBackend = MemoryBackend.V2
) -> List[Dict[str, Any]]:
    """
    Search memories by semantic similarity.

    Uses Memory V2 by default for:
    - Heat-based re-ranking (similarity * heat * importance)
    - Automatic access boosting
    - Client/project filtering

    Args:
        query: Natural language search query
        limit: Maximum results
        filters: Optional filters (client, source, memory_type)
        backend: Which backend to use (default: V2)

    Returns:
        List of memories with effective_score ranking
    """
    if backend == MemoryBackend.V2:
        service = _get_v2_service()
        return service.search(query, limit, filters)
    elif backend == MemoryBackend.LEGACY_CHROMA:
        service = _get_legacy_service()
        if service:
            import asyncio
            results = asyncio.run(service.search(query, limit=limit))
            # Convert MemoryResult to dict
            return [
                {
                    "id": r.id,
                    "content": r.content,
                    "score": r.relevance_score,
                    "effective_score": r.relevance_score,
                    "source": r.source_type,
                    "metadata": r.metadata
                }
                for r in results
            ]
        return []
    elif backend == MemoryBackend.MEMOS:
        service = _get_memos_service()
        if service:
            return service.search(query, limit, filters)
        return []
    else:
        raise ValueError(f"Unknown backend: {backend}")


def get_context(
    query: str,
    limit: int = 10,
    backend: MemoryBackend = MemoryBackend.V2
) -> str:
    """
    Get formatted context string for Claude prompts.

    Args:
        query: What context is needed for
        limit: Maximum memories to include
        backend: Which backend to use (default: V2)

    Returns:
        Formatted string with heat indicators
    """
    if backend == MemoryBackend.V2:
        service = _get_v2_service()
        return service.get_context_for_query(query, limit)
    elif backend == MemoryBackend.MEMOS:
        service = _get_memos_service()
        if service:
            return service.get_context_for_query(query, limit)
        return "Memory service unavailable."
    else:
        # Legacy doesn't have this method - use V2
        return _get_v2_service().get_context_for_query(query, limit)


# =============================================================================
# ADHD HELPERS - Route to Memory V2
# =============================================================================

def whats_hot(limit: int = 10) -> List[Dict[str, Any]]:
    """
    What's top of mind right now?

    Returns highest-heat memories for current focus context.
    Use for: "What am I focused on?", "Current priorities"
    """
    return _get_v2_service().whats_hot(limit)


def whats_cold(threshold: float = 0.2, limit: int = 10) -> List[Dict[str, Any]]:
    """
    What am I neglecting/forgetting?

    Returns lowest-heat memories that might need attention.
    Use for: "What am I forgetting?", "Neglected clients", "Cold leads"
    """
    return _get_v2_service().whats_cold(threshold, limit)


def pin_memory(memory_id: str) -> bool:
    """Pin a memory so it never decays."""
    return _get_v2_service().pin(memory_id)


def unpin_memory(memory_id: str) -> bool:
    """Unpin a memory to allow normal decay."""
    return _get_v2_service().unpin(memory_id)


# =============================================================================
# STATS AND MANAGEMENT
# =============================================================================

def get_stats(backend: MemoryBackend = MemoryBackend.V2) -> Dict[str, Any]:
    """Get memory system statistics."""
    if backend == MemoryBackend.V2:
        return _get_v2_service().stats()
    elif backend == MemoryBackend.MEMOS:
        service = _get_memos_service()
        if service:
            return service.get_stats()
        return {"error": "MemOS unavailable"}
    else:
        return {"error": "Stats not available for this backend"}


def get_all_memories(limit: int = 100, backend: MemoryBackend = MemoryBackend.V2) -> List[Dict[str, Any]]:
    """Get all memories for migration/export."""
    if backend == MemoryBackend.V2:
        return _get_v2_service().get_all(limit)
    elif backend == MemoryBackend.MEMOS:
        service = _get_memos_service()
        if service:
            return service.get_all(limit)
        return []
    else:
        return []


def delete_memory(memory_id: str, backend: MemoryBackend = MemoryBackend.V2) -> bool:
    """Delete a memory."""
    if backend == MemoryBackend.V2:
        return _get_v2_service().delete(memory_id)
    elif backend == MemoryBackend.MEMOS:
        service = _get_memos_service()
        if service:
            return service.delete(memory_id)
        return False
    else:
        return False


# =============================================================================
# CONVENIENCE ALIASES
# =============================================================================

# Primary exports
get_memory = get_context
remember = add_memory
recall = search_memory

# Quick access to services
def get_v2():
    """Get raw Memory V2 service for advanced operations."""
    return _get_v2_service()

def get_legacy():
    """Get raw legacy service (fallback only)."""
    return _get_legacy_service()


if __name__ == "__main__":
    # Self-test
    print("Memory Router initialized")
    print(f"Backend: Memory V2 (primary)")

    try:
        service = _get_v2_service()
        stats = service.stats()
        print(f"Stats: {stats}")
    except Exception as e:
        print(f"Error: {e}")
