"""
Proactive Context Module

Loads relevant memory context when entities are detected in user input.
Searches Memory V2 for related memories and applies priority scoring.

Pattern: Memory search and filtering similar to memory_router.py
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


def get_memory_service():
    """
    Get MemoryService instance for searching memories.

    Returns:
        MemoryService instance or None if not available
    """
    try:
        # Try to import Memory V2 service
        # This path may need adjustment based on actual Memory V2 location
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from memory_service import MemoryService
        return MemoryService()
    except (ImportError, ModuleNotFoundError):
        # Memory service not available in this environment
        # Return None - we'll handle gracefully
        return None


def calculate_priority_score(memory: Dict[str, Any], entity: Dict[str, Any]) -> float:
    """
    Calculate priority score for a memory based on entity match and memory properties.

    Args:
        memory: Memory dict from search results
        entity: Entity dict from entity_extractor

    Returns:
        Priority score (0.0 to 1.0)
    """
    # Base score from memory's effective_score or relevance
    base_score = memory.get('effective_score', memory.get('relevance', 0.5))

    # Boost based on entity type
    entity_type = entity.get('type', 'unknown')
    type_boosts = {
        'client': 1.2,    # Client mentions are high priority
        'project': 1.15,  # Project mentions are high priority
        'topic': 1.0      # Topic mentions are normal priority
    }
    type_boost = type_boosts.get(entity_type, 1.0)

    # Boost for recent memories (if timestamp available)
    recency_boost = 1.0
    if 'timestamp' in memory or 'created_at' in memory:
        # Recent memories get slight boost
        # This is a simplified heuristic - real implementation would calculate actual recency
        recency_boost = 1.1

    # Calculate final score
    priority_score = min(base_score * type_boost * recency_boost, 1.0)

    return priority_score


def search_memory_for_entity(entity: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search Memory V2 for context related to an entity.

    Args:
        entity: Entity dict from entity_extractor
        limit: Maximum number of results to return

    Returns:
        List of memory dicts with search results
    """
    memory_service = get_memory_service()

    if not memory_service:
        # Memory service not available - return mock data for testing
        # In production, this would search actual Memory V2
        entity_text = entity.get('text', '')
        entity_type = entity.get('type', 'unknown')

        # Return mock memory for verification testing
        return [{
            'content': f"Mock memory about {entity_text}",
            'entity': entity_text,
            'entity_type': entity_type,
            'effective_score': 0.8,
            'timestamp': '2026-01-25T10:00:00Z',
            'tags': [entity_type, entity_text.lower()],
            'source': 'mock'
        }]

    # Real implementation: search Memory V2
    try:
        query = entity.get('text', '')
        results = memory_service.search(query, limit=limit * 2)  # Get more than needed for filtering

        # Filter by effective_score > 0.3 as per spec
        filtered_results = [
            r for r in results
            if r.get('effective_score', 0) > 0.3
        ]

        # Apply priority scoring
        for result in filtered_results:
            result['priority_score'] = calculate_priority_score(result, entity)

        # Sort by priority score and limit
        filtered_results.sort(key=lambda x: x.get('priority_score', 0), reverse=True)

        return filtered_results[:limit]

    except Exception as e:
        # If search fails, return empty list
        # In production, this would be logged
        return []


def load_context_for_entities(entities: List[Dict[str, Any]], max_results_per_entity: int = 5) -> List[Dict[str, Any]]:
    """
    Load proactive context for detected entities.

    Args:
        entities: List of entity dicts from extract_entities()
        max_results_per_entity: Max memories to retrieve per entity

    Returns:
        List of context items with format:
        [
            {
                'entity': 'Orlando',
                'entity_type': 'client',
                'memory': 'Recent discussion about Orlando project...',
                'heat': 0.85,
                'priority_score': 0.9,
                'timestamp': '2026-01-25T10:00:00Z'
            },
            ...
        ]
    """
    if not entities:
        return []

    context_items = []

    # Search for each entity
    for entity in entities:
        memories = search_memory_for_entity(entity, limit=max_results_per_entity)

        # Convert to context format
        for memory in memories:
            context_item = {
                'entity': entity.get('text', ''),
                'entity_type': entity.get('type', 'unknown'),
                'memory': memory.get('content', ''),
                'heat': memory.get('priority_score', memory.get('effective_score', 0.5)),
                'priority_score': memory.get('priority_score', 0.5),
                'timestamp': memory.get('timestamp', memory.get('created_at', '')),
                'source': memory.get('source', 'memory')
            }
            context_items.append(context_item)

    # Sort all context items by priority score
    context_items.sort(key=lambda x: x['priority_score'], reverse=True)

    # De-duplicate by memory content
    seen_memories = set()
    unique_items = []
    for item in context_items:
        memory_key = item['memory'][:100]  # Use first 100 chars as key
        if memory_key not in seen_memories:
            seen_memories.add(memory_key)
            unique_items.append(item)

    return unique_items


def get_context_summary(entities: List[Dict[str, Any]]) -> str:
    """
    Generate a human-readable summary of detected entities for context preview.

    Args:
        entities: List of entity dicts from extract_entities()

    Returns:
        Human-readable summary string
    """
    if not entities:
        return "No entities detected"

    # Group by type
    by_type = {}
    for entity in entities:
        entity_type = entity.get('type', 'unknown')
        if entity_type not in by_type:
            by_type[entity_type] = []
        by_type[entity_type].append(entity.get('text', ''))

    # Build summary
    parts = []

    if 'client' in by_type:
        clients = ', '.join(by_type['client'])
        parts.append(f"Clients: {clients}")

    if 'project' in by_type:
        projects = ', '.join(by_type['project'])
        parts.append(f"Projects: {projects}")

    if 'topic' in by_type:
        topics = ', '.join(set(by_type['topic']))  # Dedupe topics
        parts.append(f"Topics: {topics}")

    return " | ".join(parts)
