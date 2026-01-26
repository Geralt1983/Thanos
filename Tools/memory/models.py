"""
Data models for the Thanos Memory System.

These models represent the core entities tracked by the memory system:
- Activities: Everything the user does
- Struggles: Detected difficulties and blockers
- Values: What matters to the user
- Relationships: People and entities the user cares about
- Summaries: Aggregated daily/weekly data
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
from enum import Enum


# =============================================================================
# Enums
# =============================================================================

class ActivityType(Enum):
    """Types of activities the system tracks."""
    CONVERSATION = "conversation"
    TASK_WORK = "task_work"
    TASK_COMPLETE = "task_complete"
    BRAIN_DUMP = "brain_dump"
    COMMAND = "command"
    CALENDAR_EVENT = "calendar_event"
    HEALTH_LOGGED = "health_logged"
    COMMITMENT_MADE = "commitment_made"
    COMMITMENT_FULFILLED = "commitment_fulfilled"
    FOCUS_SESSION = "focus_session"
    BREAK = "break"
    CONTEXT_SWITCH = "context_switch"


class StruggleType(Enum):
    """Types of struggles the system detects."""
    CONFUSION = "confusion"
    FRUSTRATION = "frustration"
    BLOCKED = "blocked"
    OVERWHELMED = "overwhelmed"
    PROCRASTINATION = "procrastination"
    DECISION_PARALYSIS = "decision_paralysis"
    ENERGY_LOW = "energy_low"
    CONTEXT_SWITCH = "context_switch"
    INTERRUPTION = "interruption"
    TECHNICAL = "technical"
    COMMUNICATION = "communication"
    DEADLINE_PRESSURE = "deadline_pressure"


class ValueType(Enum):
    """Types of user values the system recognizes."""
    PRIORITY = "priority"
    RELATIONSHIP = "relationship"
    COMMITMENT = "commitment"
    PROJECT = "project"
    GOAL = "goal"
    PRINCIPLE = "principle"
    BOUNDARY = "boundary"
    PREFERENCE = "preference"


class Sentiment(Enum):
    """Sentiment classifications."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FRUSTRATED = "frustrated"
    ANXIOUS = "anxious"
    EXCITED = "excited"


class Domain(Enum):
    """Activity domains."""
    WORK = "work"
    PERSONAL = "personal"


class TimeOfDay(Enum):
    """Time of day classifications."""
    MORNING = "morning"      # 5am - 12pm
    AFTERNOON = "afternoon"  # 12pm - 5pm
    EVENING = "evening"      # 5pm - 9pm
    NIGHT = "night"          # 9pm - 5am


# =============================================================================
# Core Models
# =============================================================================

