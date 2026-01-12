"""Unit tests for pattern analyzers.

Tests all four pattern analyzers with mock data and edge cases:
- task_patterns: hourly, daily, task type patterns, completion rates
- health_correlation: sleep/tasks, readiness/productivity, deep sleep/focus, sleep timing/energy
- habit_streaks: recurring habits, streak analysis, break detection
- trend_detector: trend detection, momentum calculation

Edge cases tested:
- Empty data
- Single data point
- Insufficient data
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from Tools.pattern_recognition.analyzers.task_patterns import (
    analyze_hourly_patterns,
    analyze_daily_patterns,
    analyze_task_type_patterns,
    calculate_daily_completion_rate,
    get_all_task_patterns,
)
from Tools.pattern_recognition.analyzers.health_correlation import (
    correlate_sleep_duration_with_tasks,
    correlate_readiness_with_productivity,
    correlate_deep_sleep_with_focus,
    correlate_sleep_timing_with_morning_energy,
    get_all_health_correlations,
)
from Tools.pattern_recognition.analyzers.habit_streaks import (
    identify_recurring_habits,
    analyze_habit_streak,
    analyze_streak_breaks,
    get_all_habit_streaks,
)
from Tools.pattern_recognition.analyzers.trend_detector import (
    detect_trend,
    analyze_task_completion_trend,
    analyze_health_metric_trend,
    analyze_productivity_trend,
    calculate_momentum,
    get_all_trends,
)
from Tools.pattern_recognition.models import (
    TaskCompletionPattern,
    HealthCorrelation,
    HabitStreak,
    Trend,
    PatternType,
    TrendDirection,
)
from Tools.pattern_recognition.time_series import (
    TaskCompletionRecord,
    HealthMetricRecord,
    ProductivityRecord,
    TimeSeriesData,
    DataPoint,
)


# ============================================================================
# Mock Data Generators
# ============================================================================

def create_mock_task_records(
    num_days: int = 30,
    peak_hours: List[int] = None,
    high_day: int = None
) -> List[TaskCompletionRecord]:
    """Create mock task completion records.

    Args:
        num_days: Number of days to generate
        peak_hours: Hours with higher completion (e.g., [9, 10, 11])
        high_day: Day of week with higher completion (0=Monday)

    Returns:
        List of TaskCompletionRecord objects
    """
    records = []
    base_date = datetime.now() - timedelta(days=num_days)

    for i in range(num_days):
        current_date = base_date + timedelta(days=i)
        day_of_week = current_date.weekday()

        # Base tasks per day
        base_tasks = 5

        # Boost on high_day
        if high_day is not None and day_of_week == high_day:
            base_tasks = 8

        # Create hourly distribution
        hourly_completions = {}
        for hour in range(24):
            if peak_hours and hour in peak_hours:
                hourly_completions[hour] = 3  # Peak hours
            elif 9 <= hour <= 17:
                hourly_completions[hour] = 1  # Working hours
            else:
                hourly_completions[hour] = 0  # Off hours

        # Task types
        task_types = {
            "deep_work": 2 if peak_hours and any(9 <= h <= 11 for h in peak_hours) else 1,
            "meetings": 1,
            "admin": 1,
        }

        record = TaskCompletionRecord(
            date=current_date,
            tasks_completed=base_tasks,
            hourly_completions=hourly_completions,
            task_types=task_types,
        )
        records.append(record)

    return records


def create_mock_health_records(
    num_days: int = 30,
    sleep_duration_avg: float = 7.5,
    sleep_duration_std: float = 1.0,
    readiness_avg: float = 75.0,
) -> List[HealthMetricRecord]:
    """Create mock health metric records.

    Args:
        num_days: Number of days to generate
        sleep_duration_avg: Average sleep duration in hours
        sleep_duration_std: Standard deviation of sleep duration
        readiness_avg: Average readiness score

    Returns:
        List of HealthMetricRecord objects
    """
    records = []
    base_date = datetime.now() - timedelta(days=num_days)

    import random
    random.seed(42)  # Reproducible tests

    for i in range(num_days):
        current_date = base_date + timedelta(days=i)

        # Generate correlated sleep metrics
        sleep_duration = max(4.0, min(10.0, random.gauss(sleep_duration_avg, sleep_duration_std)))

        # Deep sleep correlates with total sleep
        deep_sleep_minutes = int(sleep_duration * 60 * 0.20)  # 20% of total sleep

        # Readiness correlates with sleep quality
        readiness = min(100, max(50, readiness_avg + (sleep_duration - 7.5) * 5))

        # Sleep timing (bedtime hour)
        bedtime_hour = 22.5 + random.gauss(0, 1.0)  # Around 10:30 PM

        record = HealthMetricRecord(
            date=current_date,
            sleep_duration=sleep_duration,
            deep_sleep_minutes=deep_sleep_minutes,
            readiness_score=int(readiness),
            hrv=60,
            resting_heart_rate=55,
            steps=8000,
            active_calories=400,
            metadata={"bedtime_hour": bedtime_hour}
        )
        records.append(record)

    return records


def create_mock_productivity_records(
    num_days: int = 30,
    trending_up: bool = False,
    trending_down: bool = False,
) -> List[ProductivityRecord]:
    """Create mock productivity records.

    Args:
        num_days: Number of days to generate
        trending_up: If True, show improving trend
        trending_down: If True, show declining trend

    Returns:
        List of ProductivityRecord objects
    """
    records = []
    base_date = datetime.now() - timedelta(days=num_days)

    for i in range(num_days):
        current_date = base_date + timedelta(days=i)

        # Base productivity score
        base_score = 7.0

        # Add trend
        if trending_up:
            trend_adjustment = (i / num_days) * 3.0  # Increase by 3 points
        elif trending_down:
            trend_adjustment = -(i / num_days) * 3.0  # Decrease by 3 points
        else:
            trend_adjustment = 0

        productivity_score = base_score + trend_adjustment

        record = ProductivityRecord(
            date=current_date,
            tasks_completed=int(productivity_score),
            focus_score=productivity_score,
            energy_level=productivity_score,
            productivity_score=productivity_score,
        )
        records.append(record)

    return records


# ============================================================================
# Task Patterns Analyzer Tests
# ============================================================================

class TestTaskPatternsAnalyzer:
    """Tests for task_patterns analyzer."""

    def test_analyze_hourly_patterns_with_peak_hours(self):
        """Test hourly pattern detection with clear peak hours."""
        records = create_mock_task_records(num_days=30, peak_hours=[9, 10, 11])
        patterns = analyze_hourly_patterns(records, min_samples=5, min_confidence=0.5)

        assert len(patterns) > 0
        assert all(isinstance(p, TaskCompletionPattern) for p in patterns)
        assert any("9" in p.time_period or "10" in p.time_period or "11" in p.time_period
                  for p in patterns)

    def test_analyze_hourly_patterns_empty_data(self):
        """Test hourly pattern detection with empty data."""
        patterns = analyze_hourly_patterns([])
        assert patterns == []

    def test_analyze_hourly_patterns_single_record(self):
        """Test hourly pattern detection with single data point."""
        records = create_mock_task_records(num_days=1)
        patterns = analyze_hourly_patterns(records, min_samples=5)

        # Should return empty or very low confidence
        assert len(patterns) == 0 or all(p.confidence_score < 0.7 for p in patterns)

    def test_analyze_hourly_patterns_insufficient_samples(self):
        """Test hourly pattern detection with insufficient samples."""
        records = create_mock_task_records(num_days=3)
        patterns = analyze_hourly_patterns(records, min_samples=10)

        # Should return empty due to insufficient samples
        assert patterns == []

    def test_analyze_daily_patterns_with_high_day(self):
        """Test daily pattern detection with one high-productivity day."""
        # Monday (0) is high productivity day
        records = create_mock_task_records(num_days=30, high_day=0)
        patterns = analyze_daily_patterns(records, min_samples=3, min_confidence=0.5)

        if patterns:
            assert all(isinstance(p, TaskCompletionPattern) for p in patterns)
            # Should detect Monday pattern
            assert any("Monday" in p.time_period or p.time_period == "0" for p in patterns)

    def test_analyze_daily_patterns_empty_data(self):
        """Test daily pattern detection with empty data."""
        patterns = analyze_daily_patterns([])
        assert patterns == []

    def test_analyze_task_type_patterns(self):
        """Test task type pattern detection."""
        records = create_mock_task_records(num_days=30, peak_hours=[9, 10, 11])
        patterns = analyze_task_type_patterns(records, min_samples=5, min_confidence=0.5)

        if patterns:
            assert all(isinstance(p, TaskCompletionPattern) for p in patterns)
            # Should detect deep_work pattern in morning hours
            assert any("deep_work" in p.description.lower() for p in patterns)

    def test_analyze_task_type_patterns_empty_data(self):
        """Test task type pattern detection with empty data."""
        patterns = analyze_task_type_patterns([])
        assert patterns == []

    def test_calculate_daily_completion_rate(self):
        """Test daily completion rate calculation."""
        records = create_mock_task_records(num_days=30)
        pattern = calculate_daily_completion_rate(records, min_confidence=0.5)

        if pattern:
            assert isinstance(pattern, TaskCompletionPattern)
            assert pattern.completion_rate > 0
            assert 0.0 <= pattern.confidence_score <= 1.0

    def test_calculate_daily_completion_rate_empty_data(self):
        """Test daily completion rate with empty data."""
        pattern = calculate_daily_completion_rate([])
        assert pattern is None

    def test_calculate_daily_completion_rate_single_record(self):
        """Test daily completion rate with single data point."""
        records = create_mock_task_records(num_days=1)
        pattern = calculate_daily_completion_rate(records, min_samples=5)

        # Should return None due to insufficient samples
        assert pattern is None

    def test_get_all_task_patterns(self):
        """Test convenience function to get all task patterns."""
        records = create_mock_task_records(num_days=30, peak_hours=[9, 10])
        all_patterns = get_all_task_patterns(records)

        assert isinstance(all_patterns, dict)
        assert "hourly" in all_patterns
        assert "daily" in all_patterns
        assert "task_type" in all_patterns
        assert "completion_rate" in all_patterns


# ============================================================================
# Health Correlation Analyzer Tests
# ============================================================================

class TestHealthCorrelationAnalyzer:
    """Tests for health_correlation analyzer."""

    def test_correlate_sleep_duration_with_tasks(self):
        """Test sleep duration vs tasks correlation."""
        health_records = create_mock_health_records(num_days=30, sleep_duration_avg=7.5)
        task_records = create_mock_task_records(num_days=30)

        correlation = correlate_sleep_duration_with_tasks(
            health_records, task_records, min_samples=7, min_confidence=0.5
        )

        if correlation:
            assert isinstance(correlation, HealthCorrelation)
            assert correlation.health_metric == "sleep_duration"
            assert correlation.productivity_metric == "tasks_completed"
            assert -1.0 <= correlation.correlation_strength <= 1.0
            assert 0.0 <= correlation.confidence_score <= 1.0

    def test_correlate_sleep_duration_empty_data(self):
        """Test sleep correlation with empty data."""
        correlation = correlate_sleep_duration_with_tasks([], [], min_samples=7)
        assert correlation is None

    def test_correlate_sleep_duration_insufficient_data(self):
        """Test sleep correlation with insufficient data."""
        health_records = create_mock_health_records(num_days=3)
        task_records = create_mock_task_records(num_days=3)

        correlation = correlate_sleep_duration_with_tasks(
            health_records, task_records, min_samples=10
        )
        assert correlation is None

    def test_correlate_readiness_with_productivity(self):
        """Test readiness score vs productivity correlation."""
        health_records = create_mock_health_records(num_days=30)
        productivity_records = create_mock_productivity_records(num_days=30)

        correlation = correlate_readiness_with_productivity(
            health_records, productivity_records, min_samples=7, min_confidence=0.5
        )

        if correlation:
            assert isinstance(correlation, HealthCorrelation)
            assert correlation.health_metric == "readiness_score"
            assert correlation.productivity_metric == "productivity_score"
            assert -1.0 <= correlation.correlation_strength <= 1.0

    def test_correlate_readiness_empty_data(self):
        """Test readiness correlation with empty data."""
        correlation = correlate_readiness_with_productivity([], [])
        assert correlation is None

    def test_correlate_deep_sleep_with_focus(self):
        """Test deep sleep vs focus correlation."""
        health_records = create_mock_health_records(num_days=30)
        productivity_records = create_mock_productivity_records(num_days=30)

        correlation = correlate_deep_sleep_with_focus(
            health_records, productivity_records, min_samples=7, min_confidence=0.5
        )

        if correlation:
            assert isinstance(correlation, HealthCorrelation)
            assert "deep_sleep" in correlation.health_metric
            assert "focus" in correlation.productivity_metric.lower()

    def test_correlate_deep_sleep_empty_data(self):
        """Test deep sleep correlation with empty data."""
        correlation = correlate_deep_sleep_with_focus([], [])
        assert correlation is None

    def test_correlate_sleep_timing_with_morning_energy(self):
        """Test sleep timing vs morning energy correlation."""
        health_records = create_mock_health_records(num_days=30)
        productivity_records = create_mock_productivity_records(num_days=30)

        correlation = correlate_sleep_timing_with_morning_energy(
            health_records, productivity_records, min_samples=7, min_confidence=0.5
        )

        if correlation:
            assert isinstance(correlation, HealthCorrelation)
            assert "timing" in correlation.health_metric.lower() or "bedtime" in correlation.health_metric.lower()

    def test_correlate_sleep_timing_empty_data(self):
        """Test sleep timing correlation with empty data."""
        correlation = correlate_sleep_timing_with_morning_energy([], [])
        assert correlation is None

    def test_get_all_health_correlations(self):
        """Test convenience function to get all health correlations."""
        health_records = create_mock_health_records(num_days=30)
        task_records = create_mock_task_records(num_days=30)
        productivity_records = create_mock_productivity_records(num_days=30)

        all_correlations = get_all_health_correlations(
            health_records, task_records, productivity_records
        )

        assert isinstance(all_correlations, dict)
        assert "sleep_duration" in all_correlations
        assert "readiness" in all_correlations
        assert "deep_sleep" in all_correlations
        assert "sleep_timing" in all_correlations


# ============================================================================
# Habit Streaks Analyzer Tests
# ============================================================================

class TestHabitStreaksAnalyzer:
    """Tests for habit_streaks analyzer."""

    def test_identify_recurring_habits(self):
        """Test identification of recurring habits."""
        records = create_mock_task_records(num_days=30)
        habits = identify_recurring_habits(records, min_occurrences=5, min_days_span=7)

        assert isinstance(habits, list)
        if habits:
            # Should find habits like 'deep_work', 'meetings', 'admin'
            assert all(isinstance(h, str) for h in habits)
            assert any(habit in ["deep_work", "meetings", "admin"] for habit in habits)

    def test_identify_recurring_habits_empty_data(self):
        """Test habit identification with empty data."""
        habits = identify_recurring_habits([])
        assert habits == []

    def test_identify_recurring_habits_insufficient_span(self):
        """Test habit identification with insufficient time span."""
        records = create_mock_task_records(num_days=3)
        habits = identify_recurring_habits(records, min_occurrences=5, min_days_span=30)

        # Should return empty due to insufficient span
        assert habits == []

    def test_analyze_habit_streak(self):
        """Test habit streak analysis."""
        records = create_mock_task_records(num_days=30)

        # Analyze streak for a known habit
        streak = analyze_habit_streak(
            "deep_work", records, expected_frequency_days=1, min_confidence=0.5
        )

        if streak:
            assert isinstance(streak, HabitStreak)
            assert streak.habit_name == "deep_work"
            assert streak.streak_length >= 0
            assert 0.0 <= streak.consistency_score <= 1.0
            assert 0.0 <= streak.confidence_score <= 1.0

    def test_analyze_habit_streak_empty_data(self):
        """Test habit streak analysis with empty data."""
        streak = analyze_habit_streak("deep_work", [])
        assert streak is None

    def test_analyze_habit_streak_single_record(self):
        """Test habit streak analysis with single data point."""
        records = create_mock_task_records(num_days=1)
        streak = analyze_habit_streak("deep_work", records, min_confidence=0.7)

        # Should return None or very low confidence
        assert streak is None or streak.confidence_score < 0.7

    def test_analyze_habit_streak_nonexistent_habit(self):
        """Test habit streak analysis for non-existent habit."""
        records = create_mock_task_records(num_days=30)
        streak = analyze_habit_streak("nonexistent_habit", records)

        assert streak is None

    def test_analyze_streak_breaks(self):
        """Test streak break analysis."""
        records = create_mock_task_records(num_days=30)

        breaks = analyze_streak_breaks(
            "deep_work", records, min_samples=5
        )

        # May or may not find breaks depending on the mock data
        assert isinstance(breaks, list)
        if breaks:
            assert all(isinstance(b, dict) for b in breaks)

    def test_analyze_streak_breaks_empty_data(self):
        """Test streak break analysis with empty data."""
        breaks = analyze_streak_breaks("deep_work", [])
        assert breaks == []

    def test_get_all_habit_streaks(self):
        """Test convenience function to get all habit streaks."""
        records = create_mock_task_records(num_days=30)

        all_streaks = get_all_habit_streaks(records)

        assert isinstance(all_streaks, dict)
        if all_streaks:
            assert "habits" in all_streaks
            assert "streaks" in all_streaks


# ============================================================================
# Trend Detector Analyzer Tests
# ============================================================================

class TestTrendDetectorAnalyzer:
    """Tests for trend_detector analyzer."""

    def test_detect_trend_improving(self):
        """Test trend detection with improving trend."""
        # Create time series with improving trend
        time_series = TimeSeriesData(metric_name="tasks_per_day", unit="tasks")
        base_date = datetime.now() - timedelta(days=30)

        for i in range(30):
            value = 5.0 + (i / 30) * 3.0  # Increase from 5 to 8
            time_series.add_point(base_date + timedelta(days=i), value)

        trend = detect_trend(time_series, window_days=30, min_samples=7, min_confidence=0.5)

        if trend:
            assert isinstance(trend, Trend)
            assert trend.trend_direction in [TrendDirection.IMPROVING, TrendDirection.VOLATILE]
            assert 0.0 <= trend.confidence_score <= 1.0
            assert 0.0 <= trend.trend_strength <= 1.0

    def test_detect_trend_declining(self):
        """Test trend detection with declining trend."""
        # Create time series with declining trend
        time_series = TimeSeriesData(metric_name="productivity", unit="score")
        base_date = datetime.now() - timedelta(days=30)

        for i in range(30):
            value = 8.0 - (i / 30) * 3.0  # Decrease from 8 to 5
            time_series.add_point(base_date + timedelta(days=i), value)

        trend = detect_trend(time_series, window_days=30, min_samples=7, min_confidence=0.5)

        if trend:
            assert isinstance(trend, Trend)
            assert trend.trend_direction in [TrendDirection.DECLINING, TrendDirection.VOLATILE]

    def test_detect_trend_plateau(self):
        """Test trend detection with plateau (stable) trend."""
        # Create time series with stable values
        time_series = TimeSeriesData(metric_name="sleep_hours", unit="hours")
        base_date = datetime.now() - timedelta(days=30)

        for i in range(30):
            value = 7.5  # Constant value
            time_series.add_point(base_date + timedelta(days=i), value)

        trend = detect_trend(time_series, window_days=30, min_samples=7, min_confidence=0.5)

        if trend:
            assert isinstance(trend, Trend)
            # Should be plateau or low confidence
            assert trend.trend_direction == TrendDirection.PLATEAU or trend.confidence_score < 0.7

    def test_detect_trend_empty_data(self):
        """Test trend detection with empty data."""
        time_series = TimeSeriesData(metric_name="test", unit="unit")
        trend = detect_trend(time_series)

        assert trend is None

    def test_detect_trend_single_data_point(self):
        """Test trend detection with single data point."""
        time_series = TimeSeriesData(metric_name="test", unit="unit")
        time_series.add_point(datetime.now(), 10.0)

        trend = detect_trend(time_series, min_samples=7)
        assert trend is None

    def test_detect_trend_insufficient_data(self):
        """Test trend detection with insufficient data."""
        time_series = TimeSeriesData(metric_name="test", unit="unit")
        base_date = datetime.now()

        for i in range(3):
            time_series.add_point(base_date + timedelta(days=i), float(i))

        trend = detect_trend(time_series, min_samples=10)
        assert trend is None

    def test_analyze_task_completion_trend(self):
        """Test task completion trend analysis."""
        records = create_mock_productivity_records(num_days=30, trending_up=True)

        trend = analyze_task_completion_trend(records, window_days=30, min_confidence=0.5)

        if trend:
            assert isinstance(trend, Trend)
            assert "task" in trend.metric_name.lower()
            assert trend.trend_direction in [TrendDirection.IMPROVING, TrendDirection.VOLATILE]

    def test_analyze_task_completion_trend_empty_data(self):
        """Test task completion trend with empty data."""
        trend = analyze_task_completion_trend([])
        assert trend is None

    def test_analyze_health_metric_trend(self):
        """Test health metric trend analysis."""
        records = create_mock_health_records(num_days=30)

        trend = analyze_health_metric_trend(
            records, metric="sleep_duration", window_days=30, min_confidence=0.5
        )

        if trend:
            assert isinstance(trend, Trend)
            assert "sleep" in trend.metric_name.lower()

    def test_analyze_health_metric_trend_empty_data(self):
        """Test health metric trend with empty data."""
        trend = analyze_health_metric_trend([], metric="sleep_duration")
        assert trend is None

    def test_analyze_productivity_trend(self):
        """Test productivity trend analysis."""
        records = create_mock_productivity_records(num_days=30, trending_up=True)

        trend = analyze_productivity_trend(records, window_days=30, min_confidence=0.5)

        if trend:
            assert isinstance(trend, Trend)
            assert "productivity" in trend.metric_name.lower()

    def test_analyze_productivity_trend_empty_data(self):
        """Test productivity trend with empty data."""
        trend = analyze_productivity_trend([])
        assert trend is None

    def test_calculate_momentum(self):
        """Test momentum calculation."""
        records = create_mock_productivity_records(num_days=30, trending_up=True)

        momentum = calculate_momentum(records, window_days=7)

        if momentum:
            assert isinstance(momentum, dict)
            # Should contain momentum indicators

    def test_calculate_momentum_empty_data(self):
        """Test momentum calculation with empty data."""
        momentum = calculate_momentum([])

        # Should handle empty data gracefully
        assert momentum is None or momentum == {}

    def test_calculate_momentum_insufficient_data(self):
        """Test momentum calculation with insufficient data."""
        records = create_mock_productivity_records(num_days=3)

        momentum = calculate_momentum(records, window_days=7)

        # Should handle insufficient data
        assert momentum is None or momentum == {}

    def test_get_all_trends(self):
        """Test convenience function to get all trends."""
        task_records = create_mock_task_records(num_days=30)
        health_records = create_mock_health_records(num_days=30)
        productivity_records = create_mock_productivity_records(num_days=30)

        all_trends = get_all_trends(task_records, health_records, productivity_records)

        assert isinstance(all_trends, dict)
        # May contain various trend categories


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases across all analyzers."""

    def test_all_analyzers_handle_empty_data(self):
        """Test that all analyzers handle empty data gracefully."""
        # Task patterns
        assert analyze_hourly_patterns([]) == []
        assert analyze_daily_patterns([]) == []
        assert analyze_task_type_patterns([]) == []
        assert calculate_daily_completion_rate([]) is None

        # Health correlations
        assert correlate_sleep_duration_with_tasks([], []) is None
        assert correlate_readiness_with_productivity([], []) is None
        assert correlate_deep_sleep_with_focus([], []) is None
        assert correlate_sleep_timing_with_morning_energy([], []) is None

        # Habit streaks
        assert identify_recurring_habits([]) == []
        assert analyze_habit_streak("test", []) is None
        assert analyze_streak_breaks("test", []) == []

        # Trends
        empty_ts = TimeSeriesData(metric_name="test", unit="unit")
        assert detect_trend(empty_ts) is None
        assert analyze_task_completion_trend([]) is None
        assert analyze_health_metric_trend([], "sleep_duration") is None
        assert analyze_productivity_trend([]) is None

    def test_all_analyzers_handle_single_data_point(self):
        """Test that all analyzers handle single data point."""
        task_records = create_mock_task_records(num_days=1)
        health_records = create_mock_health_records(num_days=1)
        productivity_records = create_mock_productivity_records(num_days=1)

        # Should return empty or None with strict requirements
        patterns = analyze_hourly_patterns(task_records, min_samples=5)
        assert patterns == []

        correlation = correlate_sleep_duration_with_tasks(
            health_records, task_records, min_samples=7
        )
        assert correlation is None

        habits = identify_recurring_habits(task_records, min_occurrences=5)
        assert habits == []

        # Time series with single point
        ts = TimeSeriesData(metric_name="test", unit="unit")
        ts.add_point(datetime.now(), 5.0)
        trend = detect_trend(ts, min_samples=7)
        assert trend is None

    def test_confidence_scores_within_bounds(self):
        """Test that all confidence scores are within 0.0-1.0 range."""
        records = create_mock_task_records(num_days=30, peak_hours=[9, 10])

        # Task patterns
        patterns = analyze_hourly_patterns(records, min_confidence=0.0)
        for pattern in patterns:
            assert 0.0 <= pattern.confidence_score <= 1.0

        # Health correlations
        health_records = create_mock_health_records(num_days=30)
        correlation = correlate_sleep_duration_with_tasks(
            health_records, records, min_confidence=0.0
        )
        if correlation:
            assert 0.0 <= correlation.confidence_score <= 1.0

        # Habit streaks
        streak = analyze_habit_streak("deep_work", records, min_confidence=0.0)
        if streak:
            assert 0.0 <= streak.confidence_score <= 1.0

        # Trends
        productivity_records = create_mock_productivity_records(num_days=30)
        trend = analyze_productivity_trend(productivity_records, min_confidence=0.0)
        if trend:
            assert 0.0 <= trend.confidence_score <= 1.0

    def test_date_ranges_are_valid(self):
        """Test that all date ranges are valid (start <= end)."""
        records = create_mock_task_records(num_days=30, peak_hours=[9, 10])
        health_records = create_mock_health_records(num_days=30)

        # Task patterns
        patterns = analyze_hourly_patterns(records)
        for pattern in patterns:
            assert pattern.date_range_start <= pattern.date_range_end

        # Health correlations
        correlation = correlate_sleep_duration_with_tasks(health_records, records, min_confidence=0.0)
        if correlation and correlation.date_range_start:
            assert correlation.date_range_start <= correlation.date_range_end

        # Habit streaks
        streak = analyze_habit_streak("deep_work", records, min_confidence=0.0)
        if streak:
            assert streak.date_range_start <= streak.date_range_end

        # Trends
        productivity_records = create_mock_productivity_records(num_days=30)
        trend = analyze_productivity_trend(productivity_records, min_confidence=0.0)
        if trend and trend.date_range_start:
            assert trend.date_range_start <= trend.date_range_end


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
