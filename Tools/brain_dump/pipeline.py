#!/usr/bin/env python3
"""
Unified Brain Dump Pipeline for Thanos.

This is the single entry point for all brain dump processing.
Uses RULE-BASED classification only - no API calls needed.

Routes content to appropriate storage based on classification:
- work_task -> WorkOS (only work tasks)
- personal_task -> Local SQLite with impact scoring
- thought/idea/observation -> ChromaDB for pattern mining
- worry -> Journal + SQLite worries table
- commitment -> Local SQLite
- habit -> Local SQLite (NOT WorkOS)
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# Configure logging
logger = logging.getLogger('brain_dump_pipeline')

# Handle both module and direct imports for processor
try:
    from Tools.accountability.processor import BrainDumpProcessor
    from Tools.accountability.models import (
        ImpactScore,
        BrainDumpCategory,
        TaskDomain,
        ClassifiedBrainDump,
    )
except ImportError:
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from accountability.processor import BrainDumpProcessor
        from accountability.models import (
            ImpactScore,
            BrainDumpCategory,
            TaskDomain,
            ClassifiedBrainDump,
        )
    except ImportError:
        BrainDumpProcessor = None
        ImpactScore = None
        BrainDumpCategory = None
        TaskDomain = None
        ClassifiedBrainDump = None


# Map BrainDumpCategory to routing classification names
CATEGORY_TO_CLASSIFICATION = {
    BrainDumpCategory.THOUGHT: 'thinking',
    BrainDumpCategory.PROJECT: 'work_task',  # Projects route as work tasks
    BrainDumpCategory.TASK: None,  # Determined by domain
    BrainDumpCategory.WORRY: 'worry',
    BrainDumpCategory.OBSERVATION: 'observation',
    BrainDumpCategory.IDEA: 'idea',
}


@dataclass
class ProcessingResult:
    """Result of processing a brain dump through the pipeline."""

    # Input tracking
    id: str
    raw_content: str
    source: str

    # Classification
    classification: str
    classification_confidence: float
    reasoning: str

    # Domain and impact (for personal items)
    domain: Optional[str] = None  # 'work' or 'personal'
    domain_confidence: Optional[float] = None
    impact_score: Optional[Dict[str, float]] = None

    # Where data was stored
    destinations: List[str] = field(default_factory=list)

    # IDs of created items
    created_task_id: Optional[str] = None
    created_commitment_id: Optional[str] = None
    created_worry_id: Optional[str] = None
    chroma_memory_id: Optional[str] = None
    journal_entry_id: Optional[int] = None
    workos_task_id: Optional[int] = None

    # Review status
    needs_review: bool = False
    review_reason: Optional[str] = None

    # User-facing response
    acknowledgment: str = ""
    similar_thoughts: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    processing_time_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'raw_content': self.raw_content,
            'source': self.source,
            'classification': self.classification,
            'classification_confidence': self.classification_confidence,
            'reasoning': self.reasoning,
            'domain': self.domain,
            'domain_confidence': self.domain_confidence,
            'impact_score': self.impact_score,
            'destinations': self.destinations,
            'created_task_id': self.created_task_id,
            'created_commitment_id': self.created_commitment_id,
            'created_worry_id': self.created_worry_id,
            'chroma_memory_id': self.chroma_memory_id,
            'journal_entry_id': self.journal_entry_id,
            'workos_task_id': self.workos_task_id,
            'needs_review': self.needs_review,
            'review_reason': self.review_reason,
            'acknowledgment': self.acknowledgment,
            'similar_thoughts': self.similar_thoughts,
            'processed_at': self.processed_at,
            'processing_time_ms': self.processing_time_ms,
        }


class BrainDumpPipeline:
    """
    Unified pipeline for processing brain dumps.

    Uses RULE-BASED classification only (BrainDumpProcessor).
    No API calls - all classification happens locally via keyword matching.

    Storage mapping:
    - work_task -> WorkOS
    - personal_task -> SQLite (with impact scores)
    - thought/idea/observation -> ChromaDB
    - worry -> Journal + SQLite worries table
    - commitment -> SQLite
    - habit -> SQLite (local, not WorkOS)
    """

    # Confidence threshold for auto-routing
    CONFIDENCE_THRESHOLD = 0.6

    def __init__(
        self,
        state_store=None,
        journal=None,
        chroma_adapter=None,
        workos_bridge=None,
    ):
        """
        Initialize the pipeline.

        Args:
            state_store: SQLite state store for local data
            journal: Journal for logging all events
            chroma_adapter: ChromaDB adapter for vector storage
            workos_bridge: WorkOS MCP bridge (only for work_task sync)
        """
        self.processor = BrainDumpProcessor() if BrainDumpProcessor else None
        self.state_store = state_store
        self.journal = journal
        self.chroma_adapter = chroma_adapter
        self.workos_bridge = workos_bridge

    async def process(
        self,
        content: str,
        source: str = "direct",
        force_domain: Optional[str] = None,
    ) -> ProcessingResult:
        """
        Process a brain dump through the full pipeline.

        All classification is rule-based - no API calls.

        Args:
            content: Raw brain dump content
            source: Source of the dump (telegram, voice, direct, etc.)
            force_domain: Override domain detection ('work' or 'personal')

        Returns:
            ProcessingResult with all metadata and destinations
        """
        start_time = datetime.now()
        dump_id = str(uuid.uuid4())[:8]

        if not self.processor:
            return ProcessingResult(
                id=dump_id,
                raw_content=content,
                source=source,
                classification="unknown",
                classification_confidence=0.0,
                reasoning="Processor not available",
                needs_review=True,
                review_reason="Pipeline not properly initialized",
                acknowledgment="Unable to process. System error.",
            )

        # Step 1: Classify using RULE-BASED processor (no API)
        classified = self.processor.process(content, source, {'id': dump_id})

        # Step 2: Map category to classification string
        classification = self._map_classification(classified, force_domain)

        # Get domain
        domain = None
        domain_confidence = None
        if classified.domain:
            if force_domain:
                domain = force_domain
                domain_confidence = 1.0
            else:
                domain = classified.domain.value
                domain_confidence = classified.confidence

        # Get impact score for personal items
        impact_score = None
        if domain == 'personal' and classified.impact_score:
            impact_score = classified.impact_score.to_dict()

        # Build reasoning string
        reasoning = f"Category: {classified.category.value}"
        if classified.domain:
            reasoning += f", Domain: {classified.domain.value}"
        if classified.review_reason:
            reasoning += f" ({classified.review_reason})"

        # Build initial result
        result = ProcessingResult(
            id=dump_id,
            raw_content=content,
            source=source,
            classification=classification,
            classification_confidence=classified.confidence,
            reasoning=reasoning,
            domain=domain,
            domain_confidence=domain_confidence,
            impact_score=impact_score,
            needs_review=classified.needs_review,
            review_reason=classified.review_reason,
            acknowledgment=self._generate_acknowledgment(classification),
        )

        # Step 3: Route to appropriate storage
        if result.needs_review:
            # Store in review queue, don't auto-route
            await self._store_for_review(result, classified)
            result.destinations.append("review_queue")
        else:
            # Route based on classification
            await self._route(result, classified)

        # Step 4: Log routing decision
        await self._log_routing_decision(result, classified)

        # Calculate processing time
        result.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            f"Processed brain dump {result.id}: "
            f"classification={result.classification}, "
            f"domain={result.domain}, "
            f"destinations={result.destinations}, "
            f"time={result.processing_time_ms:.1f}ms"
        )

        return result

    def _map_classification(
        self,
        classified: ClassifiedBrainDump,
        force_domain: Optional[str] = None
    ) -> str:
        """Map processor's BrainDumpCategory to routing classification."""

        category = classified.category

        # Tasks are special - they become work_task or personal_task
        if category == BrainDumpCategory.TASK:
            if force_domain:
                return f"{force_domain}_task"
            if classified.domain == TaskDomain.WORK:
                return "work_task"
            return "personal_task"

        # Projects route as work tasks
        if category == BrainDumpCategory.PROJECT:
            return "work_task"

        # Direct mapping for other categories
        return CATEGORY_TO_CLASSIFICATION.get(category, 'thinking')

    async def _route(self, result: ProcessingResult, classified: ClassifiedBrainDump) -> None:
        """Route to appropriate storage based on classification."""

        classification = result.classification

        if classification == 'work_task':
            await self._route_work_task(result, classified)

        elif classification == 'personal_task':
            await self._route_personal_task(result, classified)

        elif classification in ('thinking', 'observation'):
            await self._route_reflective(result, classified)

        elif classification == 'idea':
            await self._route_idea(result, classified)

        elif classification == 'worry':
            await self._route_worry(result, classified)

    async def _route_work_task(self, result: ProcessingResult, classified: ClassifiedBrainDump) -> None:
        """Route work task to WorkOS."""

        # Only work tasks go to WorkOS
        if self.workos_bridge:
            try:
                workos_result = await self.workos_bridge.create_task(
                    title=classified.title or result.raw_content[:100],
                    description=result.raw_content,
                    category='work',
                    status='backlog',
                )
                if workos_result and workos_result.get('id'):
                    result.workos_task_id = workos_result['id']
                    result.destinations.append("workos")
            except Exception as e:
                logger.error(f"Failed to create WorkOS task: {e}")

        # Also store locally as backup
        if self.state_store:
            task_id = await self._create_local_task(result, classified, domain='work')
            result.created_task_id = task_id
            result.destinations.append("sqlite")

    async def _route_personal_task(self, result: ProcessingResult, classified: ClassifiedBrainDump) -> None:
        """Route personal task to local SQLite with impact scoring."""

        # Personal tasks go to local SQLite only (NOT WorkOS)
        if self.state_store:
            task_id = await self._create_local_task(result, classified, domain='personal')
            result.created_task_id = task_id
            result.destinations.append("sqlite")

    async def _route_reflective(self, result: ProcessingResult, classified: ClassifiedBrainDump) -> None:
        """Route thinking/observation to ChromaDB for pattern mining."""

        if self.chroma_adapter:
            try:
                memory_id = await self._store_in_chroma(
                    result,
                    collection='personal_memories',
                    classification=result.classification,
                )
                result.chroma_memory_id = memory_id
                result.destinations.append("chromadb")

                # Get similar thoughts
                similar = await self._find_similar_thoughts(result.raw_content)
                result.similar_thoughts = similar[:3]

            except Exception as e:
                logger.error(f"Failed to store in ChromaDB: {e}")

        # Always log to journal
        if self.journal:
            entry_id = self.journal.log(
                event_type=f"brain_dump_{result.classification}",
                source="brain_dump",
                title=result.raw_content[:100],
                data={
                    'dump_id': result.id,
                    'classification': result.classification,
                    'confidence': result.classification_confidence,
                },
                severity="info"
            )
            result.journal_entry_id = entry_id
            result.destinations.append("journal")

    async def _route_idea(self, result: ProcessingResult, classified: ClassifiedBrainDump) -> None:
        """Route idea to ChromaDB with category metadata."""

        if self.chroma_adapter:
            try:
                memory_id = await self._store_in_chroma(
                    result,
                    collection='personal_memories',
                    classification='idea',
                    extra_metadata={
                        'idea_title': classified.title,
                    }
                )
                result.chroma_memory_id = memory_id
                result.destinations.append("chromadb")
            except Exception as e:
                logger.error(f"Failed to store idea in ChromaDB: {e}")

    async def _route_worry(self, result: ProcessingResult, classified: ClassifiedBrainDump) -> None:
        """Route worry to journal first, then SQLite worries table."""

        # First, log to journal for processing
        if self.journal:
            entry_id = self.journal.log(
                event_type="brain_dump_worry",
                source="brain_dump",
                title=f"Worry captured: {result.raw_content[:50]}...",
                data={
                    'dump_id': result.id,
                    'raw_content': result.raw_content,
                    'needs_reframing': True,
                },
                severity="info"
            )
            result.journal_entry_id = entry_id
            result.destinations.append("journal")

        # Store in worries table for tracking
        if self.state_store and hasattr(self.state_store, 'add_worry'):
            worry_id = self.state_store.add_worry(
                raw_content=result.raw_content,
                journal_entry_id=result.journal_entry_id,
                dump_id=result.id,
            )
            result.created_worry_id = worry_id
            result.destinations.append("sqlite_worries")

        # Also store in ChromaDB for pattern detection
        if self.chroma_adapter:
            try:
                memory_id = await self._store_in_chroma(
                    result,
                    collection='personal_memories',
                    classification='worry',
                )
                result.chroma_memory_id = memory_id
                result.destinations.append("chromadb")
            except Exception as e:
                logger.error(f"Failed to store worry in ChromaDB: {e}")

    async def _store_for_review(self, result: ProcessingResult, classified: ClassifiedBrainDump) -> None:
        """Store item in review queue for manual classification."""

        if self.state_store and hasattr(self.state_store, 'add_pending_review'):
            self.state_store.add_pending_review(
                dump_id=result.id,
                raw_content=result.raw_content,
                source=result.source,
                suggested_classification=result.classification,
                confidence=result.classification_confidence,
                review_reason=result.review_reason,
            )

        # Also log to journal
        if self.journal:
            self.journal.log(
                event_type="brain_dump_needs_review",
                source="brain_dump",
                title=f"Review needed: {result.raw_content[:50]}...",
                data={
                    'dump_id': result.id,
                    'suggested_classification': result.classification,
                    'confidence': result.classification_confidence,
                    'review_reason': result.review_reason,
                },
                severity="warning"
            )

    async def _log_routing_decision(self, result: ProcessingResult, classified: ClassifiedBrainDump) -> None:
        """Log routing decision for validation and debugging."""

        if self.journal:
            self.journal.log(
                event_type="brain_dump_routed",
                source="pipeline",
                title=f"Routed: {result.classification} -> {', '.join(result.destinations)}",
                data={
                    'dump_id': result.id,
                    'classification': result.classification,
                    'classification_confidence': result.classification_confidence,
                    'domain': result.domain,
                    'domain_confidence': result.domain_confidence,
                    'destinations': result.destinations,
                    'needs_review': result.needs_review,
                    'review_reason': result.review_reason,
                    'impact_score': result.impact_score,
                },
                severity="info"
            )

    async def _create_local_task(
        self,
        result: ProcessingResult,
        classified: ClassifiedBrainDump,
        domain: str,
    ) -> Optional[str]:
        """Create task in local SQLite with impact scoring."""

        if not self.state_store:
            return None

        # Build metadata
        metadata = {
            'dump_id': result.id,
            'domain': domain,
            'classification': result.classification,
            'classification_confidence': result.classification_confidence,
        }

        # Add impact score if available
        if result.impact_score:
            metadata['impact_health'] = result.impact_score.get('health')
            metadata['impact_stress'] = result.impact_score.get('stress')
            metadata['impact_financial'] = result.impact_score.get('financial')
            metadata['impact_relationship'] = result.impact_score.get('relationship')
            metadata['impact_composite'] = result.impact_score.get('composite')

        task_id = self.state_store.add_task(
            title=classified.title or result.raw_content[:100],
            description=result.raw_content,
            priority=classified.energy_hint,
            source="brain_dump",
            metadata=metadata,
        )

        return task_id

    async def _store_in_chroma(
        self,
        result: ProcessingResult,
        collection: str,
        classification: str,
        extra_metadata: Optional[Dict] = None,
    ) -> Optional[str]:
        """Store content in ChromaDB for semantic search."""

        if not self.chroma_adapter:
            return None

        metadata = {
            'source': 'brain_dump',
            'classification': classification,
            'timestamp': result.processed_at,
            'dump_id': result.id,
            'brain_dump_source': result.source,
        }

        if extra_metadata:
            metadata.update(extra_metadata)

        # Add impact dimensions if available
        if result.impact_score:
            metadata['impact_domains'] = [
                k for k, v in result.impact_score.items()
                if k != 'composite' and v and v > 5
            ]

        memory_id = self.chroma_adapter.add_memory(
            collection=collection,
            content=result.raw_content,
            metadata=metadata,
        )

        return memory_id

    async def _find_similar_thoughts(self, content: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Find similar past thoughts in ChromaDB."""

        if not self.chroma_adapter:
            return []

        try:
            results = self.chroma_adapter.search(
                collection='personal_memories',
                query=content,
                limit=limit,
                where={'classification': {'$in': ['thinking', 'observation', 'idea']}},
            )
            return results
        except Exception as e:
            logger.error(f"Failed to find similar thoughts: {e}")
            return []

    def _generate_acknowledgment(self, classification: str) -> str:
        """Generate acknowledgment message for classification."""

        acknowledgments = {
            'thinking': "Thought noted. Take your time.",
            'observation': "Observation recorded.",
            'idea': "Idea captured for later exploration.",
            'personal_task': "Personal task created.",
            'work_task': "Work task created and synced.",
            'worry': "Worry captured. We'll process this together.",
        }

        return acknowledgments.get(classification, "Brain dump received.")


# Convenience function for direct use
async def process_brain_dump(
    content: str,
    source: str = "direct",
    state_store=None,
    journal=None,
    chroma_adapter=None,
    workos_bridge=None,
) -> ProcessingResult:
    """
    Process a brain dump through the full pipeline.

    All classification is RULE-BASED - no API calls.

    Args:
        content: Raw brain dump content
        source: Source of the dump
        state_store: SQLite state store
        journal: Journal for logging
        chroma_adapter: ChromaDB adapter
        workos_bridge: WorkOS bridge (for work tasks only)

    Returns:
        ProcessingResult with all metadata
    """
    pipeline = BrainDumpPipeline(
        state_store=state_store,
        journal=journal,
        chroma_adapter=chroma_adapter,
        workos_bridge=workos_bridge,
    )
    return await pipeline.process(content, source)


# Sync wrapper
def process_brain_dump_sync(
    content: str,
    source: str = "direct",
    **kwargs,
) -> ProcessingResult:
    """Synchronous wrapper for process_brain_dump."""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    process_brain_dump(content, source, **kwargs)
                )
                return future.result()
        else:
            return loop.run_until_complete(process_brain_dump(content, source, **kwargs))
    except RuntimeError:
        return asyncio.run(process_brain_dump(content, source, **kwargs))


# CLI for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pipeline.py 'your brain dump text'")
        print("\nExamples:")
        print("  python pipeline.py 'Call dentist tomorrow'")
        print("  python pipeline.py 'Fix bug in login page for client Memphis'")
        print("  python pipeline.py 'I wonder if we should use GraphQL'")
        sys.exit(1)

    text = ' '.join(sys.argv[1:])
    print(f"\nProcessing: {text}\n")

    result = process_brain_dump_sync(text)

    print(f"Classification: {result.classification}")
    print(f"Confidence: {result.classification_confidence:.2f}")
    print(f"Domain: {result.domain}")
    print(f"Destinations: {result.destinations}")
    print(f"Needs Review: {result.needs_review}")
    if result.review_reason:
        print(f"Review Reason: {result.review_reason}")
    print(f"Acknowledgment: {result.acknowledgment}")

    if result.impact_score:
        print(f"\nImpact Score:")
        for k, v in result.impact_score.items():
            if v and isinstance(v, (int, float)):
                print(f"  {k}: {v:.1f}")
            elif v:
                print(f"  {k}: {v}")

    print(f"\nProcessing time: {result.processing_time_ms:.1f}ms")