@dataclass
class Activity:
    """
    Represents a single user activity.

    Activities are the fundamental unit of the memory system,
    capturing everything the user does.
    """
    id: str
    timestamp: datetime
    activity_type: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None

    # Context
    project: Optional[str] = None
    domain: Optional[str] = None
    energy_level: Optional[str] = None

    # Duration
    duration_minutes: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    # Source
    source: str = "system"
    source_context: Optional[Dict[str, Any]] = None

    # Relationships
    related_task_id: Optional[str] = None
    related_event_id: Optional[str] = None
    related_commitment_id: Optional[str] = None
    session_id: Optional[str] = None

    # Emotional markers
    sentiment: Optional[str] = None
    struggle_detected: bool = False
    struggle_type: Optional[str] = None

    # Search
    search_text: Optional[str] = None
    embedding_id: Optional[str] = None

    # Metadata
    metadata: Optional[Dict[str, Any]] = None

    # Computed fields
    date: Optional[date] = None
    hour: Optional[int] = None
    day_of_week: Optional[int] = None

    def __post_init__(self):
        """Compute derived fields."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        self.date = self.timestamp.date()
        self.hour = self.timestamp.hour
        self.day_of_week = self.timestamp.weekday()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        if self.date:
            d['date'] = self.date.isoformat()
        if self.started_at:
            d['started_at'] = self.started_at.isoformat()
        if self.ended_at:
            d['ended_at'] = self.ended_at.isoformat()
        return d


@dataclass
class Struggle:
    """
    Represents a detected struggle or difficulty.

    Struggles are identified through linguistic and behavioral
    signals, and tracked over time for pattern recognition.
    """
    id: str
    detected_at: datetime
    struggle_type: str
    title: str
    description: Optional[str] = None
    trigger_text: Optional[str] = None

    # Context
    project: Optional[str] = None
    domain: Optional[str] = None
    related_task_id: Optional[str] = None

    # Temporal
    time_of_day: Optional[str] = None
    day_of_week: Optional[int] = None

    # Resolution
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    # Pattern tracking
    recurrence_count: int = 1
    last_occurred: Optional[datetime] = None

    # Detection metadata
    confidence: float = 0.5
    source_activity_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Compute derived fields."""
        if isinstance(self.detected_at, str):
            self.detected_at = datetime.fromisoformat(self.detected_at)
        if not self.time_of_day:
            hour = self.detected_at.hour
            if 5 <= hour < 12:
                self.time_of_day = TimeOfDay.MORNING.value
            elif 12 <= hour < 17:
                self.time_of_day = TimeOfDay.AFTERNOON.value
            elif 17 <= hour < 21:
                self.time_of_day = TimeOfDay.EVENING.value
            else:
                self.time_of_day = TimeOfDay.NIGHT.value
        if self.day_of_week is None:
            self.day_of_week = self.detected_at.weekday()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['detected_at'] = self.detected_at.isoformat()
        if self.resolved_at:
            d['resolved_at'] = self.resolved_at.isoformat()
        if self.last_occurred:
            d['last_occurred'] = self.last_occurred.isoformat()
        return d


@dataclass
class UserValue:
    """
    Represents a recognized user value or priority.

    Values are detected through explicit statements, emotional
    emphasis, and behavioral patterns.
    """
    id: str
    detected_at: datetime
    last_reinforced: Optional[datetime] = None

    # Value details
    value_type: str = ValueType.PREFERENCE.value
    title: str = ""
    description: Optional[str] = None

    # Importance tracking
    mention_count: int = 1
    emotional_weight: float = 0.5
    explicit_importance: bool = False

    # Context
    domain: Optional[str] = None
    related_entity: Optional[str] = None

    # Status
    is_active: bool = True

    # Evidence
    source_quotes: Optional[List[str]] = None

    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['detected_at'] = self.detected_at.isoformat()
        if self.last_reinforced:
            d['last_reinforced'] = self.last_reinforced.isoformat()
        return d


