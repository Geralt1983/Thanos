"""
Thanos Intelligent Memory System.

Captures daily activities, detects struggles, recognizes values,
and provides temporal intelligence for natural language queries.

Architecture:
- SQLite for structured temporal data
- ChromaDB for semantic vector search
- Automatic capture through event hooks
- Natural language query interface

Usage:
    from Tools.memory import MemoryService, get_memory_service

    memory = get_memory_service()

    # Capture activity
    await memory.capture_activity(
        activity_type="brain_dump",
        title="Planning session",
        content="Thinking about the Memphis project...",
        source="telegram"
    )

    # Search memories
    results = await memory.search("Memphis project planning")

    # Get day summary
    summary = await memory.get_day(date.today())

    # Natural language query
    result = await memory.query("What did I do last Tuesday?")
"""

from .models import (
    Activity,
    Struggle,
    UserValue,
    Relationship,
    DaySummary,
    WeekSummary,
    MemoryResult,
    QueryResult,
)
from .service import MemoryService, get_memory_service
from .capture import MemoryCapturePipeline
from .struggle_detector import StruggleDetector
from .value_detector import ValueDetector
from .query_parser import TemporalQueryParser

__all__ = [
    # Models
    "Activity",
    "Struggle",
    "UserValue",
    "Relationship",
    "DaySummary",
    "WeekSummary",
    "MemoryResult",
    "QueryResult",
    # Service
    "MemoryService",
    "get_memory_service",
    # Components
    "MemoryCapturePipeline",
    "StruggleDetector",
    "ValueDetector",
    "TemporalQueryParser",
]
