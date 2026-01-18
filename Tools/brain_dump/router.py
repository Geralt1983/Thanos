#!/usr/bin/env python3
"""
Brain Dump Router for Thanos.

Routes classified brain dumps to appropriate destinations:
- Tasks (work/personal) to state store and optionally WorkOS
- Commitments to state store
- Ideas and notes to state store
- Reflective entries (thinking, venting, observation) to journal only

The router ensures all entries are archived and logged appropriately.
"""

import uuid
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from Tools.unified_state import StateStore
    from Tools.journal import Journal
    from Tools.adapters.workos import WorkOSAdapter

# Import ClassifiedBrainDump from classifier
from .classifier import ClassifiedBrainDump


class Classification(Enum):
    """Classification types for brain dump content."""

    # Reflective types - journal only, no tasks created
    THINKING = "thinking"
    VENTING = "venting"
    OBSERVATION = "observation"

    # Capture types - stored in state
    NOTE = "note"
    IDEA = "idea"

    # Actionable types - create tasks/commitments
    PERSONAL_TASK = "personal_task"
    WORK_TASK = "work_task"
    COMMITMENT = "commitment"

    # Mixed content requiring segment-by-segment processing
    MIXED = "mixed"

    @classmethod
    def from_string(cls, value: str) -> "Classification":
        """Convert string to Classification enum."""
        try:
            return cls(value)
        except ValueError:
            # Default to thinking for unknown classifications
            return cls.THINKING


@dataclass
class ClassifiedSegment:
    """A segment of a brain dump with its classification."""

    content: str
    classification: Union[Classification, str]
    confidence: float = 1.0
    entities: Optional[List[str]] = None
    priority: Optional[str] = None
    stakeholder: Optional[str] = None
    deadline: Optional[str] = None
    task: Optional[Dict[str, Any]] = None
    commitment: Optional[Dict[str, Any]] = None
    idea: Optional[Dict[str, Any]] = None
    note: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    @property
    def classification_enum(self) -> Classification:
        """Get classification as enum."""
        if isinstance(self.classification, Classification):
            return self.classification
        return Classification.from_string(self.classification)


@dataclass
class RoutingResult:
    """
    Result of routing a brain dump to its destinations.

    Tracks all created entities and acknowledgments for the routing operation.
    """

    dump_id: str
    tasks_created: List[str] = field(default_factory=list)
    commitment_created: Optional[str] = None
    idea_created: Optional[str] = None
    note_created: Optional[str] = None
    journal_entry: Optional[int] = None
    acknowledgment: Optional[str] = None
    workos_task_id: Optional[int] = None
    errors: List[str] = field(default_factory=list)

    def merge(self, other: "RoutingResult") -> "RoutingResult":
        """
        Merge results from another routing operation.

        Used when processing mixed classification brain dumps
        where each segment produces its own result.

        Args:
            other: Another RoutingResult to merge in.

        Returns:
            Self with merged results.
        """
        self.tasks_created.extend(other.tasks_created)

        # For single-value fields, keep first non-None value
        if other.commitment_created and not self.commitment_created:
            self.commitment_created = other.commitment_created
        if other.idea_created and not self.idea_created:
            self.idea_created = other.idea_created
        if other.note_created and not self.note_created:
            self.note_created = other.note_created
        if other.workos_task_id and not self.workos_task_id:
            self.workos_task_id = other.workos_task_id

        self.errors.extend(other.errors)

        return self

    @property
    def success(self) -> bool:
        """Check if routing completed without errors."""
        return len(self.errors) == 0

    def summary(self) -> str:
        """Generate a human-readable summary of routing results."""
        parts = []

        if self.tasks_created:
            parts.append(f"{len(self.tasks_created)} task(s) created")
        if self.commitment_created:
            parts.append("commitment created")
        if self.idea_created:
            parts.append("idea captured")
        if self.note_created:
            parts.append("note captured")
        if self.journal_entry:
            parts.append("logged to journal")
        if self.workos_task_id:
            parts.append(f"synced to WorkOS (#{self.workos_task_id})")
        if self.errors:
            parts.append(f"{len(self.errors)} error(s)")

        return ", ".join(parts) if parts else "no actions taken"


