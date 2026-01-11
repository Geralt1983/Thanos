"""Pattern analyzers for task completion, health correlations, habits, and trends."""

from .task_patterns import (
    analyze_hourly_patterns,
    analyze_daily_patterns,
    analyze_task_type_patterns,
    calculate_daily_completion_rate,
    get_all_task_patterns,
)
from .health_correlation import (
    correlate_sleep_duration_with_tasks,
    correlate_readiness_with_productivity,
    correlate_deep_sleep_with_focus,
    correlate_sleep_timing_with_morning_energy,
    get_all_health_correlations,
)
from .habit_streaks import (
    identify_recurring_habits,
    analyze_habit_streak,
    analyze_streak_breaks,
    get_all_habit_streaks,
)
from .trend_detector import (
    detect_trend,
    analyze_task_completion_trend,
    analyze_health_metric_trend,
    analyze_productivity_trend,
    calculate_momentum,
    get_all_trends,
)

__all__ = [
    "analyze_hourly_patterns",
    "analyze_daily_patterns",
    "analyze_task_type_patterns",
    "calculate_daily_completion_rate",
    "get_all_task_patterns",
    "correlate_sleep_duration_with_tasks",
    "correlate_readiness_with_productivity",
    "correlate_deep_sleep_with_focus",
    "correlate_sleep_timing_with_morning_energy",
    "get_all_health_correlations",
    "identify_recurring_habits",
    "analyze_habit_streak",
    "analyze_streak_breaks",
    "get_all_habit_streaks",
    "detect_trend",
    "analyze_task_completion_trend",
    "analyze_health_metric_trend",
    "analyze_productivity_trend",
    "calculate_momentum",
    "get_all_trends",
]
