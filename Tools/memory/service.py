"""
Memory Service for Thanos Memory System.

Provides the high-level API for capturing, querying, and managing
the intelligent memory system. Coordinates SQLite storage with
ChromaDB vector search for hybrid retrieval.
"""

import logging
import time
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from .models import (
    Activity, Struggle, UserValue, Relationship,
    DaySummary, WeekSummary, MemoryResult, QueryResult, ContextualSurface
)
from .store import MemoryStore
from .capture import MemoryCapturePipeline, CaptureResult
from .query_parser import TemporalQueryParser, TemporalQuery, QueryType
from .struggle_detector import StruggleDetector
from .value_detector import ValueDetector

logger = logging.getLogger(__name__)

# Singleton instance
_memory_service: Optional['MemoryService'] = None


def get_memory_service(
    db_path: Optional[str] = None,
    chroma_path: Optional[str] = None,
    enable_ai: bool = True
) -> 'MemoryService':
    """
    Get or create the singleton MemoryService instance.

    Args:
        db_path: Path to SQLite database.
        chroma_path: Path to ChromaDB storage.
        enable_ai: Whether to enable AI-powered detection.

    Returns:
        MemoryService instance.
    """
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService(
            db_path=db_path,
            chroma_path=chroma_path,
            enable_ai=enable_ai
        )
    return _memory_service