class BrainDumpRouter:
    """
    Routes classified brain dumps to appropriate destinations.

    Routing rules:
    - thinking, venting, observation: Journal only, NO tasks created
    - note: Create note in state store, log to journal
    - idea: Create idea in state store, log to journal
    - personal_task: Create task with domain="personal", log to journal
    - work_task: Create task with domain="work", sync to WorkOS if adapter provided
    - commitment: Create commitment in state store, log to journal
    - mixed: Recursively route each segment, merge results

    All brain dumps are archived regardless of classification.
    """

    def __init__(
        self,
        state: "StateStore",
        journal: "Journal",
        workos_adapter: Optional["WorkOSAdapter"] = None
    ):
        """
        Initialize the brain dump router.

        Args:
            state: StateStore for persisting tasks, commitments, notes, ideas.
            journal: Journal for logging all brain dump events.
            workos_adapter: Optional WorkOS adapter for syncing work tasks.
        """
        self.state = state
        self.journal = journal
        self.workos_adapter = workos_adapter

    async def route(self, dump: ClassifiedBrainDump) -> RoutingResult:
        """
        Route a classified brain dump to appropriate destinations.

        Args:
            dump: The classified brain dump to route (from BrainDumpClassifier).

        Returns:
            RoutingResult with all created entities and status.
        """
        result = RoutingResult(dump_id=dump.id)

        try:
            # Archive the raw dump first
            await self._archive_dump(dump)

            # Get classification as enum
            classification = Classification.from_string(dump.classification)

            # Route based on classification
            if classification == Classification.MIXED:
                result = await self._route_mixed(dump, result)
            else:
                result = await self._route_single(dump, classification, result)

            # Use acknowledgment from classifier if available
            if dump.acknowledgment and not result.acknowledgment:
                result.acknowledgment = dump.acknowledgment

        except Exception as e:
            result.errors.append(f"Routing failed: {str(e)}")

        return result

    async def _route_single(
        self,
        dump: ClassifiedBrainDump,
        classification: Classification,
        result: RoutingResult
    ) -> RoutingResult:
        """Route a single-classification brain dump."""

        # Reflective types - journal only
        if classification in (
            Classification.THINKING,
            Classification.VENTING,
            Classification.OBSERVATION
        ):
            result = await self._route_reflective(dump, classification, result)

        # Capture types
        elif classification == Classification.NOTE:
            result = await self._route_note(dump, result)

        elif classification == Classification.IDEA:
            result = await self._route_idea(dump, result)

        # Actionable types
        elif classification == Classification.PERSONAL_TASK:
            result = await self._route_personal_task(dump, result)

        elif classification == Classification.WORK_TASK:
            result = await self._route_work_task(dump, result)

        elif classification == Classification.COMMITMENT:
            result = await self._route_commitment(dump, result)

        return result

    async def _route_mixed(
        self,
        dump: ClassifiedBrainDump,
        result: RoutingResult
    ) -> RoutingResult:
        """Route a mixed-classification brain dump by processing each segment."""

        if not dump.segments:
            # No segments, treat as a note
            result = await self._route_note(dump, result)
            return result

        for segment_data in dump.segments:
            # Convert segment dict to ClassifiedSegment
            segment = ClassifiedSegment(
                content=segment_data.get('text', ''),
                classification=segment_data.get('classification', 'thinking'),
                task=segment_data.get('extracted', {}).get('task') if segment_data.get('extracted') else segment_data.get('task'),
                commitment=segment_data.get('extracted', {}).get('commitment') if segment_data.get('extracted') else segment_data.get('commitment'),
                idea=segment_data.get('extracted', {}).get('idea') if segment_data.get('extracted') else segment_data.get('idea'),
                note=segment_data.get('extracted', {}).get('note') if segment_data.get('extracted') else segment_data.get('note'),
            )

            # Create a mini-dump for each segment
            segment_dump = self._create_segment_dump(dump, segment)

            # Route the segment and merge results
            segment_classification = segment.classification_enum
            segment_result = await self._route_single(
                segment_dump,
                segment_classification,
                RoutingResult(dump_id=segment_dump.id)
            )
            result.merge(segment_result)

        # Log the mixed dump as a whole
        self.journal.log(
            event_type="brain_dump_mixed",
            source="brain_dump",
            title=f"Mixed brain dump processed: {len(dump.segments)} segments",
            data={
                "dump_id": dump.id,
                "segment_count": len(dump.segments),
                "tasks_created": len(result.tasks_created),
                "classifications": [s.get('classification', 'unknown') for s in dump.segments]
            },
            severity="info"
        )

        return result

    def _create_segment_dump(
        self,
        parent: ClassifiedBrainDump,
        segment: ClassifiedSegment
    ) -> ClassifiedBrainDump:
        """Create a ClassifiedBrainDump from a segment."""
        return ClassifiedBrainDump(
            id=f"{parent.id}_seg_{uuid.uuid4().hex[:4]}",
            raw_text=segment.content,
            source=parent.source,
            classification=segment.classification if isinstance(segment.classification, str)
                           else segment.classification.value,
            confidence=segment.confidence,
            reasoning=f"Segment from mixed dump {parent.id}",
            task=segment.task,
            commitment=segment.commitment,
            idea=segment.idea,
            note=segment.note,
        )

    async def _route_reflective(
        self,
        dump: ClassifiedBrainDump,
        classification: Classification,
        result: RoutingResult
    ) -> RoutingResult:
        """Route reflective content (thinking, venting, observation) to journal only."""

        # Map classification to event type
        event_type_map = {
            Classification.THINKING: "brain_dump_thinking",
            Classification.VENTING: "brain_dump_venting",
            Classification.OBSERVATION: "brain_dump_observation"
        }

        event_type = event_type_map.get(classification, "brain_dump_received")

        # Log to journal only - no task creation
        entry_id = self.journal.log(
            event_type=event_type,
            source="brain_dump",
            title=self._generate_title(dump),
            data={
                "dump_id": dump.id,
                "content": dump.raw_text,
                "classification": dump.classification,
                "confidence": dump.confidence,
                "reasoning": dump.reasoning,
                "source": dump.source,
            },
            severity="info"
        )

        result.journal_entry = entry_id
        result.acknowledgment = dump.acknowledgment or self._generate_acknowledgment(classification)

        return result

    async def _route_note(
        self,
        dump: ClassifiedBrainDump,
        result: RoutingResult
    ) -> RoutingResult:
        """Route note to state store and journal."""

        try:
            # Create note in state store
            note_id = await self._create_note(dump)
            result.note_created = note_id

            # Log to journal
            entry_id = self.journal.log(
                event_type="note_captured",
                source="brain_dump",
                title=f"Note captured: {self._generate_title(dump)}",
                data={
                    "dump_id": dump.id,
                    "note_id": note_id,
                    "content": dump.raw_text[:200],
                    "source": dump.source
                },
                severity="info"
            )
            result.journal_entry = entry_id
            result.acknowledgment = f"Note captured: {note_id}"

        except Exception as e:
            result.errors.append(f"Failed to create note: {str(e)}")

        return result

    async def _route_idea(
        self,
        dump: ClassifiedBrainDump,
        result: RoutingResult
    ) -> RoutingResult:
        """Route idea to state store and journal."""

        try:
            # Create idea in state store
            idea_id = await self._create_idea(dump)
            result.idea_created = idea_id

            # Log to journal
            entry_id = self.journal.log(
                event_type="idea_captured",
                source="brain_dump",
                title=f"Idea captured: {self._generate_title(dump)}",
                data={
                    "dump_id": dump.id,
                    "idea_id": idea_id,
                    "content": dump.raw_text[:200],
                    "source": dump.source
                },
                severity="info"
            )
            result.journal_entry = entry_id
            result.acknowledgment = f"Idea captured: {idea_id}"

        except Exception as e:
            result.errors.append(f"Failed to create idea: {str(e)}")

        return result

    async def _route_personal_task(
        self,
        dump: ClassifiedBrainDump,
        result: RoutingResult
    ) -> RoutingResult:
        """Route personal task to state store and journal. Does NOT touch WorkOS."""

        try:
            # Create task in state store with domain="personal"
            task_id = await self._create_task(dump, domain="personal")
            result.tasks_created.append(task_id)

            # Log to journal
            entry_id = self.journal.log(
                event_type="task_created",
                source="brain_dump",
                title=f"Personal task created: {self._generate_title(dump)}",
                data={
                    "dump_id": dump.id,
                    "task_id": task_id,
                    "domain": "personal",
                    "priority": dump.task.get('priority') if dump.task else None,
                    "source": dump.source
                },
                severity="info"
            )
            result.journal_entry = entry_id
            result.acknowledgment = f"Personal task created: {task_id}"

        except Exception as e:
            result.errors.append(f"Failed to create personal task: {str(e)}")

        return result

    async def _route_work_task(
        self,
        dump: ClassifiedBrainDump,
        result: RoutingResult
    ) -> RoutingResult:
        """Route work task to state store, WorkOS (if available), and journal."""

        try:
            # Create task in state store with domain="work"
            task_id = await self._create_task(dump, domain="work")
            result.tasks_created.append(task_id)

            # Sync to WorkOS if adapter is available
            if self.workos_adapter:
                workos_id = await self._sync_to_workos(dump)
                result.workos_task_id = workos_id

            # Log to journal
            entry_id = self.journal.log(
                event_type="task_created",
                source="brain_dump",
                title=f"Work task created: {self._generate_title(dump)}",
                data={
                    "dump_id": dump.id,
                    "task_id": task_id,
                    "domain": "work",
                    "workos_id": result.workos_task_id,
                    "priority": dump.task.get('priority') if dump.task else None,
                    "source": dump.source
                },
                severity="info"
            )
            result.journal_entry = entry_id

            if result.workos_task_id:
                result.acknowledgment = f"Work task created: {task_id} (WorkOS #{result.workos_task_id})"
            else:
                result.acknowledgment = f"Work task created: {task_id}"

        except Exception as e:
            result.errors.append(f"Failed to create work task: {str(e)}")

        return result

    async def _route_commitment(
        self,
        dump: ClassifiedBrainDump,
        result: RoutingResult
    ) -> RoutingResult:
        """Route commitment to state store and journal."""

        try:
            # Create commitment in state store
            commitment_id = await self._create_commitment(dump)
            result.commitment_created = commitment_id

            # Log to journal
            stakeholder = dump.commitment.get('to_whom') if dump.commitment else None
            deadline = dump.commitment.get('deadline') if dump.commitment else None

            entry_id = self.journal.log(
                event_type="commitment_created",
                source="brain_dump",
                title=f"Commitment created: {self._generate_title(dump)}",
                data={
                    "dump_id": dump.id,
                    "commitment_id": commitment_id,
                    "stakeholder": stakeholder,
                    "deadline": deadline,
                    "source": dump.source
                },
                severity="info"
            )
            result.journal_entry = entry_id
            result.acknowledgment = f"Commitment created: {commitment_id}"

        except Exception as e:
            result.errors.append(f"Failed to create commitment: {str(e)}")

        return result

    # ==================== Helper Methods ====================

    async def _archive_dump(self, dump: ClassifiedBrainDump) -> None:
        """Archive the raw brain dump for future reference."""
        archive_key = f"brain_dump_archive:{dump.id}"
        archive_data = {
            "id": dump.id,
            "raw_text": dump.raw_text,
            "classification": dump.classification,
            "confidence": dump.confidence,
            "reasoning": dump.reasoning,
            "source": dump.source,
            "timestamp": dump.timestamp,
            "archived_at": datetime.now().isoformat()
        }

        # Use state store's set_state if available (for SQLiteStateStore compatibility)
        if hasattr(self.state, 'set_state'):
            self.state.set_state(archive_key, archive_data)
        elif hasattr(self.state, '_get_connection'):
            # For StateStore (unified_state), store in generic state table
            import json
            with self.state._get_connection() as conn:
                # Check if state table exists, create if not
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS state (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.execute('''
                    INSERT OR REPLACE INTO state (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (archive_key, json.dumps(archive_data)))

    async def _create_note(self, dump: ClassifiedBrainDump) -> str:
        """Create a note in the state store."""
        # Get note content from parsed data or raw text
        note_content = dump.note.get('content') if dump.note else dump.raw_text

        # StateStore doesn't have a notes table, so we use tasks with a special source
        note_id = self.state.add_task(
            title=self._generate_title(dump),
            description=note_content,
            source="brain_dump_note",
            metadata={
                "dump_id": dump.id,
                "type": "note",
                "category": dump.note.get('category') if dump.note else None
            }
        )
        return note_id

    async def _create_idea(self, dump: ClassifiedBrainDump) -> str:
        """Create an idea in the state store."""
        # Get idea data from parsed data
        idea_title = dump.idea.get('title') if dump.idea else self._generate_title(dump)
        idea_desc = dump.idea.get('description') if dump.idea else dump.raw_text

        # Use tasks with a special source for ideas
        idea_id = self.state.add_task(
            title=idea_title,
            description=idea_desc,
            source="brain_dump_idea",
            metadata={
                "dump_id": dump.id,
                "type": "idea",
                "category": dump.idea.get('category') if dump.idea else None
            }
        )
        return idea_id

    async def _create_task(self, dump: ClassifiedBrainDump, domain: str) -> str:
        """Create a task in the state store."""
        # Get task data from parsed data
        task_data = dump.task or {}
        task_title = task_data.get('title') or self._generate_title(dump)
        task_desc = task_data.get('description') or dump.raw_text
        priority = task_data.get('priority')

        task_id = self.state.add_task(
            title=task_title,
            description=task_desc,
            priority=priority,
            source="brain_dump",
            metadata={
                "dump_id": dump.id,
                "domain": domain,
                "classification": dump.classification,
                "estimated_effort": task_data.get('estimated_effort')
            }
        )
        return task_id

    async def _create_commitment(self, dump: ClassifiedBrainDump) -> str:
        """Create a commitment in the state store."""
        # Get commitment data from parsed data
        commitment_data = dump.commitment or {}
        title = commitment_data.get('description') or self._generate_title(dump)
        stakeholder = commitment_data.get('to_whom')
        deadline_str = commitment_data.get('deadline')

        # Parse deadline if provided
        deadline = None
        if deadline_str:
            try:
                # Try to parse common date formats
                if isinstance(deadline_str, str):
                    # Handle "Friday", "next week", etc. - for now just pass through
                    # A more sophisticated parser could be added here
                    pass
            except (ValueError, TypeError):
                pass

        commitment_id = self.state.add_commitment(
            title=title,
            description=dump.raw_text,
            stakeholder=stakeholder,
            deadline=deadline,
            metadata={
                "dump_id": dump.id,
                "raw_deadline": deadline_str,
                "source": dump.source
            }
        )
        return commitment_id

    async def _sync_to_workos(self, dump: ClassifiedBrainDump) -> Optional[int]:
        """Sync a work task to WorkOS database."""
        if not self.workos_adapter:
            return None

        try:
            # Get task data
            task_data = dump.task or {}

            # Map priority to effort estimate
            effort_map = {
                "critical": 5,
                "high": 4,
                "medium": 3,
                "low": 2
            }
            priority = task_data.get('priority', 'medium')
            effort = effort_map.get(priority, 2)

            result = await self.workos_adapter.call_tool(
                "create_task",
                {
                    "title": task_data.get('title') or self._generate_title(dump),
                    "description": dump.raw_text,
                    "status": "backlog",
                    "effort_estimate": effort
                }
            )

            if result.success and result.data:
                return result.data.get("id")

        except Exception:
            # WorkOS sync failures are non-fatal
            pass

        return None

    def _generate_title(self, dump: ClassifiedBrainDump) -> str:
        """Generate a title from the brain dump content."""
        # Check for title in task/idea/note data
        if dump.task and dump.task.get('title'):
            return dump.task['title']
        if dump.idea and dump.idea.get('title'):
            return dump.idea['title']

        # Use first line or first 50 chars of raw text
        first_line = dump.raw_text.split('\n')[0].strip()
        if len(first_line) <= 50:
            return first_line
        return first_line[:47] + "..."

    def _generate_acknowledgment(self, classification: Classification) -> str:
        """Generate an acknowledgment message for the user."""
        ack_map = {
            Classification.THINKING: "Thought noted. Take your time.",
            Classification.VENTING: "I hear you. No action needed.",
            Classification.OBSERVATION: "Observation recorded.",
            Classification.NOTE: "Note captured.",
            Classification.IDEA: "Idea captured for later.",
            Classification.PERSONAL_TASK: "Personal task created.",
            Classification.WORK_TASK: "Work task created.",
            Classification.COMMITMENT: "Commitment tracked.",
            Classification.MIXED: "Multiple items processed."
        }

        return ack_map.get(classification, "Brain dump received.")


# Convenience function for routing
async def route_brain_dump(
    dump: ClassifiedBrainDump,
    state: "StateStore",
    journal: "Journal",
    workos_adapter: Optional["WorkOSAdapter"] = None
) -> RoutingResult:
    """
    Convenience function to route a classified brain dump.

    Args:
        dump: The classified brain dump from BrainDumpClassifier.
        state: StateStore for persisting data.
        journal: Journal for logging.
        workos_adapter: Optional WorkOS adapter for work tasks.

    Returns:
        RoutingResult with all created entities.
    """
    router = BrainDumpRouter(state, journal, workos_adapter)
    return await router.route(dump)
