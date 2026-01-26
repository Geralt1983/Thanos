"""
Brain Dump Ingester for Thanos Personal Memory System.

This is the UNIFIED entry point for all brain dumps - personal AND work.
Every brain dump flows through here for:
1. Entity extraction (people, places, things)
2. Task extraction (implicit todos)
3. Deadline detection (dates, urgency)
4. Blocker detection (dependencies, obstacles)
5. Energy state detection
6. Full vectorization via ChromaDB
7. Pattern linking across memory systems

WorkOS gets a COPY of work-related items; personal memories stay in the
unified personal memory system.
"""

import re
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """An entity extracted from text."""
    name: str
    entity_type: str  # person, place, organization, thing
    context: Optional[str] = None
    relationship: Optional[str] = None  # spouse, child, client, colleague


@dataclass
class ExtractedTask:
    """An implicit task extracted from brain dump."""
    title: str
    urgency: str = "normal"  # low, normal, high, critical
    deadline: Optional[datetime] = None
    deadline_text: Optional[str] = None
    blockers: List[str] = field(default_factory=list)
    is_work: bool = False
    client: Optional[str] = None


@dataclass
class ExtractedDeadline:
    """A deadline extracted from text."""
    text: str
    parsed_date: Optional[datetime] = None
    urgency: str = "normal"
    related_task: Optional[str] = None


