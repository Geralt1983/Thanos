"""
Thanos Memory V2 - Cloud-first memory with heat decay.

Architecture:
- mem0: Automatic fact extraction and deduplication
- Voyage AI: Embeddings (voyage-2, 1536 dimensions)
- Neon pgvector: Vector storage (serverless PostgreSQL)
- Heat decay: Recent/accessed memories surface naturally

Usage:
    from Tools.memory_v2 import memory_service, heat_service

    # Add a memory
    memory_service.add("Had a great meeting with Orlando team",
                       metadata={"source": "manual", "client": "Orlando"})

    # Search (ranked by similarity * heat * importance)
    results = memory_service.search("Orlando project status")

    # ADHD helpers
    hot = memory_service.whats_hot(10)   # Current focus
    cold = memory_service.whats_cold()    # What am I neglecting?
"""

from .service import MemoryService, get_memory_service
from .heat import HeatService, get_heat_service
from .config import MEM0_CONFIG, HEAT_CONFIG

__all__ = [
    'MemoryService',
    'get_memory_service',
    'HeatService',
    'get_heat_service',
    'MEM0_CONFIG',
    'HEAT_CONFIG',
]

# Singleton instances
memory_service = None
heat_service = None

def init():
    """Initialize memory services."""
    global memory_service, heat_service
    memory_service = get_memory_service()
    heat_service = get_heat_service()
    return memory_service, heat_service
