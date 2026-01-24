"""
MCP Tools for Thanos Memory V2.

These tools can be exposed via an MCP server for Claude Code integration.

Tools:
- memory_search: Search memories with heat-based ranking
- memory_add: Add a new memory
- memory_context: Get formatted context for prompts
- memory_whats_hot: Get current focus memories
- memory_whats_cold: Get neglected memories
- memory_pin: Pin a critical memory
"""

from typing import List, Dict, Any, Optional
from .service import get_memory_service
from .heat import get_heat_service


def memory_search(
    query: str,
    limit: int = 10,
    client: str = None,
    project: str = None,
    domain: str = None,
    source: str = None
) -> List[Dict[str, Any]]:
    """
    Search Jeremy's memories for relevant context.

    Uses semantic similarity search, re-ranked by heat score.
    Recent and frequently-accessed memories rank higher.

    Ranking Formula:
        effective_score = (0.6 * similarity) + (0.3 * heat) + (0.1 * importance)

    Args:
        query: Natural language search query (e.g., "Orlando project status")
        limit: Maximum results to return (default 10)
        client: Optional filter by client name (e.g., "Orlando", "Kentucky")
        project: Optional filter by project (e.g., "ScottCare", "VersaCare")
        domain: Optional filter by domain ("work" or "personal")
        source: Optional filter by source (hey_pocket, telegram, manual)

    Returns:
        List of relevant memories with scores and metadata

    Examples:
        memory_search("API integration")  # Search all memories
        memory_search("API integration", client="Orlando")  # Within client context
        memory_search("authentication", project="VersaCare")  # Within project
        memory_search("family plans", domain="personal")  # Personal only
    """
    service = get_memory_service()
    return service.search(
        query,
        limit=limit,
        client=client,
        project=project,
        domain=domain,
        source=source
    )


def memory_add(
    content: str,
    source: str = "manual",
    memory_type: str = "note",
    client: str = None,
    project: str = None,
    importance: float = 1.0
) -> Dict[str, Any]:
    """
    Add a new memory directly.

    Content will be processed for fact extraction and stored with
    automatic embedding generation.

    Args:
        content: The content to remember
        source: Where this came from (manual, observation, hey_pocket, telegram)
        memory_type: Category (note, fact, goal, decision, pattern, etc.)
        client: Optional client association
        project: Optional project association
        importance: Manual importance multiplier (0.5 - 2.0)

    Returns:
        Result of memory addition including ID

    Example:
        memory_add("Orlando wants ClinDoc by end of Q1",
                   source="meeting", client="Orlando", memory_type="fact")
    """
    service = get_memory_service()

    metadata = {
        "source": source,
        "type": memory_type,
        "importance": importance
    }

    if client:
        metadata["client"] = client
    if project:
        metadata["project"] = project

    return service.add(content, metadata=metadata)


def memory_context(query: str, limit: int = 10) -> str:
    """
    Get formatted context for a query (for prompt injection).

    Returns a formatted string of relevant memories suitable for
    including in Claude prompts. Each memory includes heat indicator.

    Args:
        query: What context is needed for
        limit: Maximum memories to include

    Returns:
        Formatted string of relevant memories with heat indicators:
        🔥 = hot (active focus)
        • = warm (normal)
        ❄️ = cold (neglected)

    Example:
        context = memory_context("Orlando project")
        prompt = f"{context}\\n\\nBased on this, what should I focus on?"
    """
    service = get_memory_service()
    return service.get_context_for_query(query, limit=limit)


def memory_whats_hot(limit: int = 10) -> List[Dict[str, Any]]:
    """
    What's top of mind? Returns highest-heat memories.

    Use for:
    - "What am I focused on?"
    - "Current priorities"
    - "Recent context"

    Args:
        limit: Maximum results (default 10)

    Returns:
        List of highest-heat memories with full metadata
    """
    service = get_memory_service()
    return service.whats_hot(limit)


