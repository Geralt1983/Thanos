"""Data models for pattern recognition engine.

This module defines the core data structures for representing patterns, correlations,
streaks, trends, and insights discovered through analysis of historical data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PatternType(Enum):
    """Types of task completion patterns."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    TASK_TYPE = "task_type"


class TrendDirection(Enum):
    """Direction of a detected trend."""
    IMPROVING = "improving"
    DECLINING = "declining"
    PLATEAU = "plateau"
    VOLATILE = "volatile"


class InsightCategory(Enum):
    """Categories of insights."""
    TASK_COMPLETION = "task_completion"
    HEALTH_CORRELATION = "health_correlation"
    HABIT = "habit"
    TREND = "trend"
    BEHAVIORAL = "behavioral"


@dataclass
class TaskCompletionPattern:
    """Pattern of task completions identified through analysis.

    Examples:
        - "Most productive between 9-11am"
        - "Mondays have 30% lower completion rate"
        - "Deep work tasks completed best in morning"
    """
    pattern_type: PatternType
    description: str
    time_period: str  # e.g., "9-11am", "Monday", "weekends"
    completion_rate: float  # Average completion rate for this pattern
    sample_size: int  # Number of data points supporting this pattern
    confidence_score: float  # 0.0 to 1.0
    date_range_start: datetime
    date_range_end: datetime
    evidence: List[str]  # Supporting data points or observations
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")


@dataclass
class HealthCorrelation:
    """Correlation between health metrics and productivity/behavior.

    Examples:
        - "7+ hours sleep correlates with 40% more tasks completed"
        - "Readiness score >85 predicts high-energy days"
        - "Deep sleep <90min correlates with lower focus"
    """
    health_metric: str  # e.g., "sleep_duration", "readiness_score", "deep_sleep"
    productivity_metric: str  # e.g., "tasks_completed", "focus_score", "energy_level"
    correlation_strength: float  # -1.0 to 1.0 (Pearson correlation coefficient)
    correlation_description: str  # Human-readable description
    threshold_value: Optional[float] = None  # e.g., 7 hours for sleep
    effect_size: Optional[float] = None  # Quantified impact (e.g., 40% more tasks)
    confidence_score: float = 0.0  # 0.0 to 1.0
    sample_size: int = 0
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate scores."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        if not -1.0 <= self.correlation_strength <= 1.0:
            raise ValueError("Correlation strength must be between -1.0 and 1.0")


@dataclass
class HabitStreak:
    """Information about a habit streak and its consistency.

    Examples:
        - "Daily review: 45-day streak (current)"
        - "Exercise: 12-day streak broken on 2024-01-15"
        - "Meditation: 89% consistency over 90 days"
    """
    habit_name: str
    streak_length: int  # Days in current/past streak
    is_active: bool  # Whether streak is currently active
    last_completion_date: datetime
    break_date: Optional[datetime] = None  # When streak was broken (if not active)
    break_reasons: List[str] = field(default_factory=list)  # Identified reasons for breaks
    consistency_score: float = 0.0  # 0.0 to 1.0 - percentage of days completed
    longest_streak: int = 0  # Longest streak ever for this habit
    total_completions: int = 0  # Total times habit was completed
    confidence_score: float = 0.0  # 0.0 to 1.0
    date_range_start: datetime = field(default_factory=datetime.now)
    date_range_end: datetime = field(default_factory=datetime.now)
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate scores."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        if not 0.0 <= self.consistency_score <= 1.0:
            raise ValueError("Consistency score must be between 0.0 and 1.0")


@dataclass
class Trend:
    """Detected trend in a metric over time.

    Examples:
        - "Tasks per day increasing (7.2 → 9.4 over 30 days)"
        - "Sleep quality declining (avg 85 → 72 in readiness)"
        - "Momentum building: 7-day trend shows consistent improvement"
    """
    metric_name: str  # e.g., "tasks_per_day", "readiness_score", "deep_sleep"
    trend_direction: TrendDirection
    trend_description: str  # Human-readable description
    start_value: float  # Metric value at start of period
    end_value: float  # Metric value at end of period
    change_percentage: float  # Percentage change
    trend_strength: float  # 0.0 to 1.0 - how strong/consistent is the trend
    momentum_indicator: str  # e.g., "7-day", "30-day"
    confidence_score: float = 0.0  # 0.0 to 1.0
    sample_size: int = 0
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate scores."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        if not 0.0 <= self.trend_strength <= 1.0:
            raise ValueError("Trend strength must be between 0.0 and 1.0")


@dataclass
class Insight:
    """Actionable insight derived from patterns, correlations, or trends.

    This is the primary output of the pattern recognition engine - insights that
    can be presented to the user in weekly reviews or on-demand queries.

    Examples:
        - "Schedule deep work in mornings when you're 40% more productive"
        - "Prioritize sleep: 7+ hours correlates with significantly better task completion"
        - "Your daily review habit streak is at risk - last 3 breaks happened on Fridays"
    """
    summary: str  # 1-2 sentence description
    category: InsightCategory
    detailed_description: str  # More detailed explanation
    suggested_action: str  # Specific, actionable recommendation
    actionability_score: float  # 0.0 to 1.0 - can user act on this?
    impact_score: float  # 0.0 to 1.0 - potential improvement impact
    confidence_score: float  # 0.0 to 1.0 - statistical confidence
    significance_score: float  # 0.0 to 1.0 - overall significance
    recency_score: float  # 0.0 to 1.0 - how recent is the data
    novelty_score: float  # 0.0 to 1.0 - is this a new insight or repeated
    supporting_evidence: List[str]  # Data points, patterns, correlations
    source_patterns: List[str] = field(default_factory=list)  # IDs/descriptions of source patterns
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate scores."""
        for score_name, score_value in [
            ("actionability_score", self.actionability_score),
            ("impact_score", self.impact_score),
            ("confidence_score", self.confidence_score),
            ("significance_score", self.significance_score),
            ("recency_score", self.recency_score),
            ("novelty_score", self.novelty_score),
        ]:
            if not 0.0 <= score_value <= 1.0:
                raise ValueError(f"{score_name} must be between 0.0 and 1.0")

    def get_overall_score(self) -> float:
        """Calculate overall insight score based on all factors.

        Returns:
            float: Weighted overall score between 0.0 and 1.0
        """
        # Weighted average of all scores
        weights = {
            "significance": 0.25,
            "actionability": 0.20,
            "impact": 0.20,
            "confidence": 0.15,
            "recency": 0.10,
            "novelty": 0.10,
        }

        overall = (
            self.significance_score * weights["significance"] +
            self.actionability_score * weights["actionability"] +
            self.impact_score * weights["impact"] +
            self.confidence_score * weights["confidence"] +
            self.recency_score * weights["recency"] +
            self.novelty_score * weights["novelty"]
        )

        return overall

    def format_for_display(self, include_details: bool = True) -> str:
        """Format insight for display in weekly review or CLI.

        Args:
            include_details: Whether to include detailed description and evidence

        Returns:
            str: Formatted insight string
        """
        lines = [
            f"💡 {self.summary}",
            f"   Action: {self.suggested_action}",
            f"   Confidence: {self.confidence_score:.0%} | Impact: {self.impact_score:.0%}",
        ]

        if include_details:
            lines.append(f"\n   {self.detailed_description}")
            if self.supporting_evidence:
                lines.append("\n   Evidence:")
                for evidence in self.supporting_evidence[:3]:  # Top 3 pieces of evidence
                    lines.append(f"   • {evidence}")

        return "\n".join(lines)
