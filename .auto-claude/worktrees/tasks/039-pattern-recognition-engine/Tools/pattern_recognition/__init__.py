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

from .analyzers.task_patterns import (
    analyze_hourly_patterns,
    analyze_daily_patterns,
    analyze_task_type_patterns,
    calculate_daily_completion_rate,
    get_all_task_patterns,
)

from .insight_generator import (
    generate_insight_from_task_pattern,
    generate_insight_from_health_correlation,
    generate_insight_from_habit_streak,
    generate_insight_from_trend,
    generate_insights_from_all_patterns,
    rank_insights,
    filter_insights_by_confidence,
    filter_insights_by_category,
    select_top_insights,
    calculate_recency_score,
    calculate_significance_score,
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
    # Analyzers
    "analyze_hourly_patterns",
    "analyze_daily_patterns",
    "analyze_task_type_patterns",
    "calculate_daily_completion_rate",
    "get_all_task_patterns",
    # Insight Generation
    "generate_insight_from_task_pattern",
    "generate_insight_from_health_correlation",
    "generate_insight_from_habit_streak",
    "generate_insight_from_trend",
    "generate_insights_from_all_patterns",
    "rank_insights",
    "filter_insights_by_confidence",
    "filter_insights_by_category",
    "select_top_insights",
    "calculate_recency_score",
    "calculate_significance_score",
]
