"""Trend detection analyzer.

Detects improving trends, declining trends, plateau periods, and momentum indicators
in productivity, health, and behavioral metrics over time.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics

from ..models import Trend, TrendDirection
from ..time_series import (
    TaskCompletionRecord,
    HealthMetricRecord,
    ProductivityRecord,
    TimeSeriesData
)


def detect_trend(
    time_series: TimeSeriesData,
    window_days: int = 30,
    min_samples: int = 7,
    min_confidence: float = 0.6
) -> Optional[Trend]:
    """Detect trend in a time series.

    Analyzes a time series to determine if there's an improving, declining, or
    plateau trend. Uses linear regression slope and consistency analysis.

    Args:
        time_series: TimeSeriesData to analyze
        window_days: Number of days to analyze (default: 30)
        min_samples: Minimum number of data points required
        min_confidence: Minimum confidence score to return trend

    Returns:
        Trend object if significant trend detected, None otherwise

    Examples:
        "Tasks per day increasing (7.2 → 9.4 over 30 days)"
        "Sleep quality declining (avg 85 → 72 in readiness)"
        "Plateau: Productivity stable around 8.5 tasks/day"
    """
    if not time_series.data_points or len(time_series.data_points) < min_samples:
        return None

    # Sort by timestamp
    sorted_points = sorted(time_series.data_points, key=lambda p: p.timestamp)

    # Filter to window
    if window_days:
        cutoff_date = sorted_points[-1].timestamp - timedelta(days=window_days)
        sorted_points = [p for p in sorted_points if p.timestamp >= cutoff_date]

    if len(sorted_points) < min_samples:
        return None

    # Calculate trend metrics
    values = [p.value for p in sorted_points]
    start_value = statistics.mean(values[:len(values)//3])  # First third average
    end_value = statistics.mean(values[-len(values)//3:])  # Last third average

    # Calculate percentage change
    if start_value != 0:
        change_pct = ((end_value - start_value) / abs(start_value)) * 100
    else:
        change_pct = 0.0 if end_value == 0 else 100.0

    # Calculate linear regression slope
    slope = _calculate_linear_regression_slope(sorted_points)

    # Determine trend direction based on slope and change
    trend_direction = _determine_trend_direction(slope, change_pct)

    # Calculate trend strength (consistency of movement)
    trend_strength = _calculate_trend_strength(values, trend_direction)

    # Calculate momentum indicator
    momentum = _calculate_momentum_category(window_days)

    # Calculate confidence
    confidence = _calculate_confidence(
        sample_size=len(sorted_points),
        trend_strength=trend_strength,
        change_magnitude=abs(change_pct),
        min_samples=min_samples
    )

    if confidence < min_confidence:
        return None

    # Build description
    description = _build_trend_description(
        time_series.metric_name,
        trend_direction,
        start_value,
        end_value,
        change_pct,
        time_series.unit
    )

    # Get date range
    date_start = sorted_points[0].timestamp
    date_end = sorted_points[-1].timestamp

    # Build evidence
    evidence = [
        f"Start value: {start_value:.2f} {time_series.unit}",
        f"End value: {end_value:.2f} {time_series.unit}",
        f"Change: {change_pct:+.1f}%",
        f"Trend strength: {trend_strength:.2f}",
        f"Based on {len(sorted_points)} data points over {window_days} days"
    ]

    return Trend(
        metric_name=time_series.metric_name,
        trend_direction=trend_direction,
        trend_description=description,
        start_value=start_value,
        end_value=end_value,
        change_percentage=change_pct,
        trend_strength=trend_strength,
        momentum_indicator=momentum,
        confidence_score=confidence,
        sample_size=len(sorted_points),
        date_range_start=date_start,
        date_range_end=date_end,
        evidence=evidence,
        metadata={
            'slope': slope,
            'window_days': window_days,
            'unit': time_series.unit
        }
    )


def analyze_task_completion_trend(
    task_records: List[TaskCompletionRecord],
    window_days: int = 30,
    min_samples: int = 7,
    min_confidence: float = 0.6
) -> Optional[Trend]:
    """Analyze trend in task completion rate.

    Detects whether tasks per day are increasing, decreasing, or plateauing.

    Args:
        task_records: List of task completion records
        window_days: Number of days to analyze
        min_samples: Minimum number of samples required
        min_confidence: Minimum confidence score

    Returns:
        Trend object if significant trend detected, None otherwise

    Examples:
        "Tasks per day increasing (7.2 → 9.4 over 30 days)"
        "Task completion declining by 15% over the last month"
    """
    if not task_records or len(task_records) < min_samples:
        return None

    # Create time series from task records
    time_series = TimeSeriesData(
        metric_name="tasks_per_day",
        unit="tasks"
    )

    for record in task_records:
        time_series.add_point(
            timestamp=record.date,
            value=float(record.tasks_completed),
            metadata={'completion_rate': record.completion_rate}
        )

    return detect_trend(
        time_series=time_series,
        window_days=window_days,
        min_samples=min_samples,
        min_confidence=min_confidence
    )


def analyze_health_metric_trend(
    health_records: List[HealthMetricRecord],
    metric_name: str,
    window_days: int = 30,
    min_samples: int = 7,
    min_confidence: float = 0.6
) -> Optional[Trend]:
    """Analyze trend in a specific health metric.

    Detects whether health metrics like sleep duration, readiness score, or
    deep sleep are improving, declining, or stable.

    Args:
        health_records: List of health metric records
        metric_name: Name of metric to analyze (e.g., 'sleep_duration', 'readiness_score')
        window_days: Number of days to analyze
        min_samples: Minimum number of samples required
        min_confidence: Minimum confidence score

    Returns:
        Trend object if significant trend detected, None otherwise

    Examples:
        "Sleep quality improving (readiness 72 → 85 over 30 days)"
        "Deep sleep declining by 20% in the last 2 weeks"
    """
    if not health_records or len(health_records) < min_samples:
        return None

    # Extract metric values
    metric_getter = {
        'sleep_duration': lambda r: r.sleep_duration,
        'deep_sleep_duration': lambda r: r.deep_sleep_duration,
        'rem_sleep_duration': lambda r: r.rem_sleep_duration,
        'sleep_score': lambda r: r.sleep_score,
        'readiness_score': lambda r: r.readiness_score,
        'activity_score': lambda r: r.activity_score,
        'hrv': lambda r: r.hrv,
        'resting_heart_rate': lambda r: r.resting_heart_rate,
    }

    if metric_name not in metric_getter:
        return None

    getter = metric_getter[metric_name]

    # Determine unit
    unit_map = {
        'sleep_duration': 'hours',
        'deep_sleep_duration': 'hours',
        'rem_sleep_duration': 'hours',
        'sleep_score': 'score',
        'readiness_score': 'score',
        'activity_score': 'score',
        'hrv': 'ms',
        'resting_heart_rate': 'bpm',
    }
    unit = unit_map.get(metric_name, '')

    # Create time series
    time_series = TimeSeriesData(
        metric_name=metric_name,
        unit=unit
    )

    for record in health_records:
        value = getter(record)
        if value is not None:
            time_series.add_point(
                timestamp=record.date,
                value=float(value)
            )

    if not time_series.data_points or len(time_series.data_points) < min_samples:
        return None

    return detect_trend(
        time_series=time_series,
        window_days=window_days,
        min_samples=min_samples,
        min_confidence=min_confidence
    )


def analyze_productivity_trend(
    productivity_records: List[ProductivityRecord],
    window_days: int = 30,
    min_samples: int = 7,
    min_confidence: float = 0.6
) -> Optional[Trend]:
    """Analyze trend in overall productivity score.

    Detects whether composite productivity is improving, declining, or stable.

    Args:
        productivity_records: List of productivity records
        window_days: Number of days to analyze
        min_samples: Minimum number of samples required
        min_confidence: Minimum confidence score

    Returns:
        Trend object if significant trend detected, None otherwise

    Examples:
        "Productivity improving (6.5 → 8.2 over 30 days)"
        "Productivity declining by 18% this month"
    """
    if not productivity_records or len(productivity_records) < min_samples:
        return None

    # Create time series
    time_series = TimeSeriesData(
        metric_name="productivity_score",
        unit="score"
    )

    for record in productivity_records:
        time_series.add_point(
            timestamp=record.date,
            value=record.productivity_score,
            metadata={
                'tasks_completed': record.tasks_completed,
                'focus_time': record.focus_time,
                'energy_level': record.energy_level
            }
        )

    return detect_trend(
        time_series=time_series,
        window_days=window_days,
        min_samples=min_samples,
        min_confidence=min_confidence
    )


def calculate_momentum(
    time_series: TimeSeriesData,
    short_window_days: int = 7,
    long_window_days: int = 30
) -> Dict[str, Optional[Trend]]:
    """Calculate momentum indicators for short and long term trends.

    Compares 7-day and 30-day trends to identify momentum building or fading.

    Args:
        time_series: TimeSeriesData to analyze
        short_window_days: Short-term window (default: 7 days)
        long_window_days: Long-term window (default: 30 days)

    Returns:
        Dictionary with '7-day' and '30-day' keys containing Trend objects

    Examples:
        "7-day momentum: Strong improvement (+12%)"
        "30-day momentum: Gradual decline (-8%)"
        "Momentum building: 7-day trend stronger than 30-day"
    """
    momentum = {}

    # Calculate short-term trend
    short_trend = detect_trend(
        time_series=time_series,
        window_days=short_window_days,
        min_samples=min(5, short_window_days),
        min_confidence=0.5  # Lower threshold for momentum
    )
    momentum['7-day'] = short_trend

    # Calculate long-term trend
    long_trend = detect_trend(
        time_series=time_series,
        window_days=long_window_days,
        min_samples=7,
        min_confidence=0.5
    )
    momentum['30-day'] = long_trend

    # Add momentum comparison
    if short_trend and long_trend:
        if short_trend.change_percentage > long_trend.change_percentage:
            momentum['momentum_status'] = 'building'
        elif short_trend.change_percentage < long_trend.change_percentage:
            momentum['momentum_status'] = 'fading'
        else:
            momentum['momentum_status'] = 'stable'
    else:
        momentum['momentum_status'] = 'insufficient_data'

    return momentum


def get_all_trends(
    task_records: List[TaskCompletionRecord],
    health_records: List[HealthMetricRecord],
    productivity_records: List[ProductivityRecord],
    window_days: int = 30,
    min_confidence: float = 0.6
) -> Dict[str, Optional[Trend]]:
    """Analyze all available trends and return comprehensive results.

    Convenience function to analyze trends across all metrics at once.

    Args:
        task_records: List of task completion records
        health_records: List of health metric records
        productivity_records: List of productivity records
        window_days: Number of days to analyze
        min_confidence: Minimum confidence score

    Returns:
        Dictionary with trend names as keys and Trend objects as values

    Example keys:
        'tasks_per_day', 'productivity_score', 'sleep_duration',
        'readiness_score', 'deep_sleep_duration'
    """
    trends = {}

    # Task completion trend
    trends['tasks_per_day'] = analyze_task_completion_trend(
        task_records=task_records,
        window_days=window_days,
        min_confidence=min_confidence
    )

    # Productivity trend
    trends['productivity_score'] = analyze_productivity_trend(
        productivity_records=productivity_records,
        window_days=window_days,
        min_confidence=min_confidence
    )

    # Health metric trends
    health_metrics = [
        'sleep_duration',
        'readiness_score',
        'deep_sleep_duration',
        'sleep_score',
        'activity_score'
    ]

    for metric in health_metrics:
        trends[metric] = analyze_health_metric_trend(
            health_records=health_records,
            metric_name=metric,
            window_days=window_days,
            min_confidence=min_confidence
        )

    # Calculate momentum for key metrics
    if task_records:
        task_series = TimeSeriesData(metric_name="tasks_per_day", unit="tasks")
        for record in task_records:
            task_series.add_point(record.date, float(record.tasks_completed))
        trends['task_momentum'] = calculate_momentum(task_series)

    return trends


# Helper functions

def _calculate_linear_regression_slope(data_points: List) -> float:
    """Calculate linear regression slope for trend detection.

    Args:
        data_points: List of DataPoint objects sorted by timestamp

    Returns:
        Slope value (positive = increasing, negative = decreasing)
    """
    if len(data_points) < 2:
        return 0.0

    n = len(data_points)
    x_values = list(range(n))  # Use indices as x values
    y_values = [p.value for p in data_points]

    # Calculate means
    x_mean = statistics.mean(x_values)
    y_mean = statistics.mean(y_values)

    # Calculate slope using least squares method
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)

    if denominator == 0:
        return 0.0

    slope = numerator / denominator
    return slope


def _determine_trend_direction(slope: float, change_pct: float) -> TrendDirection:
    """Determine trend direction based on slope and percentage change.

    Args:
        slope: Linear regression slope
        change_pct: Percentage change over period

    Returns:
        TrendDirection enum value
    """
    # Thresholds for significant change
    IMPROVEMENT_THRESHOLD = 5.0  # 5% improvement
    DECLINE_THRESHOLD = -5.0  # 5% decline
    VOLATILITY_THRESHOLD = 0.15  # High slope variability

    # Check for plateau (minimal change)
    if DECLINE_THRESHOLD < change_pct < IMPROVEMENT_THRESHOLD:
        # Check if slope indicates volatility
        if abs(slope) > VOLATILITY_THRESHOLD:
            return TrendDirection.VOLATILE
        return TrendDirection.PLATEAU

    # Determine direction
    if change_pct >= IMPROVEMENT_THRESHOLD:
        return TrendDirection.IMPROVING
    elif change_pct <= DECLINE_THRESHOLD:
        return TrendDirection.DECLINING
    else:
        return TrendDirection.PLATEAU


def _calculate_trend_strength(values: List[float], direction: TrendDirection) -> float:
    """Calculate how strong/consistent the trend is.

    Args:
        values: List of values in chronological order
        direction: Detected trend direction

    Returns:
        Strength score between 0.0 and 1.0
    """
    if len(values) < 2:
        return 0.0

    # For plateau or volatile, strength is based on stability (inverse of variance)
    if direction in [TrendDirection.PLATEAU, TrendDirection.VOLATILE]:
        if len(values) > 1:
            mean = statistics.mean(values)
            if mean != 0:
                cv = statistics.stdev(values) / abs(mean)  # Coefficient of variation
                stability = max(0.0, 1.0 - cv)
                return stability
        return 0.5

    # For improving/declining, strength is based on consistency of movement
    # Count how many consecutive moves are in the expected direction
    movements_in_direction = 0
    total_movements = 0

    for i in range(1, len(values)):
        diff = values[i] - values[i-1]
        total_movements += 1

        if direction == TrendDirection.IMPROVING and diff > 0:
            movements_in_direction += 1
        elif direction == TrendDirection.DECLINING and diff < 0:
            movements_in_direction += 1
        elif diff == 0:  # No change counts as partial consistency
            movements_in_direction += 0.5

    consistency = movements_in_direction / total_movements if total_movements > 0 else 0.0

    return max(0.0, min(1.0, consistency))


def _calculate_momentum_category(window_days: int) -> str:
    """Determine momentum indicator category based on window size.

    Args:
        window_days: Number of days in the trend window

    Returns:
        Momentum category string
    """
    if window_days <= 7:
        return "7-day"
    elif window_days <= 14:
        return "14-day"
    elif window_days <= 30:
        return "30-day"
    elif window_days <= 60:
        return "60-day"
    else:
        return "90-day"


def _calculate_confidence(
    sample_size: int,
    trend_strength: float,
    change_magnitude: float,
    min_samples: int
) -> float:
    """Calculate confidence score for trend detection.

    Args:
        sample_size: Number of data points
        trend_strength: Strength/consistency of trend (0.0 to 1.0)
        change_magnitude: Absolute percentage change
        min_samples: Minimum required samples

    Returns:
        Confidence score between 0.0 and 1.0
    """
    # Sample size component (0.0 to 1.0)
    # Reaches 0.9 at 3x min_samples, caps at 0.95
    sample_factor = min(0.95, 0.5 + (sample_size / (min_samples * 3)) * 0.45)

    # Trend strength component (already 0.0 to 1.0)
    strength_factor = max(0.0, min(1.0, trend_strength))

    # Change magnitude component (0.0 to 1.0)
    # Significant changes (>15%) get higher scores
    magnitude_factor = min(1.0, change_magnitude / 15.0) * 0.5 + 0.5

    # Weighted combination: 40% sample size, 35% trend strength, 25% magnitude
    confidence = (
        sample_factor * 0.40 +
        strength_factor * 0.35 +
        magnitude_factor * 0.25
    )

    return max(0.0, min(1.0, confidence))


def _build_trend_description(
    metric_name: str,
    direction: TrendDirection,
    start_value: float,
    end_value: float,
    change_pct: float,
    unit: str
) -> str:
    """Build human-readable trend description.

    Args:
        metric_name: Name of the metric
        direction: Trend direction
        start_value: Starting value
        end_value: Ending value
        change_pct: Percentage change
        unit: Unit of measurement

    Returns:
        Formatted description string
    """
    metric_display = metric_name.replace('_', ' ').title()

    if direction == TrendDirection.IMPROVING:
        return (
            f"{metric_display} improving "
            f"({start_value:.1f} → {end_value:.1f} {unit}, "
            f"+{change_pct:.1f}%)"
        )
    elif direction == TrendDirection.DECLINING:
        return (
            f"{metric_display} declining "
            f"({start_value:.1f} → {end_value:.1f} {unit}, "
            f"{change_pct:.1f}%)"
        )
    elif direction == TrendDirection.PLATEAU:
        avg = (start_value + end_value) / 2
        return (
            f"{metric_display} stable "
            f"(around {avg:.1f} {unit}, "
            f"{change_pct:+.1f}%)"
        )
    else:  # VOLATILE
        return (
            f"{metric_display} volatile "
            f"({start_value:.1f} ↔ {end_value:.1f} {unit}, "
            f"inconsistent pattern)"
        )
