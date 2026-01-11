"""Pattern Recognition Engine

Analyze historical data to identify patterns in productivity, energy, habits, and behavior.
"""

from .models import (
    TaskCompletionPattern,
    HealthCorrelation,
    HabitStreak,
    Trend,
    Insight,
)

from .time_series import (
    AggregationPeriod,
    DataPoint,
    TimeSeriesData,
    AggregatedData,
    TaskCompletionRecord,
    HealthMetricRecord,
    ProductivityRecord,
    TimeSeriesAggregator,
    create_time_series_from_dict,
    merge_time_series,
)

__all__ = [
    # Models
    "TaskCompletionPattern",
    "HealthCorrelation",
    "HabitStreak",
    "Trend",
    "Insight",
    # Time Series
    "AggregationPeriod",
    "DataPoint",
    "TimeSeriesData",
    "AggregatedData",
    "TaskCompletionRecord",
    "HealthMetricRecord",
    "ProductivityRecord",
    "TimeSeriesAggregator",
    "create_time_series_from_dict",
    "merge_time_series",
]