class MemoryService:
    """
    High-level service for the Thanos memory system.

    Provides:
    - Activity capture and storage
    - Natural language querying
    - Contextual memory surfacing
    - Struggle and value tracking
    - Day/week summaries

    Example:
        memory = MemoryService()

        # Capture activity
        await memory.capture_activity(
            activity_type="brain_dump",
            title="Planning session",
            content="Working on Memphis architecture...",
            source="telegram"
        )

        # Natural language query
        result = await memory.query("What did I do last Tuesday?")

        # Get day summary
        summary = await memory.get_day(date.today())
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        chroma_path: Optional[str] = None,
        enable_ai: bool = True
    ):
        """
        Initialize the memory service.

        Args:
            db_path: Path to SQLite database.
            chroma_path: Path to ChromaDB storage.
            enable_ai: Whether to enable AI-powered detection.
        """
        self.db_path = db_path
        self.chroma_path = chroma_path
        self.enable_ai = enable_ai

        # Initialize components
        self.store = MemoryStore(db_path)
        self.pipeline = MemoryCapturePipeline(
            db_path=db_path,
            chroma_path=chroma_path,
            enable_ai=enable_ai
        )
        self.query_parser = TemporalQueryParser()
        self.struggle_detector = StruggleDetector()
        self.value_detector = ValueDetector()

        # Lazy-loaded ChromaDB adapter
        self._chroma_adapter = None

        logger.info("MemoryService initialized")

    @property
    def chroma_adapter(self):
        """Lazy-load ChromaDB adapter."""
        if self._chroma_adapter is None:
            try:
                from Tools.adapters.chroma_adapter import ChromaAdapter
                self._chroma_adapter = ChromaAdapter(persist_directory=self.chroma_path)
            except ImportError:
                logger.warning("ChromaDB adapter not available")
        return self._chroma_adapter

    # =========================================================================
    # Capture API
    # =========================================================================

    async def capture_activity(
        self,
        activity_type: str,
        title: str,
        content: Optional[str] = None,
        source: str = "system",
        source_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> CaptureResult:
        """
        Capture an activity through the memory pipeline.

        This automatically:
        - Classifies the event
        - Extracts context (project, domain, entities)
        - Detects struggles
        - Detects values
        - Generates embeddings
        - Stores in SQLite and ChromaDB

        Args:
            activity_type: Type of activity (brain_dump, task_complete, etc.)
            title: Short title for the activity.
            content: Full content (for brain dumps, conversations).
            source: Source of the event (telegram, cli, system).
            source_context: Additional source-specific context.
            metadata: Additional metadata.
            **kwargs: Additional fields (project, domain, etc.)

        Returns:
            CaptureResult with IDs and detection results.
        """
        return await self.pipeline.capture(
            event_type=activity_type,
            title=title,
            content=content,
            source=source,
            source_context=source_context,
            metadata=metadata,
            **kwargs
        )

    async def capture_brain_dump(
        self,
        content: str,
        source: str = "telegram",
        **kwargs
    ) -> CaptureResult:
        """
        Capture a brain dump with FULL extraction pipeline.

        This uses the BrainDumpIngester for:
        - Entity extraction (people, places, things)
        - Task extraction (implicit todos)
        - Deadline detection
        - Blocker detection
        - Energy state detection
        - Full vectorization
        - Pattern linking

        Returns CaptureResult for compatibility, but the real extraction
        data is in the BrainDumpExtraction returned by the ingester.
        """
        from .brain_dump_ingester import get_brain_dump_ingester

        # Use the full ingester pipeline
        ingester = get_brain_dump_ingester()
        extraction = await ingester.ingest(content, source)

        # Also run through the standard pipeline for struggle/value detection
        result = await self.capture_activity(
            activity_type="brain_dump",
            title=content[:100] + ("..." if len(content) > 100 else ""),
            content=content,
            source=source,
            metadata={
                'extraction': {
                    'entities': [e.name for e in extraction.entities],
                    'tasks': [t.title for t in extraction.tasks],
                    'deadlines': [d.text for d in extraction.deadlines],
                    'blockers': extraction.blockers,
                    'energy': extraction.energy.level if extraction.energy else None,
                    'domains': extraction.domains,
                    'values': extraction.values_detected,
                    'struggles': extraction.struggles_detected,
                }
            },
            **kwargs
        )

        # Log extraction summary
        logger.info(
            f"Brain dump captured: {len(extraction.entities)} entities, "
            f"{len(extraction.tasks)} tasks, {len(extraction.deadlines)} deadlines, "
            f"energy={extraction.energy.level if extraction.energy else 'unknown'}"
        )

        return result

    async def capture_task_completion(
        self,
        task_id: str,
        title: str,
        duration_minutes: Optional[int] = None,
        project: Optional[str] = None,
        **kwargs
    ) -> CaptureResult:
        """Convenience method for capturing task completions."""
        return await self.capture_activity(
            activity_type="task_complete",
            title=f"Completed: {title}",
            task_id=task_id,
            duration_minutes=duration_minutes,
            project=project,
            **kwargs
        )

    async def capture_command(
        self,
        command: str,
        result: Optional[str] = None,
        duration_ms: Optional[float] = None,
        source: str = "cli",
        **kwargs
    ) -> CaptureResult:
        """Convenience method for capturing command executions."""
        return await self.capture_activity(
            activity_type="command",
            title=f"Command: {command}",
            content=result,
            source=source,
            metadata={"command": command, "duration_ms": duration_ms},
            **kwargs
        )

    # =========================================================================
    # Query API
    # =========================================================================

    async def query(self, query_text: str) -> QueryResult:
        """
        Execute a natural language memory query.

        Supports queries like:
        - "What did I do last Tuesday?"
        - "When did I last work on Memphis?"
        - "What was I struggling with yesterday?"
        - "Show me my productivity pattern this week"

        Args:
            query_text: Natural language query.

        Returns:
            QueryResult with results and summary.
        """
        start_time = time.time()

        # Parse the query
        parsed = self.query_parser.parse(query_text)

        # Execute based on query type
        if parsed.query_type == QueryType.DAY_RECALL:
            results = await self._query_day_recall(parsed)
        elif parsed.query_type == QueryType.PROJECT_HISTORY:
            results = await self._query_project_history(parsed)
        elif parsed.query_type == QueryType.STRUGGLE_RECALL:
            results = await self._query_struggle_recall(parsed)
        elif parsed.query_type == QueryType.ACCOMPLISHMENT:
            results = await self._query_accomplishments(parsed)
        elif parsed.query_type == QueryType.PATTERN_ANALYSIS:
            results = await self._query_patterns(parsed)
        elif parsed.query_type == QueryType.ENTITY_QUERY:
            results = await self._query_entity(parsed)
        else:
            results = await self._query_general(parsed)

        execution_time = (time.time() - start_time) * 1000

        # Generate summary
        summary = self._generate_query_summary(parsed, results)

        return QueryResult(
            query=query_text,
            query_type=parsed.query_type.value,
            results=results,
            summary=summary,
            date_range=parsed.date_range,
            filters_applied={
                'project': parsed.project,
                'entity': parsed.entity,
                'domain': parsed.domain,
                'search_terms': parsed.search_terms
            },
            total_matches=len(results),
            execution_time_ms=round(execution_time, 2)
        )

    async def _query_day_recall(self, parsed: TemporalQuery) -> List[MemoryResult]:
        """Query activities for a specific day or date range."""
        if parsed.specific_date:
            activities = await self.store.get_activities_by_date(
                parsed.specific_date,
                project=parsed.project,
                domain=parsed.domain,
                limit=parsed.limit
            )
        elif parsed.date_range:
            activities = await self.store.get_activities_by_range(
                parsed.date_range[0],
                parsed.date_range[1],
                project=parsed.project,
                domain=parsed.domain,
                limit=parsed.limit
            )
        else:
            # Default to today
            activities = await self.store.get_activities_by_date(
                date.today(),
                project=parsed.project,
                domain=parsed.domain,
                limit=parsed.limit
            )

        return [self._activity_to_result(a) for a in activities]

    async def _query_project_history(self, parsed: TemporalQuery) -> List[MemoryResult]:
        """Query project-specific history."""
        project = parsed.project or (parsed.search_terms[0] if parsed.search_terms else None)
        if not project:
            return []

        activities = await self.store.get_activities_by_range(
            date.today() - timedelta(days=90),
            date.today(),
            project=project,
            limit=parsed.limit
        )

        return [self._activity_to_result(a) for a in activities]

    async def _query_struggle_recall(self, parsed: TemporalQuery) -> List[MemoryResult]:
        """Query struggles for a time period."""
        if parsed.specific_date:
            target_date = parsed.specific_date
        elif parsed.date_range:
            target_date = parsed.date_range[0]  # Use start date
        else:
            target_date = date.today() - timedelta(days=7)

        struggles = await self.store.get_struggles_by_date(
            target_date,
            limit=parsed.limit
        )

        return [self._struggle_to_result(s) for s in struggles]

    async def _query_accomplishments(self, parsed: TemporalQuery) -> List[MemoryResult]:
        """Query task completions and accomplishments."""
        if parsed.specific_date:
            start = parsed.specific_date
            end = parsed.specific_date
        elif parsed.date_range:
            start, end = parsed.date_range
        else:
            start = date.today() - timedelta(days=7)
            end = date.today()

        activities = await self.store.get_activities_by_range(
            start, end,
            activity_types=['task_complete', 'commitment_fulfilled'],
            project=parsed.project,
            limit=parsed.limit
        )

        return [self._activity_to_result(a) for a in activities]

    async def _query_patterns(self, parsed: TemporalQuery) -> List[MemoryResult]:
        """Query productivity and struggle patterns."""
        # Get activity statistics
        stats = await self.store.get_activity_stats(days=30)

        # Get struggle patterns
        struggle_patterns = await self.store.get_struggle_patterns(days=30)

        # Convert to results
        results = []

        # Add productivity pattern result
        peak_hours = sorted(
            stats['by_hour'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        results.append(MemoryResult(
            id="pattern_productivity",
            content=f"Peak productivity hours: {', '.join(f'{h}:00' for h, _ in peak_hours)}. "
                    f"Average {stats['avg_per_day']} activities per day. "
                    f"Most active on {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][max(stats['by_day_of_week'].items(), key=lambda x: x[1])[0]] if stats['by_day_of_week'] else 'unknown'}.",
            source_type="pattern",
            relevance_score=1.0,
            metadata={'stats': stats}
        ))

        # Add struggle pattern result
        if struggle_patterns['total_struggles'] > 0:
            common_type = max(
                struggle_patterns['by_type'].items(),
                key=lambda x: x[1]
            )[0] if struggle_patterns['by_type'] else 'unknown'

            results.append(MemoryResult(
                id="pattern_struggles",
                content=f"Most common struggle: {common_type}. "
                        f"Total struggles in last 30 days: {struggle_patterns['total_struggles']}.",
                source_type="pattern",
                relevance_score=0.9,
                metadata={'patterns': struggle_patterns}
            ))

        return results

    async def _query_entity(self, parsed: TemporalQuery) -> List[MemoryResult]:
        """Query information about an entity (person, project)."""
        entity = parsed.entity or (parsed.search_terms[0] if parsed.search_terms else None)
        if not entity:
            return []

        results = []

        # Check relationships
        relationship = await self.store.get_relationship(entity)
        if relationship:
            results.append(MemoryResult(
                id=relationship.id,
                content=f"{entity}: {relationship.entity_type}. "
                        f"Mentioned {relationship.mention_count} times. "
                        f"{'Sentiment: ' + relationship.sentiment_trend if relationship.sentiment_trend else ''}",
                source_type="relationship",
                relevance_score=1.0,
                entity=entity,
                metadata=relationship.to_dict()
            ))

        # Search activities mentioning this entity
        activities = await self.store.search_activities(entity, limit=10)
        for a in activities:
            results.append(self._activity_to_result(a, relevance=0.8))

        return results

    async def _query_general(self, parsed: TemporalQuery) -> List[MemoryResult]:
        """Execute a general search query."""
        results = []

        # FTS search in SQLite
        if parsed.search_terms:
            search_query = ' '.join(parsed.search_terms)
            activities = await self.store.search_activities(search_query, limit=parsed.limit)
            results.extend([self._activity_to_result(a) for a in activities])

        # Vector search in ChromaDB if available
        if self.chroma_adapter and parsed.original_query:
            try:
                chroma_results = await self.chroma_adapter.call_tool(
                    "search_memory",
                    {
                        "query": parsed.original_query,
                        "collection": "activities",
                        "n_results": min(10, parsed.limit)
                    }
                )
                if chroma_results.success and chroma_results.data:
                    for item in chroma_results.data.get('results', []):
                        results.append(MemoryResult(
                            id=item.get('id', 'unknown'),
                            content=item.get('content', ''),
                            relevance_score=item.get('score', 0.5),
                            source_type="vector_search",
                            metadata=item.get('metadata')
                        ))
            except Exception as e:
                logger.warning(f"ChromaDB search failed: {e}")

        # Deduplicate and sort by relevance
        seen_ids = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x.relevance_score, reverse=True):
            if r.id not in seen_ids:
                seen_ids.add(r.id)
                unique_results.append(r)

        return unique_results[:parsed.limit]

    def _activity_to_result(self, activity: Activity, relevance: float = 1.0) -> MemoryResult:
        """Convert an Activity to a MemoryResult."""
        return MemoryResult(
            id=activity.id,
            content=activity.content or activity.title,
            relevance_score=relevance,
            source_type="activity",
            timestamp=activity.timestamp,
            project=activity.project,
            domain=activity.domain,
            metadata={'activity_type': activity.activity_type}
        )

    def _struggle_to_result(self, struggle: Struggle) -> MemoryResult:
        """Convert a Struggle to a MemoryResult."""
        return MemoryResult(
            id=struggle.id,
            content=f"{struggle.struggle_type}: {struggle.description or struggle.title}",
            relevance_score=struggle.confidence,
            source_type="struggle",
            timestamp=struggle.detected_at,
            project=struggle.project,
            domain=struggle.domain,
            metadata={
                'struggle_type': struggle.struggle_type,
                'resolved': struggle.resolved
            }
        )

    def _generate_query_summary(
        self,
        parsed: TemporalQuery,
        results: List[MemoryResult]
    ) -> str:
        """Generate a human-readable summary of query results."""
        date_desc = self.query_parser.get_date_description(parsed)

        if not results:
            return f"No memories found for {date_desc}."

        if parsed.query_type == QueryType.DAY_RECALL:
            return f"Found {len(results)} activities for {date_desc}."

        elif parsed.query_type == QueryType.STRUGGLE_RECALL:
            return f"Found {len(results)} struggles recorded for {date_desc}."

        elif parsed.query_type == QueryType.ACCOMPLISHMENT:
            return f"Completed {len(results)} tasks/commitments during {date_desc}."

        elif parsed.query_type == QueryType.PATTERN_ANALYSIS:
            return f"Analyzed patterns from the past 30 days."

        elif parsed.query_type == QueryType.ENTITY_QUERY:
            return f"Found {len(results)} memories related to '{parsed.entity or 'entity'}'."

        else:
            return f"Found {len(results)} relevant memories."

    # =========================================================================
    # Search API
    # =========================================================================

    async def search(
        self,
        query: str,
        limit: int = 20,
        use_vector: bool = True
    ) -> List[MemoryResult]:
        """
        Search memories using both FTS and vector search.

        Args:
            query: Search query.
            limit: Maximum results.
            use_vector: Whether to include vector search results.

        Returns:
            List of matching MemoryResults.
        """
        results = []

        # FTS search
        activities = await self.store.search_activities(query, limit=limit)
        for a in activities:
            results.append(self._activity_to_result(a))

        # Vector search
        if use_vector and self.chroma_adapter:
            try:
                chroma_results = await self.chroma_adapter.call_tool(
                    "search_memory",
                    {
                        "query": query,
                        "collection": "activities",
                        "n_results": limit
                    }
                )
                if chroma_results.success:
                    for item in chroma_results.data.get('results', []):
                        results.append(MemoryResult(
                            id=item.get('id', 'unknown'),
                            content=item.get('content', ''),
                            relevance_score=item.get('score', 0.5),
                            source_type="vector_search",
                            metadata=item.get('metadata')
                        ))
            except Exception as e:
                logger.warning(f"Vector search failed: {e}")

        # Deduplicate and sort
        seen = set()
        unique = []
        for r in sorted(results, key=lambda x: x.relevance_score, reverse=True):
            if r.id not in seen:
                seen.add(r.id)
                unique.append(r)

        return unique[:limit]

    # =========================================================================
    # Contextual Surfacing
    # =========================================================================

    async def get_contextual_memories(
        self,
        current_text: str,
        project: Optional[str] = None,
        entity: Optional[str] = None
    ) -> ContextualSurface:
        """
        Get contextually relevant memories for the current conversation.

        This surfaces relevant past activities, struggles, and relationships
        based on the current conversation context.

        Args:
            current_text: Current conversation text.
            project: Current project context.
            entity: Current entity being discussed.

        Returns:
            ContextualSurface with relevant memories.
        """
        # Detect entities in current text
        entities = self.value_detector.detect_entities(current_text)
        entity_names = [e.name for e in entities] if entities else []

        if entity:
            entity_names.append(entity)

        # Search for relevant memories
        related = await self.search(current_text, limit=5)

        # Check for struggle patterns
        struggle_pattern = None
        struggle_result = self.struggle_detector.detect(
            current_text,
            context={'project': project},
            use_ai=False  # Use fast pattern matching only
        )
        if struggle_result and struggle_result.struggle_detected:
            # Check if this is a recurring struggle
            recent_struggles = await self.store.get_struggles_by_date(
                date.today() - timedelta(days=7)
            )
            matching = [
                s for s in recent_struggles
                if s.struggle_type == struggle_result.struggle_type
            ]
            if matching:
                struggle_pattern = matching[0]

        return ContextualSurface(
            primary_memory=related[0] if related else None,
            related_memories=related[1:5] if len(related) > 1 else None,
            entities_found=entity_names if entity_names else None,
            struggle_pattern=struggle_pattern
        )

    # =========================================================================
    # Summary API
    # =========================================================================

    async def get_day(self, target_date: date) -> Optional[DaySummary]:
        """
        Get summary for a specific day.

        Args:
            target_date: Date to get summary for.

        Returns:
            DaySummary or None if no activities.
        """
        return await self.store.get_day_summary(target_date)

    async def get_today(self) -> Optional[DaySummary]:
        """Get today's summary."""
        return await self.get_day(date.today())

    async def get_yesterday(self) -> Optional[DaySummary]:
        """Get yesterday's summary."""
        return await self.get_day(date.today() - timedelta(days=1))

    async def get_week(
        self,
        week_start: Optional[date] = None
    ) -> WeekSummary:
        """
        Get summary for a week.

        Args:
            week_start: Start of week (defaults to current week's Monday).

        Returns:
            WeekSummary.
        """
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        # Get daily summaries
        daily_summaries = []
        current = week_start
        while current <= week_end:
            summary = await self.get_day(current)
            if summary:
                daily_summaries.append(summary)
            current += timedelta(days=1)

        # Calculate aggregates
        total_tasks = sum(s.tasks_completed for s in daily_summaries)
        total_struggles = sum(s.struggles_detected for s in daily_summaries)
        total_activities = sum(s.total_activities for s in daily_summaries)

        # Find busiest/quietest days
        if daily_summaries:
            busiest = max(daily_summaries, key=lambda s: s.total_activities)
            quietest = min(daily_summaries, key=lambda s: s.total_activities)
            busiest_day = busiest.date.weekday()
            quietest_day = quietest.date.weekday()
        else:
            busiest_day = None
            quietest_day = None

        # Collect projects
        all_projects = []
        for s in daily_summaries:
            if s.projects_touched:
                all_projects.extend(s.projects_touched)
        primary_projects = list(set(all_projects))[:5]

        return WeekSummary(
            week_start=week_start,
            week_end=week_end,
            total_tasks_completed=total_tasks,
            total_struggles=total_struggles,
            avg_tasks_per_day=round(total_tasks / 7, 1),
            busiest_day=busiest_day,
            quietest_day=quietest_day,
            primary_projects=primary_projects if primary_projects else None,
            daily_summaries=daily_summaries if daily_summaries else None
        )

    # =========================================================================
    # Struggle API
    # =========================================================================

    async def get_recent_struggles(
        self,
        days: int = 7,
        resolved: Optional[bool] = None
    ) -> List[Struggle]:
        """Get recent struggles."""
        all_struggles = []
        current = date.today()
        end = current - timedelta(days=days)

        while current >= end:
            struggles = await self.store.get_struggles_by_date(
                current,
                resolved=resolved
            )
            all_struggles.extend(struggles)
            current -= timedelta(days=1)

        return all_struggles

    async def resolve_struggle(
        self,
        struggle_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """Mark a struggle as resolved."""
        return await self.store.resolve_struggle(struggle_id, notes)

    async def get_struggle_patterns(self, days: int = 30) -> Dict[str, Any]:
        """Analyze struggle patterns."""
        return await self.store.get_struggle_patterns(days)

    # =========================================================================
    # Value API
    # =========================================================================

    async def get_values(
        self,
        domain: Optional[str] = None,
        value_types: Optional[List[str]] = None
    ) -> List[UserValue]:
        """Get active user values."""
        return await self.store.get_active_values(
            domain=domain,
            value_types=value_types
        )

    async def reinforce_value(
        self,
        value_id: str,
        quote: Optional[str] = None
    ) -> bool:
        """Reinforce a detected value."""
        return await self.store.reinforce_value(value_id, quote)

    # =========================================================================
    # Relationship API
    # =========================================================================

    async def get_relationship(self, entity_name: str) -> Optional[Relationship]:
        """Get information about a relationship/entity."""
        return await self.store.get_relationship(entity_name)

    async def get_important_relationships(
        self,
        domain: Optional[str] = None
    ) -> List[Relationship]:
        """Get important relationships."""
        return await self.store.get_important_relationships(domain=domain)

    # =========================================================================
    # Statistics API
    # =========================================================================

    async def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get activity statistics."""
        return await self.store.get_activity_stats(days)