@dataclass
class EnergySignal:
    """Energy state signals from text."""
    level: str  # low, medium, high
    indicators: List[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class BrainDumpExtraction:
    """Full extraction result from a brain dump."""
    raw_content: str
    timestamp: datetime

    # Extracted components
    entities: List[ExtractedEntity] = field(default_factory=list)
    tasks: List[ExtractedTask] = field(default_factory=list)
    deadlines: List[ExtractedDeadline] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    energy: Optional[EnergySignal] = None

    # Classification
    is_work_related: bool = False
    is_personal: bool = True
    domains: List[str] = field(default_factory=list)  # family, health, work, finance, etc.

    # Detected patterns
    values_detected: List[str] = field(default_factory=list)
    struggles_detected: List[str] = field(default_factory=list)

    # Storage IDs
    memory_id: Optional[str] = None
    vector_id: Optional[str] = None
    workos_id: Optional[str] = None


class BrainDumpIngester:
    """
    Unified brain dump ingestion pipeline.

    Every brain dump - voice, text, telegram, CLI - flows through here
    for full extraction, vectorization, and intelligent storage.
    """

    # Entity patterns
    PERSON_PATTERNS = [
        r'\b(?:my\s+)?(wife|husband|spouse|partner)\b',
        r'\b(?:my\s+)?(son|daughter|kid|child|children)\b',
        r'\b(?:my\s+)?(mom|dad|mother|father|parent)\b',
        r'\b(?:their|his|her)\s+mom\b',
        r'\b(?:the\s+)?(client|customer)\b',
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',  # Capitalized names
    ]

    # Task indicators
    TASK_INDICATORS = [
        r'\b(?:i\s+)?(?:need|gotta|have|got)\s+to\s+(.+?)(?:\.|,|$)',
        r'\b(?:i\s+)?(?:gotta|have\s+to|need\s+to)\s+get\s+(.+?)(?:done|finished|completed)?(?:\.|,|$)',
        r'\b(?:i\s+)?(?:should|must|ought\s+to)\s+(.+?)(?:\.|,|$)',
        r'\bremind(?:er)?\s+(?:me\s+)?(?:to\s+)?(.+?)(?:\.|,|$)',
        r'\bdon\'t\s+forget\s+(?:to\s+)?(.+?)(?:\.|,|$)',
        r'\b(?:todo|to-do|to\s+do):\s*(.+?)(?:\.|,|$)',
        r'\b(?:i\s+)?forgot\s+to\s+(?:get\s+)?(.+?)(?:\.|,|$)',
        r'\bgoing\s+to\s+have\s+to\s+(.+?)(?:\.|,|$)',
        r'\b(?:supposed\s+to|meant\s+to)\s+(.+?)(?:\.|,|$)',
    ]

    # Deadline patterns
    DEADLINE_PATTERNS = [
        (r'\b(?:by|before|due|until)\s+(tomorrow)\b', 1),
        (r'\b(?:by|before|due|until)\s+(next\s+(?:week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b', 7),
        (r'\b(?:in|within)\s+(\d+)\s+(day|week|month)s?\b', None),
        (r'\b(a\s+month\s+from\s+now)\b', 30),
        (r'\b(end\s+of\s+(?:the\s+)?(?:week|month|year))\b', None),
        (r'\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b', None),
    ]

    # Blocker patterns
    BLOCKER_PATTERNS = [
        r'\bbut\s+(?:i\s+)?(?:forgot|missing|don\'t\s+have|need)\s+(.+?)(?:\.|,|$)',
        r'\b(?:waiting\s+(?:for|on)|blocked\s+by|need\s+to\s+get)\s+(.+?)(?:\.|,|$)',
        r'\bcan\'t\s+(?:do|start|finish)\s+(?:it\s+)?(?:until|without)\s+(.+?)(?:\.|,|$)',
    ]

    # Energy indicators
    ENERGY_LOW = ['tired', 'exhausted', 'no sleep', 'not much sleep', 'drained',
                  'wiped', 'burnt out', 'low energy', 'sleepy', 'fatigued']
    ENERGY_HIGH = ['energized', 'pumped', 'ready', 'refreshed', 'well rested',
                   'good sleep', 'productive', 'focused', 'motivated']

    # Domain keywords
    DOMAIN_KEYWORDS = {
        'family': ['wife', 'husband', 'kid', 'child', 'daughter', 'son', 'mom', 'dad', 'parent'],
        'health': ['sleep', 'tired', 'sick', 'doctor', 'exercise', 'workout', 'energy'],
        'work': ['client', 'meeting', 'project', 'deadline', 'task', 'work', 'job'],
        'finance': ['money', 'pay', 'bill', 'budget', 'expense', 'cost', 'price'],
        'admin': ['passport', 'license', 'document', 'form', 'paperwork', 'certificate'],
    }

    # Client names (loaded from WorkOS or config)
    KNOWN_CLIENTS = ['orlando', 'raleigh', 'memphis']

    def __init__(self, memory_service=None, workos_enabled: bool = True):
        """
        Initialize the ingester.

        Args:
            memory_service: Optional existing MemoryService to use
            workos_enabled: Whether to also store work items in WorkOS
        """
        self.memory_service = memory_service
        self.workos_enabled = workos_enabled
        self._chroma_adapter = None

    @property
    def chroma_adapter(self):
        """Lazy-load ChromaDB adapter."""
        if self._chroma_adapter is None:
            try:
                from Tools.adapters.chroma_adapter import ChromaAdapter
                chroma_path = Path.home() / "Projects" / "Thanos" / "State" / "personal_memory"
                self._chroma_adapter = ChromaAdapter(persist_directory=str(chroma_path))
            except ImportError:
                logger.warning("ChromaDB adapter not available")
        return self._chroma_adapter

    async def ingest(self, content: str, source: str = "unknown") -> BrainDumpExtraction:
        """
        Full ingestion pipeline for a brain dump.

        Args:
            content: Raw brain dump text
            source: Where this came from (telegram, cli, voice, etc.)

        Returns:
            BrainDumpExtraction with all extracted information
        """
        extraction = BrainDumpExtraction(
            raw_content=content,
            timestamp=datetime.now()
        )

        content_lower = content.lower()

        # Step 1: Extract entities
        extraction.entities = self._extract_entities(content)

        # Step 2: Extract tasks
        extraction.tasks = self._extract_tasks(content)

        # Step 3: Extract deadlines
        extraction.deadlines = self._extract_deadlines(content)

        # Step 4: Extract blockers
        extraction.blockers = self._extract_blockers(content)

        # Step 5: Detect energy state
        extraction.energy = self._detect_energy(content_lower)

        # Step 6: Classify domains
        extraction.domains = self._classify_domains(content_lower)
        extraction.is_work_related = 'work' in extraction.domains or any(
            task.is_work for task in extraction.tasks
        )
        extraction.is_personal = bool(set(extraction.domains) - {'work'})

        # Step 7: Detect values and struggles (use existing detectors)
        extraction.values_detected = self._detect_values(content)
        extraction.struggles_detected = self._detect_struggles(content)

        # Step 8: Store in personal memory with vectorization
        extraction.memory_id, extraction.vector_id = await self._store_in_memory(
            extraction, source
        )

        # Step 9: If work-related, also store in WorkOS
        if extraction.is_work_related and self.workos_enabled:
            extraction.workos_id = await self._store_in_workos(extraction)

        # Step 10: Create any extracted tasks
        await self._create_extracted_tasks(extraction)

        logger.info(
            f"Brain dump ingested: {len(extraction.entities)} entities, "
            f"{len(extraction.tasks)} tasks, {len(extraction.deadlines)} deadlines, "
            f"domains={extraction.domains}, memory_id={extraction.memory_id}"
        )

        return extraction

    def _extract_entities(self, content: str) -> List[ExtractedEntity]:
        """Extract people, places, and things from text."""
        entities = []
        content_lower = content.lower()

        # Relationship-based entities
        relationship_map = {
            'wife': ('spouse', 'person'),
            'husband': ('spouse', 'person'),
            'partner': ('partner', 'person'),
            'son': ('child', 'person'),
            'daughter': ('child', 'person'),
            'kid': ('child', 'person'),
            'child': ('child', 'person'),
            'children': ('child', 'person'),
            'mom': ('parent', 'person'),
            'dad': ('parent', 'person'),
            'mother': ('parent', 'person'),
            'father': ('parent', 'person'),
            'their mom': ('co-parent', 'person'),
            'his mom': ('co-parent', 'person'),
            'her mom': ('co-parent', 'person'),
        }

        for term, (relationship, entity_type) in relationship_map.items():
            if term in content_lower:
                entities.append(ExtractedEntity(
                    name=term,
                    entity_type=entity_type,
                    relationship=relationship
                ))

        # Client detection
        for client in self.KNOWN_CLIENTS:
            if client in content_lower:
                entities.append(ExtractedEntity(
                    name=client.title(),
                    entity_type='organization',
                    relationship='client'
                ))

        return entities

    def _extract_tasks(self, content: str) -> List[ExtractedTask]:
        """Extract implicit tasks from brain dump."""
        tasks = []
        content_lower = content.lower()

        for pattern in self.TASK_INDICATORS:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                task_text = match.strip() if isinstance(match, str) else match[0].strip()
                if len(task_text) > 3:  # Filter out tiny matches
                    # Check if work-related
                    is_work = any(client in task_text for client in self.KNOWN_CLIENTS)
                    is_work = is_work or any(kw in task_text for kw in ['client', 'meeting', 'deploy', 'ship'])

                    # Detect urgency
                    urgency = 'normal'
                    if any(u in task_text for u in ['asap', 'urgent', 'immediately', 'right now']):
                        urgency = 'critical'
                    elif any(u in task_text for u in ['soon', 'expedite']):
                        urgency = 'high'

                    tasks.append(ExtractedTask(
                        title=task_text.capitalize(),
                        urgency=urgency,
                        is_work=is_work
                    ))

        return tasks

    def _extract_deadlines(self, content: str) -> List[ExtractedDeadline]:
        """Extract deadlines and time references."""
        deadlines = []
        content_lower = content.lower()
        now = datetime.now()

        for pattern, default_days in self.DEADLINE_PATTERNS:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                deadline_text = match if isinstance(match, str) else ' '.join(match)
                parsed_date = None

                # Try to parse the date
                if 'tomorrow' in deadline_text:
                    parsed_date = now + timedelta(days=1)
                elif 'next week' in deadline_text:
                    parsed_date = now + timedelta(weeks=1)
                elif 'next month' in deadline_text:
                    parsed_date = now + timedelta(days=30)
                elif 'month from now' in deadline_text:
                    parsed_date = now + timedelta(days=30)
                elif default_days:
                    parsed_date = now + timedelta(days=default_days)

                # Determine urgency
                urgency = 'normal'
                if parsed_date:
                    days_until = (parsed_date - now).days
                    if days_until <= 1:
                        urgency = 'critical'
                    elif days_until <= 7:
                        urgency = 'high'
                    elif days_until <= 14:
                        urgency = 'normal'
                    else:
                        urgency = 'low'

                deadlines.append(ExtractedDeadline(
                    text=deadline_text,
                    parsed_date=parsed_date,
                    urgency=urgency
                ))

        return deadlines

    def _extract_blockers(self, content: str) -> List[str]:
        """Extract blockers and dependencies."""
        blockers = []
        content_lower = content.lower()

        for pattern in self.BLOCKER_PATTERNS:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                blocker_text = match.strip() if isinstance(match, str) else match[0].strip()
                if len(blocker_text) > 3:
                    blockers.append(blocker_text)

        return blockers

    def _detect_energy(self, content_lower: str) -> EnergySignal:
        """Detect energy level from text."""
        low_indicators = [ind for ind in self.ENERGY_LOW if ind in content_lower]
        high_indicators = [ind for ind in self.ENERGY_HIGH if ind in content_lower]

        if low_indicators:
            return EnergySignal(
                level='low',
                indicators=low_indicators,
                confidence=min(0.9, 0.5 + len(low_indicators) * 0.15)
            )
        elif high_indicators:
            return EnergySignal(
                level='high',
                indicators=high_indicators,
                confidence=min(0.9, 0.5 + len(high_indicators) * 0.15)
            )
        else:
            return EnergySignal(level='medium', confidence=0.3)

    def _classify_domains(self, content_lower: str) -> List[str]:
        """Classify brain dump into life domains."""
        domains = []

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                domains.append(domain)

        return domains if domains else ['general']

    def _detect_values(self, content: str) -> List[str]:
        """Detect expressed values in the brain dump."""
        values = []
        content_lower = content.lower()

        value_indicators = {
            'family_time': ['time spent', 'time together', 'quality time', 'with the family'],
            'work_life_balance': ['no meetings', 'nice day', 'relaxed', 'not much work'],
            'responsibility': ['gotta get', 'need to', 'supposed to', 'have to'],
            'connection': ['talked to', 'talking to', 'spent time', 'good conversation'],
        }

        for value, indicators in value_indicators.items():
            if any(ind in content_lower for ind in indicators):
                values.append(value)

        return values

    def _detect_struggles(self, content: str) -> List[str]:
        """Detect struggles or challenges in the brain dump."""
        struggles = []
        content_lower = content.lower()

        struggle_indicators = {
            'fatigue': ['tired', 'exhausted', 'no sleep', 'sleepy'],
            'forgetfulness': ['forgot', 'forgot to', 'didn\'t remember'],
            'overwhelm': ['too much', 'overwhelmed', 'so much to do'],
            'time_pressure': ['running out of time', 'deadline', 'expedite'],
        }

        for struggle, indicators in struggle_indicators.items():
            if any(ind in content_lower for ind in indicators):
                struggles.append(struggle)

        return struggles

    async def _store_in_memory(
        self,
        extraction: BrainDumpExtraction,
        source: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Store in personal memory system with vectorization."""
        import uuid

        memory_id = str(uuid.uuid4())[:12]
        vector_id = None

        # Store in ChromaDB for vector search
        if self.chroma_adapter:
            try:
                # Build metadata for filtering
                metadata = {
                    'source': source,
                    'timestamp': extraction.timestamp.isoformat(),
                    'domains': ','.join(extraction.domains),
                    'is_work': str(extraction.is_work_related),  # ChromaDB needs strings
                    'is_personal': str(extraction.is_personal),
                    'energy_level': extraction.energy.level if extraction.energy else 'unknown',
                    'entity_count': len(extraction.entities),
                    'task_count': len(extraction.tasks),
                    'has_blockers': str(len(extraction.blockers) > 0),
                }

                # Add to personal_memories collection
                result = await self.chroma_adapter.call_tool("store_memory", {
                    "content": extraction.raw_content,
                    "collection": "personal_memories",
                    "metadata": metadata
                })

                if result.success:
                    vector_id = result.data.get('id') if result.data else memory_id
                    logger.info(f"Vectorized brain dump: {memory_id}")
                else:
                    logger.warning(f"Failed to vectorize: {result.error}")
            except Exception as e:
                logger.warning(f"Failed to vectorize brain dump: {e}")

        # Also store in local SQLite for structured queries
        try:
            from .store import MemoryStore
            store = MemoryStore()
            await store.add_activity(
                activity_type='brain_dump',
                title=extraction.raw_content[:100],
                content=extraction.raw_content,
                source=source,
                metadata={
                    'domains': extraction.domains,
                    'entities': [e.name for e in extraction.entities],
                    'energy': extraction.energy.level if extraction.energy else None,
                    'values': extraction.values_detected,
                    'struggles': extraction.struggles_detected,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to store in SQLite: {e}")

        return memory_id, vector_id

    async def _store_in_workos(self, extraction: BrainDumpExtraction) -> Optional[str]:
        """Store work-related portion in WorkOS."""
        if not self.workos_enabled:
            return None

        try:
            # This will call the WorkOS MCP
            # For now, just log - actual MCP call happens at orchestration layer
            logger.info(f"Would store in WorkOS: {extraction.raw_content[:50]}...")
            return None  # Placeholder
        except Exception as e:
            logger.warning(f"Failed to store in WorkOS: {e}")
            return None

    async def _create_extracted_tasks(self, extraction: BrainDumpExtraction):
        """Create actual tasks from extracted task intentions."""
        for task in extraction.tasks:
            if task.is_work and self.workos_enabled:
                # Create in WorkOS
                logger.info(f"Would create work task: {task.title}")
            else:
                # Create in personal task system
                logger.info(f"Would create personal task: {task.title}")


# Singleton instance
_ingester: Optional[BrainDumpIngester] = None


def get_brain_dump_ingester() -> BrainDumpIngester:
    """Get or create the singleton BrainDumpIngester."""
    global _ingester
    if _ingester is None:
        _ingester = BrainDumpIngester()
    return _ingester


async def ingest_brain_dump(content: str, source: str = "unknown") -> BrainDumpExtraction:
    """
    Convenience function for ingesting a brain dump.

    This is the main entry point for all brain dumps.

    Args:
        content: Raw brain dump text
        source: Where this came from

    Returns:
        Full extraction result
    """
    ingester = get_brain_dump_ingester()
    return await ingester.ingest(content, source)
