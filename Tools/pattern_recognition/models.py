"""
Pattern recognition data models.

Defines dataclasses for representing detected patterns, correlations,
streaks, trends, and insights from historical data analysis.

These models are used by pattern analyzers to structure their findings
and by the insight generator to create actionable recommendations.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class TaskCompletionPattern:
    """
    Pattern detected in task completion behavior.

    Examples:
        - "Most productive between 9-11am"
        - "Mondays have lowest completion rate"
        - "Deep work tasks completed best in morning"
    """
    pattern_type: str  # e.g., "time_of_day", "day_of_week", "task_type_timing"
    description: str  # Human-readable pattern description
    confidence_score: float  # 0.0 to 1.0 indicating statistical confidence
    start_date: date
    end_date: date
    evidence: Dict[str, Any] = field(default_factory=dict)  # Supporting data points
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional context


@dataclass
class HealthCorrelation:
    """
    Correlation between health metrics and productivity/behavior.

    Examples:
        - "7+ hours sleep → 40% more tasks completed"
        - "Readiness score >85 → higher focus scores"
        - "Deep sleep >90min → better morning energy"
    """
    health_metric: str  # e.g., "sleep_duration", "readiness_score", "deep_sleep"
    productivity_metric: str  # e.g., "tasks_completed", "focus_score", "energy_level"
    correlation_coefficient: float  # -1.0 to 1.0 (Pearson correlation)
    description: str  # Human-readable correlation description
    confidence_score: float  # 0.0 to 1.0 indicating statistical significance
    start_date: date
    end_date: date
    sample_size: int  # Number of data points used for correlation
    evidence: Dict[str, Any] = field(default_factory=dict)  # Supporting data
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreakBreak:
    """Record of when and why a habit streak was broken."""
    break_date: date
    previous_streak_length: int  # Days before break
    reason: Optional[str] = None  # Root cause if identified
    context: Dict[str, Any] = field(default_factory=dict)  # Environmental factors


@dataclass
class HabitStreak:
    """
    Information about habit streaks and consistency.

    Examples:
        - "Daily review: 23-day streak (best: 45 days)"
        - "Exercise: 87% consistency over 30 days"
    """
    habit_name: str
    current_streak: int  # Current consecutive days
    best_streak: int  # Longest streak achieved
    consistency_score: float  # 0.0 to 1.0 (percentage of days completed)
    start_date: date
    end_date: date
    total_completions: int  # Number of times completed in date range
    total_opportunities: int  # Number of days in date range
    streak_breaks: List[StreakBreak] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trend:
    """
    Detected trend in a metric over time.

    Examples:
        - "Task completion rate increasing 15% over 30 days"
        - "Readiness scores declining -8% this week"
        - "Productivity plateau for past 14 days"
    """
    metric_name: str  # e.g., "tasks_per_day", "readiness_score", "sleep_duration"
    trend_type: str  # "improving", "declining", "plateau", "volatile"
    direction: str  # "up", "down", "stable"
    rate_of_change: float  # Percentage change (e.g., 0.15 for +15%)
    confidence_score: float  # 0.0 to 1.0 indicating statistical confidence
    start_date: date
    end_date: date
    start_value: float  # Metric value at start of period
    end_value: float  # Metric value at end of period
    time_window: str  # e.g., "7-day", "30-day", "90-day"
    evidence: Dict[str, Any] = field(default_factory=dict)  # Data points, slope, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Insight:
    """
    Actionable insight generated from detected patterns.

    Insights are ranked by overall score (combination of significance,
    actionability, and impact) and presented to user in weekly reviews
    or pattern analysis reports.
    """
    title: str  # Concise summary (1 sentence)
    description: str  # Detailed explanation (2-3 sentences)
    category: str  # "task_completion", "health_correlation", "habit", "trend", "behavioral"

    # Scoring dimensions (0.0 to 1.0)
    significance_score: float  # Statistical confidence/strength
    actionability_score: float  # Can user change behavior based on this?
    impact_score: float  # Potential improvement magnitude
    recency_score: float  # How recent is the pattern? (recent = higher)
    novelty_score: float  # Is this a new insight? (avoid repetition)

    overall_score: float  # Weighted combination of above scores

    recommended_action: str  # Specific, actionable recommendation

    start_date: date
    end_date: date

    # References to supporting patterns
    supporting_patterns: List[str] = field(default_factory=list)  # IDs or descriptions

    evidence: Dict[str, Any] = field(default_factory=dict)  # Data supporting insight
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Tracking
    presented_at: Optional[date] = None  # When was this shown to user?
    user_feedback: Optional[str] = None  # User's response (if collected)