def memory_whats_cold(
    threshold: float = 0.3,
    limit: int = 10,
    min_age_days: int = 7
) -> List[Dict[str, Any]]:
    """
    What am I neglecting? Returns lowest-heat memories.

    Use for:
    - "What am I forgetting?"
    - "Neglected tasks/clients"
    - "Cold leads"
    - "Things I should revisit"

    Great for ADHD review - surfaces things that may have slipped through the cracks.

    Args:
        threshold: Heat threshold (memories below this, default 0.3)
        limit: Maximum results (default 10)
        min_age_days: Exclude memories newer than this (default 7 days).
                     New memories are cold because they're new, not neglected.

    Returns:
        List of cold memories that may need attention
    """
    service = get_memory_service()
    return service.whats_cold(threshold, limit, min_age_days)


def memory_pin(memory_id: str) -> Dict[str, Any]:
    """
    Pin a memory so it never decays (critical info).

    Use for:
    - Important personal facts
    - Critical client requirements
    - Key decisions that must not be forgotten

    Args:
        memory_id: UUID of the memory to pin

    Returns:
        Success status
    """
    service = get_memory_service()
    success = service.pin(memory_id)
    return {"pinned": memory_id, "success": success}


def memory_unpin(memory_id: str) -> Dict[str, Any]:
    """
    Unpin a memory to allow normal decay.

    Args:
        memory_id: UUID of the memory to unpin

    Returns:
        Success status
    """
    service = get_memory_service()
    success = service.unpin(memory_id)
    return {"unpinned": memory_id, "success": success}


def memory_stats() -> Dict[str, Any]:
    """
    Get memory system statistics.

    Returns:
        Statistics including:
        - total memories
        - average heat
        - hot/cold counts
        - unique clients/projects
    """
    service = get_memory_service()
    return service.stats()


def memory_heat_report() -> str:
    """
    Generate a formatted heat report.

    Shows hot and cold memories in a readable format
    for quick system health check.

    Returns:
        Formatted report string
    """
    heat_service = get_heat_service()
    return heat_service.heat_report()


def memory_delete(memory_id: str) -> Dict[str, Any]:
    """
    Delete a memory.

    Warning: This is permanent!

    Args:
        memory_id: UUID of the memory to delete

    Returns:
        Success status
    """
    service = get_memory_service()
    success = service.delete(memory_id)
    return {"deleted": memory_id, "success": success}


def memory_boost_entity(entity: str) -> Dict[str, Any]:
    """
    Manually boost memories related to an entity (fuzzy match).

    Useful when you know you'll be working on a client/project
    and want to prime the memory system.

    Args:
        entity: Client name, project name, or tag (uses ILIKE fuzzy matching)

    Returns:
        Number of memories boosted
    """
    heat_service = get_heat_service()
    count = heat_service.boost_related(entity, "access")
    return {"entity": entity, "memories_boosted": count}


def memory_boost_context(
    filter_key: str,
    filter_value: str,
    boost: float = 0.15
) -> Dict[str, Any]:
    """
    Boost all memories matching a specific context (exact match).

    Use when switching to work on a specific client/project to surface
    all related memories in subsequent searches.

    Args:
        filter_key: The metadata field to match. Allowed values:
                   "client", "project", "domain", "source", "type", "category"
        filter_value: Exact value to match (e.g., "Orlando", "VersaCare", "work")
        boost: Heat amount to add (default 0.15, max effect limited by max_heat=2.0)

    Returns:
        Number of memories boosted

    Examples:
        memory_boost_context("client", "Orlando")  # Starting Orlando work
        memory_boost_context("project", "VersaCare", boost=0.2)  # Deep dive VersaCare
        memory_boost_context("domain", "work")  # Beginning work day
    """
    heat_service = get_heat_service()
    count = heat_service.boost_by_filter(filter_key, filter_value, boost)
    return {
        "filter_key": filter_key,
        "filter_value": filter_value,
        "boost": boost,
        "memories_boosted": count
    }


# Export all tools for MCP registration
MCP_TOOLS = [
    memory_search,
    memory_add,
    memory_context,
    memory_whats_hot,
    memory_whats_cold,
    memory_pin,
    memory_unpin,
    memory_stats,
    memory_heat_report,
    memory_delete,
    memory_boost_entity,
    memory_boost_context,
]

__all__ = [
    'memory_search',
    'memory_add',
    'memory_context',
    'memory_whats_hot',
    'memory_whats_cold',
    'memory_pin',
    'memory_unpin',
    'memory_stats',
    'memory_heat_report',
    'memory_delete',
    'memory_boost_entity',
    'memory_boost_context',
    'MCP_TOOLS',
]
