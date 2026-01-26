"""
Memory Capture Pipeline for Thanos Memory System.

Processes events and captures them into the memory system with
appropriate context, embeddings, and pattern detection.
"""

import uuid
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

from .models import Activity, Struggle, UserValue
from .struggle_detector import StruggleDetector, StruggleDetectionResult
from .value_detector import ValueDetector, ValueDetectionResult, EntityMention

logger = logging.getLogger(__name__)


@dataclass
class CaptureResult:
    """Result of memory capture operation."""
    activity_id: str
    embedding_id: Optional[str] = None
    struggle_detected: bool = False
    struggle_id: Optional[str] = None
    value_detected: bool = False
    value_id: Optional[str] = None
    entities_detected: Optional[List[str]] = None


@dataclass
class CaptureContext:
    """Context extracted from an event."""
    project: Optional[str] = None
    domain: Optional[str] = None
    sentiment: Optional[str] = None
    entities: Optional[List[EntityMention]] = None
    energy_level: Optional[str] = None
    session_id: Optional[str] = None


class MemoryCapturePipeline:
    """
    Processes events through the memory capture pipeline.

    Pipeline stages:
    1. Classify event type
    2. Extract context (project, domain, entities)
    3. Detect struggles
    4. Detect values
    5. Generate embeddings
    6. Store in SQLite and ChromaDB
    7. Update relationships
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        chroma_path: Optional[str] = None,
        enable_ai: bool = True
    ):
        """
        Initialize the capture pipeline.

        Args:
            db_path: Path to SQLite database.
            chroma_path: Path to ChromaDB storage.
            enable_ai: Whether to use AI for detection.
        """
        self.db_path = db_path
        self.chroma_path = chroma_path
        self.enable_ai = enable_ai

        # Initialize detectors
        self.struggle_detector = StruggleDetector()
        self.value_detector = ValueDetector()

        # Lazy-loaded stores
        self._sqlite_store = None
        self._chroma_adapter = None

    @property
    def sqlite_store(self):
        """Lazy-load SQLite store."""
        if self._sqlite_store is None:
            from .store import MemoryStore
            self._sqlite_store = MemoryStore(self.db_path)
        return self._sqlite_store

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

    async def capture(
        self,
        event_type: str,
        title: str,
        content: Optional[str] = None,
        source: str = "system",
        source_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> CaptureResult:
        """
        Main capture entry point.

        Args:
            event_type: Type of event (brain_dump, command, task_complete, etc.)
            title: Short title for the activity.
            content: Full content (for brain dumps, conversations).
            source: Source of the event (telegram, cli, system).
            source_context: Additional source-specific context.
            metadata: Additional metadata.
            **kwargs: Additional fields (project, domain, etc.)

        Returns:
            CaptureResult with IDs and detection results.
        """
        activity_id = str(uuid.uuid4())[:12]
        text_to_analyze = content or title

        # Step 1: Extract context
        context = await self._extract_context(text_to_analyze, kwargs)

        # Step 2: Detect struggles
        struggle_result = None
        struggle_id = None
        if text_to_analyze and self._should_detect_struggles(event_type):
            struggle_result = self.struggle_detector.detect(
                text_to_analyze,
                context={"event_type": event_type, **kwargs},
                use_ai=self.enable_ai
            )
            if struggle_result and struggle_result.struggle_detected:
                struggle_id = await self._store_struggle(
                    struggle_result,
                    text_to_analyze,
                    context,
                    activity_id
                )

        # Step 3: Detect values
        value_result = None
        value_id = None
        if text_to_analyze and self._should_detect_values(event_type):
            value_result = self.value_detector.detect(
                text_to_analyze,
                context={"event_type": event_type, **kwargs},
                use_ai=self.enable_ai
            )
            if value_result and value_result.value_detected:
                value_id = await self._store_value(value_result)

        # Step 4: Generate embedding
        embedding_id = None
        if self.chroma_adapter and text_to_analyze:
            embedding_id = await self._store_embedding(
                text_to_analyze,
                event_type,
                context,
                activity_id
            )

        # Step 5: Store activity in SQLite
        activity = Activity(
            id=activity_id,
            timestamp=datetime.now(),
            activity_type=event_type,
            title=title,
            description=kwargs.get('description'),
            content=content,
            project=context.project or kwargs.get('project'),
            domain=context.domain or kwargs.get('domain'),
            energy_level=context.energy_level or kwargs.get('energy_level'),
            duration_minutes=kwargs.get('duration_minutes'),
            started_at=kwargs.get('started_at'),
            ended_at=kwargs.get('ended_at'),
            source=source,
            source_context=source_context,
            related_task_id=kwargs.get('task_id'),
            related_event_id=kwargs.get('event_id'),
            related_commitment_id=kwargs.get('commitment_id'),
            session_id=context.session_id or kwargs.get('session_id'),
            sentiment=context.sentiment,
            struggle_detected=struggle_result.struggle_detected if struggle_result else False,
            struggle_type=struggle_result.struggle_type if struggle_result else None,
            search_text=self._generate_search_text(title, content, context),
            embedding_id=embedding_id,
            metadata=metadata
        )

        await self.sqlite_store.store_activity(activity)

        # Step 6: Update relationships if entities detected
        if context.entities:
            await self._update_relationships(context.entities, activity)

        return CaptureResult(
            activity_id=activity_id,
            embedding_id=embedding_id,
            struggle_detected=struggle_result.struggle_detected if struggle_result else False,
            struggle_id=struggle_id,
            value_detected=value_result is not None,
            value_id=value_id,
            entities_detected=[e.name for e in context.entities] if context.entities else None
        )

    async def _extract_context(
        self,
        text: str,
        kwargs: Dict[str, Any]
    ) -> CaptureContext:
        """Extract context from the text and provided kwargs."""
        context = CaptureContext()

        # Try to get project from kwargs first
        context.project = kwargs.get('project')

        # Extract entities
        if text:
            entities = self.value_detector.detect_entities(text)
            if entities:
                context.entities = entities

        # Infer domain
        context.domain = kwargs.get('domain')
        if not context.domain and text:
            context.domain = self._infer_domain(text)

        # Get session
        context.session_id = kwargs.get('session_id')

        # Get energy level from Oura if available
        context.energy_level = kwargs.get('energy_level')

        return context

    def _infer_domain(self, text: str) -> Optional[str]:
        """Infer domain from text content."""
        import re

        work_patterns = [
            r'\b(client|customer|project|deadline|meeting|report)\b',
            r'\b(pr|code|api|bug|feature)\b',
            r'\b(team|colleague|boss)\b',
        ]

        personal_patterns = [
            r'\b(family|home|personal)\b',
            r'\b(weekend|vacation|holiday)\b',
            r'\b(health|exercise|gym|doctor)\b',
        ]

        text_lower = text.lower()

        work_score = sum(1 for p in work_patterns if re.search(p, text_lower))
        personal_score = sum(1 for p in personal_patterns if re.search(p, text_lower))

        if work_score > personal_score:
            return 'work'
        elif personal_score > work_score:
            return 'personal'
        return None

    def _should_detect_struggles(self, event_type: str) -> bool:
        """Determine if struggle detection should run for this event type."""
        # Run struggle detection on conversational/input events
        return event_type in (
            'brain_dump', 'conversation', 'command', 'task_work'
        )

    def _should_detect_values(self, event_type: str) -> bool:
        """Determine if value detection should run for this event type."""
        # Run value detection on conversational events
        return event_type in (
            'brain_dump', 'conversation', 'commitment_made'
        )

    async def _store_struggle(
        self,
        result: StruggleDetectionResult,
        text: str,
        context: CaptureContext,
        activity_id: str
    ) -> str:
        """Store detected struggle in the database."""
        struggle = Struggle(
            id=str(uuid.uuid4())[:12],
            detected_at=datetime.now(),
            struggle_type=result.struggle_type,
            title=f"{result.struggle_type.title()} detected",
            description=result.reasoning,
            trigger_text=text[:500],
            project=context.project,
            domain=context.domain,
            confidence=result.confidence,
            source_activity_id=activity_id,
            metadata={
                'severity': result.severity,
                'suggested_response': result.suggested_response
            }
        )

        await self.sqlite_store.store_struggle(struggle)
        return struggle.id

    async def _store_value(self, result: ValueDetectionResult) -> str:
        """Store detected value in the database."""
        value = UserValue(
            id=str(uuid.uuid4())[:12],
            detected_at=datetime.now(),
            value_type=result.value_type,
            title=result.title or "Unnamed value",
            description=result.description,
            emotional_weight=result.emotional_weight,
            explicit_importance=result.explicit,
            domain=result.domain,
            related_entity=result.related_entity,
            source_quotes=[result.evidence_quote] if result.evidence_quote else None
        )

        await self.sqlite_store.store_value(value)
        return value.id

    async def _store_embedding(
        self,
        text: str,
        event_type: str,
        context: CaptureContext,
        activity_id: str
    ) -> Optional[str]:
        """Store embedding in ChromaDB."""
        if not self.chroma_adapter:
            return None

        try:
            result = await self.chroma_adapter.call_tool(
                "store_memory",
                {
                    "content": text,
                    "collection": "activities",
                    "metadata": {
                        "activity_id": activity_id,
                        "activity_type": event_type,
                        "project": context.project,
                        "domain": context.domain,
                        "date": datetime.now().date().isoformat()
                    }
                }
            )
            if result.success:
                return result.data.get('id')
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")

        return None

    def _generate_search_text(
        self,
        title: str,
        content: Optional[str],
        context: CaptureContext
    ) -> str:
        """Generate searchable text for FTS."""
        parts = [title]
        if content:
            parts.append(content)
        if context.project:
            parts.append(context.project)
        if context.entities:
            parts.extend([e.name for e in context.entities])
        return " ".join(parts)

    async def _update_relationships(
        self,
        entities: List[EntityMention],
        activity: Activity
    ) -> None:
        """Update relationship tracking for detected entities."""
        for entity in entities:
            await self.sqlite_store.update_relationship(
                entity_name=entity.name,
                entity_type=entity.entity_type,
                domain=activity.domain,
                sentiment=entity.sentiment,
                commitment_text=entity.commitment_text if entity.commitment_detected else None
            )


# Convenience functions for common capture patterns

async def capture_brain_dump(
    content: str,
    source: str = "telegram",
    classification: Optional[str] = None,
    **kwargs
) -> CaptureResult:
    """Capture a brain dump."""
    pipeline = MemoryCapturePipeline()
    return await pipeline.capture(
        event_type="brain_dump",
        title=content[:100] + ("..." if len(content) > 100 else ""),
        content=content,
        source=source,
        metadata={"classification": classification} if classification else None,
        **kwargs
    )


async def capture_task_completion(
    task_id: str,
    title: str,
    duration_minutes: Optional[int] = None,
    project: Optional[str] = None,
    **kwargs
) -> CaptureResult:
    """Capture a task completion."""
    pipeline = MemoryCapturePipeline()
    return await pipeline.capture(
        event_type="task_complete",
        title=f"Completed: {title}",
        task_id=task_id,
        duration_minutes=duration_minutes,
        project=project,
        **kwargs
    )


async def capture_conversation(
    content: str,
    session_id: str,
    source: str = "telegram",
    **kwargs
) -> CaptureResult:
    """Capture a conversation message."""
    pipeline = MemoryCapturePipeline()
    return await pipeline.capture(
        event_type="conversation",
        title=content[:100] + ("..." if len(content) > 100 else ""),
        content=content,
        source=source,
        session_id=session_id,
        **kwargs
    )


async def capture_command(
    command: str,
    result: Optional[str] = None,
    duration_ms: Optional[float] = None,
    source: str = "cli",
    **kwargs
) -> CaptureResult:
    """Capture a command execution."""
    pipeline = MemoryCapturePipeline()
    return await pipeline.capture(
        event_type="command",
        title=f"Command: {command}",
        content=result,
        source=source,
        metadata={
            "command": command,
            "duration_ms": duration_ms
        },
        **kwargs
    )
