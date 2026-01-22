#!/usr/bin/env python3
"""
Data Models for Accountability Architecture.

Defines the core data structures for brain dump processing,
impact scoring, work prioritization, and planning enforcement.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any


class BrainDumpCategory(Enum):
    """Classification categories for brain dumps."""
    THOUGHT = "thought"           # Store for pattern discovery
    PROJECT = "project"           # Decompose into tasks
    TASK = "task"                # Route to work/personal
    WORRY = "worry"              # Convert to actionable task
    OBSERVATION = "observation"   # Log for later reference
    IDEA = "idea"                # Creative spark to explore


class TaskDomain(Enum):
    """Work or personal task domain."""
    WORK = "work"
    PERSONAL = "personal"


class ImpactDimension(Enum):
    """The four stones of impact."""
    HEALTH = "health"           # Physical and mental wellbeing
    STRESS = "stress"           # Anxiety and cognitive load
    FINANCIAL = "financial"     # Money, wealth, security
    RELATIONSHIP = "relationship"  # Family, friends, connections


class WorkPriorityMode(Enum):
    """Modes for prioritizing work tasks."""
    BIGGEST_PILE = "biggest_pile"      # Most backlogged client
    MOST_IGNORED = "most_ignored"      # Longest since last touch
    ENERGY_MATCH = "energy_match"      # Match to current readiness


class PlanningStatus(Enum):
    """Status of daily planning."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    SKIPPED = "skipped"


@dataclass
class ImpactScore:
    """
    Impact scoring across the four dimensions.

    Each dimension scored 0-10:
    - 0: No impact
    - 5: Moderate impact
    - 10: Critical/urgent impact
    """
    health: float = 0.0
    stress: float = 0.0
    financial: float = 0.0
    relationship: float = 0.0

    # Weights for composite calculation
    WEIGHTS = {
        'health': 1.5,        # Prioritize health
        'stress': 1.2,        # High weight on stress reduction
        'financial': 1.0,     # Standard weight
        'relationship': 1.3   # Relationships matter
    }

    @property
    def composite(self) -> float:
        """
        Calculate weighted composite score.

        Returns:
            Float between 0-10 representing overall impact.
        """
        total = (
            self.health * self.WEIGHTS['health'] +
            self.stress * self.WEIGHTS['stress'] +
            self.financial * self.WEIGHTS['financial'] +
            self.relationship * self.WEIGHTS['relationship']
        )
        return total / sum(self.WEIGHTS.values())

    @property
    def primary_dimension(self) -> ImpactDimension:
        """Get the highest-scoring dimension."""
        scores = {
            ImpactDimension.HEALTH: self.health,
            ImpactDimension.STRESS: self.stress,
            ImpactDimension.FINANCIAL: self.financial,
            ImpactDimension.RELATIONSHIP: self.relationship,
        }
        return max(scores, key=scores.get)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'health': self.health,
            'stress': self.stress,
            'financial': self.financial,
            'relationship': self.relationship,
            'composite': self.composite,
            'primary': self.primary_dimension.value,
        }


@dataclass
class ClassifiedBrainDump:
    """A brain dump that has been classified and processed."""
    id: int
    raw_content: str
    category: BrainDumpCategory
    domain: Optional[TaskDomain] = None
    impact_score: Optional[ImpactScore] = None

    # Extracted metadata
    title: Optional[str] = None
    entities: List[str] = field(default_factory=list)
    deadline: Optional[date] = None
    energy_hint: Optional[str] = None  # high/medium/low
    blockers: List[str] = field(default_factory=list)

    # Processing metadata
    processed_at: datetime = field(default_factory=datetime.now)
    source: str = "unknown"  # telegram, voice, direct

    # AI oversight fields
    confidence: float = 1.0  # 0-1 confidence in classification
    needs_review: bool = False  # Flag for AI/human review
    review_reason: Optional[str] = None  # Why review is needed

    # Resulting items
    created_tasks: List[int] = field(default_factory=list)
    linked_projects: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'raw_content': self.raw_content,
            'category': self.category.value,
            'domain': self.domain.value if self.domain else None,
            'impact_score': self.impact_score.to_dict() if self.impact_score else None,
            'title': self.title,
            'entities': self.entities,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'energy_hint': self.energy_hint,
            'blockers': self.blockers,
            'processed_at': self.processed_at.isoformat(),
            'source': self.source,
            'confidence': self.confidence,
            'needs_review': self.needs_review,
            'review_reason': self.review_reason,
            'created_tasks': self.created_tasks,
            'linked_projects': self.linked_projects,
        }


@dataclass
class ClientWorkload:
    """Work metrics for a single client."""
    client_id: int
    client_name: str
    task_count: int                    # Total active tasks
    days_since_touch: int              # Days since last interaction
    oldest_task_age: int               # Age of oldest task in days
    high_priority_count: int           # Number of high priority items
    total_points: int                  # Sum of task point values

    def priority_score(self, mode: WorkPriorityMode, current_readiness: int = 70) -> float:
        """
        Calculate priority score based on mode.

        Args:
            mode: The prioritization mode to use.
            current_readiness: Current Oura readiness score (for energy matching).

        Returns:
            Priority score (higher = more urgent).
        """
        if mode == WorkPriorityMode.BIGGEST_PILE:
            # Prioritize by task count with bonus for high priority
            return self.task_count * 10 + self.high_priority_count * 5

        elif mode == WorkPriorityMode.MOST_IGNORED:
            # Prioritize by neglect with penalty for task age
            return self.days_since_touch * 5 + self.oldest_task_age * 2

        elif mode == WorkPriorityMode.ENERGY_MATCH:
            # Match average task complexity to current energy
            # Lower readiness = prefer simpler tasks
            if current_readiness < 60:
                # Low energy: prefer small piles
                return -self.task_count * 5  # Negative so small piles rank higher
            elif current_readiness < 75:
                # Medium energy: balanced
                return self.task_count + self.days_since_touch
            else:
                # High energy: tackle big challenges
                return self.task_count * 10

        # Default: combined score
        return self.task_count + self.days_since_touch + self.oldest_task_age

    def to_dict(self) -> Dict[str, Any]:
        return {
            'client_id': self.client_id,
            'client_name': self.client_name,
            'task_count': self.task_count,
            'days_since_touch': self.days_since_touch,
            'oldest_task_age': self.oldest_task_age,
            'high_priority_count': self.high_priority_count,
            'total_points': self.total_points,
        }


