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

from .weekly_review_formatter import (
    format_insight_for_weekly_review,
    format_insights_for_weekly_review,
    format_insight_compact,
    format_insight_detailed,
    format_insight_markdown,
    generate_weekly_insights_summary,
    format_insights_for_cli_display,
    export_insights_to_markdown_file,
)

from .pattern_storage import (
    store_task_pattern,
    store_health_correlation,
    store_habit_streak,
    store_trend,
    store_insight,
    link_patterns,
    track_pattern_evolution,
    store_all_patterns,
)

from .pattern_queries import (
    get_patterns_by_category,
    get_recent_insights,
    get_patterns_related_to,
    get_pattern_context_for_persona,
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
    # Weekly Review Formatting
    "format_insight_for_weekly_review",
    "format_insights_for_weekly_review",
    "format_insight_compact",
    "format_insight_detailed",
    "format_insight_markdown",
    "generate_weekly_insights_summary",
    "format_insights_for_cli_display",
    "export_insights_to_markdown_file",
    # Pattern Storage
    "store_task_pattern",
    "store_health_correlation",
    "store_habit_streak",
    "store_trend",
    "store_insight",
    "link_patterns",
    "track_pattern_evolution",
    "store_all_patterns",
    # Pattern Queries
    "get_patterns_by_category",
    "get_recent_insights",
    "get_patterns_related_to",
    "get_pattern_context_for_persona",
]
