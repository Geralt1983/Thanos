"""
Pattern recognition engine for Thanos.

Analyzes historical data to identify patterns in productivity, energy,
habits, and behavior. Detects correlations and surfaces actionable insights.
"""

from .data_aggregator import (
    DataAggregator,
    AggregatedData,
    TaskCompletionRecord,
    SessionRecord,
    HealthMetrics,
    CommitmentRecord,
)
from .models import (
    TaskCompletionPattern,
    HealthCorrelation,
    HabitStreak,
    StreakBreak,
    Trend,
    Insight,
)
from .time_series import (
    TimeSeriesBuilder,
    TimeSeries,
    TimeSeriesPoint,
    AggregationPeriod,
    build_time_series,
)
from .analyzers import TaskPatternAnalyzer

__all__ = [
    "DataAggregator",
    "AggregatedData",
    "TaskCompletionRecord",
    "SessionRecord",
    "HealthMetrics",
    "CommitmentRecord",
    "TaskCompletionPattern",
    "HealthCorrelation",
    "HabitStreak",
    "StreakBreak",
    "Trend",
    "Insight",
    "TimeSeriesBuilder",
    "TimeSeries",
    "TimeSeriesPoint",
    "AggregationPeriod",
    "build_time_series",
    "TaskPatternAnalyzer",
]