@dataclass
class PlanningRecord:
    """Record of daily planning activity."""
    date: date
    planned_at: Optional[datetime] = None
    tasks_planned: int = 0
    goal_set: int = 0
    was_planned: bool = False
    reminder_count: int = 0

    # Escalation tracking
    reminders_sent: List[str] = field(default_factory=list)  # timestamps

    # Outcome tracking (filled next day)
    tasks_completed: int = 0
    goal_achieved: bool = False
    actual_points: int = 0
    notes: str = ""

    @property
    def planning_streak_broken(self) -> bool:
        """Check if this day broke the planning streak."""
        return not self.was_planned and self.reminder_count >= 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            'date': self.date.isoformat(),
            'planned_at': self.planned_at.isoformat() if self.planned_at else None,
            'tasks_planned': self.tasks_planned,
            'goal_set': self.goal_set,
            'was_planned': self.was_planned,
            'reminder_count': self.reminder_count,
            'reminders_sent': self.reminders_sent,
            'tasks_completed': self.tasks_completed,
            'goal_achieved': self.goal_achieved,
            'actual_points': self.actual_points,
            'notes': self.notes,
            'planning_streak_broken': self.planning_streak_broken,
        }


@dataclass
class AccountabilityMetrics:
    """Aggregate accountability metrics."""
    planning_streak: int = 0
    total_planned_days: int = 0
    total_days: int = 0
    brain_dumps_processed: int = 0
    average_processing_time: float = 0.0
    impact_coverage: float = 0.0  # % of personal tasks with impact scores

    # Client balance (lower = more balanced)
    client_attention_stddev: float = 0.0

    @property
    def planning_compliance(self) -> float:
        """Percentage of days that were planned."""
        if self.total_days == 0:
            return 0.0
        return (self.total_planned_days / self.total_days) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            'planning_streak': self.planning_streak,
            'planning_compliance': self.planning_compliance,
            'total_planned_days': self.total_planned_days,
            'total_days': self.total_days,
            'brain_dumps_processed': self.brain_dumps_processed,
            'average_processing_time': self.average_processing_time,
            'impact_coverage': self.impact_coverage,
            'client_attention_stddev': self.client_attention_stddev,
        }


# Impact keyword mappings for scoring
IMPACT_KEYWORDS = {
    ImpactDimension.HEALTH: [
        'doctor', 'gym', 'exercise', 'workout', 'sleep', 'medication',
        'diet', 'health', 'medical', 'appointment', 'therapy', 'dentist',
        'physical', 'mental', 'wellness', 'checkup', 'prescription',
        'vitamin', 'supplement', 'injury', 'pain', 'sick', 'ill'
    ],
    ImpactDimension.STRESS: [
        'deadline', 'overdue', 'urgent', 'overwhelmed', 'anxiety',
        'stressed', 'worried', 'panic', 'pressure', 'asap', 'emergency',
        'behind', 'late', 'forgot', 'reminder', 'must', 'have to',
        'critical', 'important', 'blocking', 'stuck'
    ],
    ImpactDimension.FINANCIAL: [
        'payment', 'bill', 'invoice', 'money', 'budget', 'tax',
        'expense', 'cost', 'price', 'salary', 'income', 'savings',
        'debt', 'loan', 'credit', 'bank', 'financial', 'insurance',
        'rent', 'mortgage', 'subscription', 'refund'
    ],
    ImpactDimension.RELATIONSHIP: [
        'call', 'visit', 'birthday', 'anniversary', 'family',
        'friend', 'mom', 'dad', 'wife', 'husband', 'kid', 'child',
        'parent', 'sibling', 'brother', 'sister', 'wedding', 'gift',
        'thank', 'apologize', 'check in', 'catch up', 'meet'
    ],
}

# Classification keywords
CATEGORY_KEYWORDS = {
    BrainDumpCategory.PROJECT: [
        'project', 'initiative', 'plan', 'goal', 'objective',
        'milestone', 'launch', 'release', 'build', 'create',
        'develop', 'implement', 'design', 'architect'
    ],
    BrainDumpCategory.TASK: [
        'do', 'need to', 'should', 'must', 'have to', 'todo',
        'action', 'complete', 'finish', 'send', 'call', 'email',
        'buy', 'get', 'fix', 'update', 'review', 'check'
    ],
    BrainDumpCategory.WORRY: [
        'worried', 'anxious', 'concerned', 'afraid', 'scared',
        'what if', 'might', 'could go wrong', 'risk', 'problem',
        'issue', 'trouble', 'fear', 'stress'
    ],
    BrainDumpCategory.IDEA: [
        'idea', 'maybe', 'could', 'wonder', 'interesting',
        'thought about', 'what about', 'possibility', 'explore'
    ],
    BrainDumpCategory.OBSERVATION: [
        'noticed', 'observed', 'saw', 'found', 'interesting',
        'fyi', 'note', 'remember'
    ],
}
