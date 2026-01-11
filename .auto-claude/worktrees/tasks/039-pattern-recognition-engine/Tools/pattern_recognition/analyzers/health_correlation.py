"""Health and productivity correlation analyzer.

Analyzes correlations between health metrics (sleep duration, readiness scores, deep sleep,
sleep timing) and productivity metrics (tasks completed, focus, energy levels). Uses Oura
health data to identify actionable patterns.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics

from ..models import HealthCorrelation
from ..time_series import HealthMetricRecord, TaskCompletionRecord, ProductivityRecord


def correlate_sleep_duration_with_tasks(
    health_records: List[HealthMetricRecord],
    task_records: List[TaskCompletionRecord],
    min_samples: int = 7,
    min_confidence: float = 0.6
) -> Optional[HealthCorrelation]:
    """Correlate sleep duration with task completion.

    Analyzes the relationship between hours of sleep and number of tasks completed
    the next day, identifying optimal sleep thresholds.

    Args:
        health_records: List of health metric records with sleep data
        task_records: List of task completion records
        min_samples: Minimum number of paired samples required
        min_confidence: Minimum confidence score to return correlation

    Returns:
        HealthCorrelation object if significant correlation found, None otherwise

    Examples:
        "7+ hours of sleep correlates with 40% more tasks completed"
    """
    # Pair up sleep data with next-day task completion
    paired_data = _pair_health_with_next_day_metric(
        health_records,
        task_records,
        health_metric="sleep_duration",
        productivity_getter=lambda r: r.tasks_completed
    )

    if len(paired_data) < min_samples:
        return None

    # Calculate correlation
    correlation_coef = _calculate_pearson_correlation(paired_data)
    if correlation_coef is None:
        return None

    # Find optimal threshold (where performance is notably better)
    threshold, effect = _find_optimal_threshold(paired_data)

    if threshold is None or abs(correlation_coef) < 0.3:
        return None

    # Calculate confidence
    confidence = _calculate_confidence(
        sample_size=len(paired_data),
        correlation_strength=abs(correlation_coef),
        min_samples=min_samples
    )

    if confidence < min_confidence:
        return None

    # Build correlation description
    if correlation_coef > 0:
        description = f"More sleep correlates with higher task completion (r={correlation_coef:.2f})"
    else:
        description = f"Sleep duration negatively correlates with task completion (r={correlation_coef:.2f})"

    # Get date range
    dates = [h.date for h, _ in paired_data]
    date_start = min(dates)
    date_end = max(dates)

    # Calculate average tasks for threshold groups
    above_threshold = [tasks for sleep, tasks in paired_data if sleep >= threshold]
    below_threshold = [tasks for sleep, tasks in paired_data if sleep < threshold]

    avg_above = statistics.mean(above_threshold) if above_threshold else 0
    avg_below = statistics.mean(below_threshold) if below_threshold else 0

    evidence = [
        f"Correlation coefficient: {correlation_coef:.2f}",
        f"Optimal sleep threshold: {threshold:.1f} hours",
        f"Average tasks with {threshold:.1f}+ hours sleep: {avg_above:.1f}",
        f"Average tasks with <{threshold:.1f} hours sleep: {avg_below:.1f}",
        f"Based on {len(paired_data)} days of data"
    ]

    return HealthCorrelation(
        health_metric="sleep_duration",
        productivity_metric="tasks_completed",
        correlation_strength=correlation_coef,
        correlation_description=description,
        threshold_value=threshold,
        effect_size=effect,
        confidence_score=confidence,
        sample_size=len(paired_data),
        date_range_start=date_start,
        date_range_end=date_end,
        evidence=evidence,
        metadata={
            "avg_tasks_above_threshold": avg_above,
            "avg_tasks_below_threshold": avg_below,
            "days_above_threshold": len(above_threshold),
            "days_below_threshold": len(below_threshold)
        }
    )


def correlate_readiness_with_productivity(
    health_records: List[HealthMetricRecord],
    productivity_records: List[ProductivityRecord],
    min_samples: int = 7,
    min_confidence: float = 0.6
) -> Optional[HealthCorrelation]:
    """Correlate Oura readiness score with productivity.

    Analyzes the relationship between daily readiness scores and productivity
    metrics, helping predict high/low energy days.

    Args:
        health_records: List of health metric records with readiness scores
        productivity_records: List of productivity records
        min_samples: Minimum number of paired samples required
        min_confidence: Minimum confidence score to return correlation

    Returns:
        HealthCorrelation object if significant correlation found, None otherwise

    Examples:
        "Readiness score >85 predicts 50% higher productivity"
    """
    # Pair readiness scores with same-day productivity
    paired_data = _pair_health_with_same_day_metric(
        health_records,
        productivity_records,
        health_metric="readiness_score",
        productivity_getter=lambda r: r.productivity_score
    )

    if len(paired_data) < min_samples:
        return None

    # Calculate correlation
    correlation_coef = _calculate_pearson_correlation(paired_data)
    if correlation_coef is None or abs(correlation_coef) < 0.3:
        return None

    # Find optimal threshold
    threshold, effect = _find_optimal_threshold(paired_data)

    if threshold is None:
        return None

    # Calculate confidence
    confidence = _calculate_confidence(
        sample_size=len(paired_data),
        correlation_strength=abs(correlation_coef),
        min_samples=min_samples
    )

    if confidence < min_confidence:
        return None

    # Build description
    if correlation_coef > 0.4:
        description = f"Strong positive correlation between readiness and productivity (r={correlation_coef:.2f})"
    elif correlation_coef > 0:
        description = f"Moderate positive correlation between readiness and productivity (r={correlation_coef:.2f})"
    else:
        description = f"Readiness shows negative correlation with productivity (r={correlation_coef:.2f})"

    # Get date range
    dates = [h.date for h, _ in paired_data]
    date_start = min(dates)
    date_end = max(dates)

    # Calculate averages for threshold groups
    above_threshold = [prod for ready, prod in paired_data if ready >= threshold]
    below_threshold = [prod for ready, prod in paired_data if ready < threshold]

    avg_above = statistics.mean(above_threshold) if above_threshold else 0
    avg_below = statistics.mean(below_threshold) if below_threshold else 0

    evidence = [
        f"Correlation coefficient: {correlation_coef:.2f}",
        f"Optimal readiness threshold: {threshold:.0f}",
        f"Average productivity with readiness ≥{threshold:.0f}: {avg_above:.1f}",
        f"Average productivity with readiness <{threshold:.0f}: {avg_below:.1f}",
        f"Based on {len(paired_data)} days of data"
    ]

    return HealthCorrelation(
        health_metric="readiness_score",
        productivity_metric="productivity_score",
        correlation_strength=correlation_coef,
        correlation_description=description,
        threshold_value=threshold,
        effect_size=effect,
        confidence_score=confidence,
        sample_size=len(paired_data),
        date_range_start=date_start,
        date_range_end=date_end,
        evidence=evidence,
        metadata={
            "avg_productivity_above_threshold": avg_above,
            "avg_productivity_below_threshold": avg_below,
            "days_above_threshold": len(above_threshold),
            "days_below_threshold": len(below_threshold)
        }
    )


def correlate_deep_sleep_with_focus(
    health_records: List[HealthMetricRecord],
    productivity_records: List[ProductivityRecord],
    min_samples: int = 7,
    min_confidence: float = 0.6
) -> Optional[HealthCorrelation]:
    """Correlate deep sleep duration with next-day focus.

    Analyzes the relationship between deep sleep and focus time the following day,
    identifying how sleep quality affects cognitive performance.

    Args:
        health_records: List of health metric records with deep sleep data
        productivity_records: List of productivity records with focus time
        min_samples: Minimum number of paired samples required
        min_confidence: Minimum confidence score to return correlation

    Returns:
        HealthCorrelation object if significant correlation found, None otherwise

    Examples:
        "90+ minutes of deep sleep correlates with 2x focus time"
    """
    # Pair deep sleep with next-day focus time
    paired_data = _pair_health_with_next_day_metric(
        health_records,
        productivity_records,
        health_metric="deep_sleep_duration",
        productivity_getter=lambda r: r.focus_time
    )

    if len(paired_data) < min_samples:
        return None

    # Calculate correlation
    correlation_coef = _calculate_pearson_correlation(paired_data)
    if correlation_coef is None or abs(correlation_coef) < 0.25:
        return None

    # Find optimal threshold (in hours)
    threshold, effect = _find_optimal_threshold(paired_data)

    if threshold is None:
        return None

    # Calculate confidence
    confidence = _calculate_confidence(
        sample_size=len(paired_data),
        correlation_strength=abs(correlation_coef),
        min_samples=min_samples
    )

    if confidence < min_confidence:
        return None

    # Build description
    if correlation_coef > 0:
        description = f"Deep sleep correlates with better focus next day (r={correlation_coef:.2f})"
    else:
        description = f"Deep sleep negatively correlates with focus (r={correlation_coef:.2f})"

    # Get date range
    dates = [h.date for h, _ in paired_data]
    date_start = min(dates)
    date_end = max(dates)

    # Calculate averages for threshold groups (convert threshold to minutes for display)
    threshold_minutes = threshold * 60
    above_threshold = [focus for deep, focus in paired_data if deep >= threshold]
    below_threshold = [focus for deep, focus in paired_data if deep < threshold]

    avg_above = statistics.mean(above_threshold) if above_threshold else 0
    avg_below = statistics.mean(below_threshold) if below_threshold else 0

    evidence = [
        f"Correlation coefficient: {correlation_coef:.2f}",
        f"Optimal deep sleep threshold: {threshold_minutes:.0f} minutes",
        f"Average focus time with {threshold_minutes:.0f}+ min deep sleep: {avg_above:.1f} hours",
        f"Average focus time with <{threshold_minutes:.0f} min deep sleep: {avg_below:.1f} hours",
        f"Based on {len(paired_data)} days of data"
    ]

    return HealthCorrelation(
        health_metric="deep_sleep_duration",
        productivity_metric="focus_time",
        correlation_strength=correlation_coef,
        correlation_description=description,
        threshold_value=threshold,
        effect_size=effect,
        confidence_score=confidence,
        sample_size=len(paired_data),
        date_range_start=date_start,
        date_range_end=date_end,
        evidence=evidence,
        metadata={
            "avg_focus_above_threshold": avg_above,
            "avg_focus_below_threshold": avg_below,
            "days_above_threshold": len(above_threshold),
            "days_below_threshold": len(below_threshold),
            "threshold_minutes": threshold_minutes
        }
    )


def correlate_sleep_timing_with_morning_energy(
    health_records: List[HealthMetricRecord],
    productivity_records: List[ProductivityRecord],
    morning_hours: Tuple[int, int] = (6, 12),
    min_samples: int = 7,
    min_confidence: float = 0.6
) -> Optional[HealthCorrelation]:
    """Correlate sleep timing with morning energy levels.

    Analyzes whether consistent sleep timing (bedtime/wake time) correlates with
    better morning energy and early productivity.

    Args:
        health_records: List of health metric records
        productivity_records: List of productivity records with energy levels
        morning_hours: Tuple of (start_hour, end_hour) defining morning period
        min_samples: Minimum number of paired samples required
        min_confidence: Minimum confidence score to return correlation

    Returns:
        HealthCorrelation object if significant correlation found, None otherwise

    Examples:
        "Consistent sleep timing (±30min) correlates with higher morning energy"
    """
    # This requires bedtime data which may not be directly in HealthMetricRecord
    # For now, we'll use sleep_score as a proxy for sleep timing consistency
    # (Oura's sleep score includes timing consistency)

    paired_data = _pair_health_with_same_day_metric(
        health_records,
        productivity_records,
        health_metric="sleep_score",
        productivity_getter=lambda r: r.energy_level if r.energy_level else 5.0
    )

    if len(paired_data) < min_samples:
        return None

    # Calculate correlation
    correlation_coef = _calculate_pearson_correlation(paired_data)
    if correlation_coef is None or abs(correlation_coef) < 0.25:
        return None

    # Find optimal threshold
    threshold, effect = _find_optimal_threshold(paired_data)

    if threshold is None:
        return None

    # Calculate confidence
    confidence = _calculate_confidence(
        sample_size=len(paired_data),
        correlation_strength=abs(correlation_coef),
        min_samples=min_samples
    )

    if confidence < min_confidence:
        return None

    # Build description
    if correlation_coef > 0:
        description = f"Better sleep quality correlates with higher morning energy (r={correlation_coef:.2f})"
    else:
        description = f"Sleep quality shows unexpected negative correlation with morning energy (r={correlation_coef:.2f})"

    # Get date range
    dates = [h.date for h, _ in paired_data]
    date_start = min(dates)
    date_end = max(dates)

    # Calculate averages for threshold groups
    above_threshold = [energy for score, energy in paired_data if score >= threshold]
    below_threshold = [energy for score, energy in paired_data if score < threshold]

    avg_above = statistics.mean(above_threshold) if above_threshold else 0
    avg_below = statistics.mean(below_threshold) if below_threshold else 0

    evidence = [
        f"Correlation coefficient: {correlation_coef:.2f}",
        f"Optimal sleep score threshold: {threshold:.0f}",
        f"Average morning energy with sleep score ≥{threshold:.0f}: {avg_above:.1f}/10",
        f"Average morning energy with sleep score <{threshold:.0f}: {avg_below:.1f}/10",
        f"Based on {len(paired_data)} days of data"
    ]

    return HealthCorrelation(
        health_metric="sleep_score",
        productivity_metric="morning_energy",
        correlation_strength=correlation_coef,
        correlation_description=description,
        threshold_value=threshold,
        effect_size=effect,
        confidence_score=confidence,
        sample_size=len(paired_data),
        date_range_start=date_start,
        date_range_end=date_end,
        evidence=evidence,
        metadata={
            "avg_energy_above_threshold": avg_above,
            "avg_energy_below_threshold": avg_below,
            "days_above_threshold": len(above_threshold),
            "days_below_threshold": len(below_threshold),
            "morning_hours": morning_hours
        }
    )


def get_all_health_correlations(
    health_records: List[HealthMetricRecord],
    task_records: Optional[List[TaskCompletionRecord]] = None,
    productivity_records: Optional[List[ProductivityRecord]] = None,
    min_samples: int = 7,
    min_confidence: float = 0.6
) -> Dict[str, Optional[HealthCorrelation]]:
    """Run all health correlation analyses and return comprehensive results.

    Convenience function to analyze all correlation types at once.

    Args:
        health_records: List of health metric records
        task_records: Optional list of task completion records
        productivity_records: Optional list of productivity records
        min_samples: Minimum samples for all analyses
        min_confidence: Minimum confidence score for all analyses

    Returns:
        Dictionary with keys for each correlation type containing HealthCorrelation
        objects or None if insufficient data/weak correlation
    """
    results = {}

    # Sleep duration vs tasks
    if task_records:
        results['sleep_duration_vs_tasks'] = correlate_sleep_duration_with_tasks(
            health_records,
            task_records,
            min_samples=min_samples,
            min_confidence=min_confidence
        )

    # Readiness vs productivity
    if productivity_records:
        results['readiness_vs_productivity'] = correlate_readiness_with_productivity(
            health_records,
            productivity_records,
            min_samples=min_samples,
            min_confidence=min_confidence
        )

        # Deep sleep vs focus
        results['deep_sleep_vs_focus'] = correlate_deep_sleep_with_focus(
            health_records,
            productivity_records,
            min_samples=min_samples,
            min_confidence=min_confidence
        )

        # Sleep timing vs morning energy
        results['sleep_timing_vs_morning_energy'] = correlate_sleep_timing_with_morning_energy(
            health_records,
            productivity_records,
            min_samples=min_samples,
            min_confidence=min_confidence
        )

    return results


# Helper functions

def _pair_health_with_next_day_metric(
    health_records: List[HealthMetricRecord],
    productivity_records: List,
    health_metric: str,
    productivity_getter
) -> List[Tuple[float, float]]:
    """Pair health metrics from one day with productivity metrics from the next day.

    Args:
        health_records: List of health records
        productivity_records: List of productivity/task records
        health_metric: Name of health metric field to extract
        productivity_getter: Function to extract productivity value from record

    Returns:
        List of (health_value, productivity_value) tuples
    """
    # Create lookup by date for health metrics
    health_by_date = {}
    for record in health_records:
        value = getattr(record, health_metric, None)
        if value is not None:
            health_by_date[record.date.date()] = value

    # Create lookup by date for productivity
    prod_by_date = {}
    for record in productivity_records:
        value = productivity_getter(record)
        if value is not None and value > 0:
            prod_by_date[record.date.date()] = value

    # Pair health from day N with productivity from day N+1
    paired = []
    for date, health_value in health_by_date.items():
        next_day = date + timedelta(days=1)
        if next_day in prod_by_date:
            paired.append((health_value, prod_by_date[next_day]))

    return paired


def _pair_health_with_same_day_metric(
    health_records: List[HealthMetricRecord],
    productivity_records: List,
    health_metric: str,
    productivity_getter
) -> List[Tuple[float, float]]:
    """Pair health metrics with productivity metrics from the same day.

    Args:
        health_records: List of health records
        productivity_records: List of productivity records
        health_metric: Name of health metric field to extract
        productivity_getter: Function to extract productivity value from record

    Returns:
        List of (health_value, productivity_value) tuples
    """
    # Create lookup by date for health metrics
    health_by_date = {}
    for record in health_records:
        value = getattr(record, health_metric, None)
        if value is not None:
            health_by_date[record.date.date()] = value

    # Create lookup by date for productivity
    prod_by_date = {}
    for record in productivity_records:
        value = productivity_getter(record)
        if value is not None:
            prod_by_date[record.date.date()] = value

    # Pair same-day values
    paired = []
    for date, health_value in health_by_date.items():
        if date in prod_by_date:
            paired.append((health_value, prod_by_date[date]))

    return paired


def _calculate_pearson_correlation(paired_data: List[Tuple[float, float]]) -> Optional[float]:
    """Calculate Pearson correlation coefficient for paired data.

    Args:
        paired_data: List of (x, y) tuples

    Returns:
        Correlation coefficient between -1 and 1, or None if insufficient data
    """
    if len(paired_data) < 2:
        return None

    x_values = [x for x, y in paired_data]
    y_values = [y for x, y in paired_data]

    # Calculate means
    x_mean = statistics.mean(x_values)
    y_mean = statistics.mean(y_values)

    # Calculate correlation coefficient
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in paired_data)

    x_variance = sum((x - x_mean) ** 2 for x in x_values)
    y_variance = sum((y - y_mean) ** 2 for y in y_values)

    denominator = (x_variance * y_variance) ** 0.5

    if denominator == 0:
        return None

    correlation = numerator / denominator

    return max(-1.0, min(1.0, correlation))


def _find_optimal_threshold(
    paired_data: List[Tuple[float, float]],
    percentiles: List[int] = [50, 60, 70, 75, 80]
) -> Tuple[Optional[float], Optional[float]]:
    """Find the optimal threshold that maximizes the difference in outcomes.

    Args:
        paired_data: List of (x, y) tuples where x is the metric to threshold
        percentiles: List of percentiles to test as thresholds

    Returns:
        Tuple of (optimal_threshold, effect_size) or (None, None)
    """
    if len(paired_data) < 4:
        return None, None

    x_values = [x for x, y in paired_data]
    y_values = [y for x, y in paired_data]

    best_threshold = None
    best_effect = 0.0

    for percentile in percentiles:
        try:
            threshold = statistics.quantiles(x_values, n=100)[percentile - 1]
        except (statistics.StatisticsError, IndexError):
            continue

        # Split into above/below threshold
        above = [y for x, y in paired_data if x >= threshold]
        below = [y for x, y in paired_data if x < threshold]

        # Need reasonable sample sizes in both groups
        if len(above) < 2 or len(below) < 2:
            continue

        # Calculate effect size (percentage difference)
        avg_above = statistics.mean(above)
        avg_below = statistics.mean(below)

        if avg_below > 0:
            effect = ((avg_above - avg_below) / avg_below)
        else:
            effect = 0.0

        # Keep threshold with largest positive effect
        if abs(effect) > abs(best_effect):
            best_threshold = threshold
            best_effect = effect

    if best_threshold is None:
        return None, None

    return best_threshold, best_effect


def _calculate_confidence(
    sample_size: int,
    correlation_strength: float,
    min_samples: int
) -> float:
    """Calculate confidence score based on sample size and correlation strength.

    Args:
        sample_size: Number of paired data points
        correlation_strength: Absolute value of correlation coefficient
        min_samples: Minimum required samples

    Returns:
        Confidence score between 0.0 and 1.0
    """
    # Sample size component (0.0 to 1.0)
    # Reaches 0.8 at 2x min_samples, caps at 0.9
    sample_factor = min(0.9, 0.5 + (sample_size / (min_samples * 2)) * 0.4)

    # Correlation strength component (already 0.0 to 1.0)
    correlation_factor = abs(correlation_strength)

    # Weighted combination: 50% sample size, 50% correlation strength
    confidence = (sample_factor * 0.5) + (correlation_factor * 0.5)

    return max(0.0, min(1.0, confidence))