@dataclass
class Relationship:
    """
    Represents a person or entity the user cares about.

    Relationships are tracked through mentions, commitments,
    and interaction patterns.
    """
    id: str
    entity_name: str
    entity_type: str  # client, colleague, family, friend, stakeholder, vendor, other

    # Importance
    importance: str = "medium"  # critical, high, medium, low
    mention_count: int = 1
    last_mentioned: Optional[datetime] = None

    # Context
    company: Optional[str] = None
    role: Optional[str] = None
    domain: Optional[str] = None

    # Relationship quality
    sentiment_trend: Optional[str] = None  # positive, neutral, negative, mixed

    # Interaction tracking
    last_interaction_date: Optional[date] = None
    interaction_frequency: Optional[str] = None

    # Notes
    notes: Optional[str] = None
    key_facts: Optional[List[str]] = None
    commitments_to: Optional[List[Dict[str, Any]]] = None

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        if self.last_mentioned:
            d['last_mentioned'] = self.last_mentioned.isoformat()
        if self.last_interaction_date:
            d['last_interaction_date'] = self.last_interaction_date.isoformat()
        if self.created_at:
            d['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            d['updated_at'] = self.updated_at.isoformat()
        return d


# =============================================================================
# Summary Models
# =============================================================================

@dataclass
class DaySummary:
    """
    Aggregated summary of a single day's activities.
    """
    date: date

    # Activity counts
    total_activities: int = 0
    tasks_completed: int = 0
    tasks_created: int = 0
    brain_dumps: int = 0
    commands_executed: int = 0

    # Time tracking
    first_activity_time: Optional[time] = None
    last_activity_time: Optional[time] = None
    total_active_minutes: int = 0

    # Productivity metrics
    focus_sessions: int = 0
    focus_minutes: int = 0
    context_switches: int = 0

    # Emotional metrics
    struggles_detected: int = 0
    predominant_sentiment: Optional[str] = None
    energy_trend: Optional[str] = None

    # Domain breakdown
    work_activities: int = 0
    personal_activities: int = 0

    # Projects
    projects_touched: Optional[List[str]] = None

    # Highlights
    key_accomplishments: Optional[List[str]] = None
    notable_struggles: Optional[List[Dict[str, Any]]] = None

    # Health correlation
    oura_readiness: Optional[int] = None
    oura_sleep_score: Optional[int] = None
    oura_activity_score: Optional[int] = None

    # Summary
    generated_summary: Optional[str] = None
    user_reflection: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['date'] = self.date.isoformat()
        if self.first_activity_time:
            d['first_activity_time'] = self.first_activity_time.isoformat()
        if self.last_activity_time:
            d['last_activity_time'] = self.last_activity_time.isoformat()
        return d


@dataclass
class WeekSummary:
    """
    Aggregated summary of a week's activities and patterns.
    """
    week_start: date
    week_end: date

    # Activity patterns
    busiest_day: Optional[int] = None
    quietest_day: Optional[int] = None
    avg_tasks_per_day: float = 0.0
    total_tasks_completed: int = 0

    # Time patterns
    typical_start_hour: Optional[int] = None
    typical_end_hour: Optional[int] = None
    peak_productivity_hours: Optional[List[int]] = None
    total_focus_hours: float = 0.0

    # Struggle patterns
    total_struggles: int = 0
    common_struggle_types: Optional[List[str]] = None
    struggle_peak_times: Optional[List[str]] = None

    # Project focus
    primary_projects: Optional[List[str]] = None
    project_time_distribution: Optional[Dict[str, float]] = None

    # Health correlation
    avg_readiness: Optional[int] = None
    productivity_health_correlation: Optional[float] = None

    # Day summaries
    daily_summaries: Optional[List[DaySummary]] = None

    # Insights
    generated_insights: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['week_start'] = self.week_start.isoformat()
        d['week_end'] = self.week_end.isoformat()
        if self.daily_summaries:
            d['daily_summaries'] = [s.to_dict() for s in self.daily_summaries]
        return d


# =============================================================================
# Query/Result Models
# =============================================================================

@dataclass
class MemoryResult:
    """
    A single result from a memory search or query.
    """
    id: str
    content: str
    relevance_score: float = 0.0

    # Source information
    source_type: str = "activity"  # activity, struggle, value, relationship
    timestamp: Optional[datetime] = None

    # Context
    project: Optional[str] = None
    domain: Optional[str] = None
    entity: Optional[str] = None

    # Additional data
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        if self.timestamp:
            d['timestamp'] = self.timestamp.isoformat()
        return d


@dataclass
class QueryResult:
    """
    Result of a memory query.
    """
    query: str
    query_type: str
    results: List[MemoryResult] = field(default_factory=list)
    summary: Optional[str] = None

    # Query metadata
    date_range: Optional[tuple] = None
    filters_applied: Optional[Dict[str, Any]] = None
    total_matches: int = 0
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'query': self.query,
            'query_type': self.query_type,
            'results': [r.to_dict() for r in self.results],
            'summary': self.summary,
            'date_range': self.date_range,
            'filters_applied': self.filters_applied,
            'total_matches': self.total_matches,
            'execution_time_ms': self.execution_time_ms
        }


@dataclass
class ContextualSurface:
    """
    Contextually surfaced memories for a conversation.
    """
    primary_memory: Optional[MemoryResult] = None
    related_memories: Optional[List[MemoryResult]] = None
    entities_found: Optional[List[str]] = None
    struggle_pattern: Optional[Struggle] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'primary_memory': self.primary_memory.to_dict() if self.primary_memory else None,
            'related_memories': [m.to_dict() for m in (self.related_memories or [])],
            'entities_found': self.entities_found,
            'struggle_pattern': self.struggle_pattern.to_dict() if self.struggle_pattern else None
        }
