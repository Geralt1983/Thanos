"""Task completion pattern analyzer.

Analyzes task completion patterns by time of day, day of week, task types, and
calculates average daily completion rates. Identifies when users are most productive
and surfaces actionable insights.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics

from ..models import TaskCompletionPattern, PatternType
from ..time_series import TaskCompletionRecord


def analyze_hourly_patterns(
    task_records: List[TaskCompletionRecord],
    min_samples: int = 5,
    min_confidence: float = 0.7
) -> List[TaskCompletionPattern]:
    """Analyze task completion patterns by hour of day.

    Identifies which hours of the day show the highest task completion rates,
    helping users understand their peak productivity windows.

    Args:
        task_records: List of task completion records
        min_samples: Minimum number of samples required for a pattern
        min_confidence: Minimum confidence score to include pattern

    Returns:
        List of TaskCompletionPattern objects for significant hourly patterns

    Examples:
        Patterns like "Most productive 9-11am" or "Low energy 2-4pm"
    """
    if not task_records:
        return []

    # Aggregate completions by hour
    hourly_completions = defaultdict(list)

    for record in task_records:
        hourly_dist = record.get_hourly_distribution()
        for hour, count in hourly_dist.items():
            hourly_completions[hour].append(count)

    patterns = []

    # Calculate statistics for each hour
    hourly_stats = {}
    for hour in range(24):
        if hour in hourly_completions and len(hourly_completions[hour]) >= min_samples:
            counts = hourly_completions[hour]
            hourly_stats[hour] = {
                'mean': statistics.mean(counts),
                'median': statistics.median(counts),
                'total': sum(counts),
                'sample_size': len(counts)
            }

    if not hourly_stats:
        return []

    # Find overall average for comparison
    all_means = [stats['mean'] for stats in hourly_stats.values()]
    overall_avg = statistics.mean(all_means)

    # Identify peak hours (significantly above average)
    peak_hours = []
    for hour, stats in hourly_stats.items():
        if stats['mean'] > overall_avg * 1.2:  # 20% above average
            peak_hours.append((hour, stats))

    # Group consecutive peak hours into time windows
    if peak_hours:
        peak_hours.sort(key=lambda x: x[0])
        windows = _group_consecutive_hours(peak_hours)

        for window_hours, window_stats in windows:
            # Calculate window statistics
            window_mean = statistics.mean([s['mean'] for _, s in window_stats])
            window_total = sum([s['total'] for _, s in window_stats])
            window_samples = sum([s['sample_size'] for _, s in window_stats])

            # Calculate confidence based on sample size and consistency
            confidence = _calculate_confidence(
                sample_size=window_samples,
                consistency=1.0 - (statistics.stdev([s['mean'] for _, s in window_stats]) / window_mean if len(window_stats) > 1 else 0),
                min_samples=min_samples
            )

            if confidence >= min_confidence:
                # Format time period
                if len(window_hours) == 1:
                    time_period = f"{window_hours[0]:02d}:00"
                else:
                    time_period = f"{window_hours[0]:02d}:00-{window_hours[-1]+1:02d}:00"

                # Calculate completion rate relative to average
                completion_rate = (window_mean / overall_avg) if overall_avg > 0 else 1.0

                # Get date range
                dates = [r.date for r in task_records]
                date_start = min(dates)
                date_end = max(dates)

                description = f"Peak productivity during {time_period} ({completion_rate:.0%} of average)"

                evidence = [
                    f"Average {window_mean:.1f} tasks completed per hour",
                    f"Total {window_total:.0f} tasks completed in this window",
                    f"Based on {window_samples} observations"
                ]

                pattern = TaskCompletionPattern(
                    pattern_type=PatternType.HOURLY,
                    description=description,
                    time_period=time_period,
                    completion_rate=completion_rate,
                    sample_size=window_samples,
                    confidence_score=confidence,
                    date_range_start=date_start,
                    date_range_end=date_end,
                    evidence=evidence,
                    metadata={
                        'hours': window_hours,
                        'avg_tasks_per_hour': window_mean,
                        'overall_avg': overall_avg
                    }
                )
                patterns.append(pattern)

    return patterns


def analyze_daily_patterns(
    task_records: List[TaskCompletionRecord],
    min_samples: int = 3,
    min_confidence: float = 0.7
) -> List[TaskCompletionPattern]:
    """Analyze task completion patterns by day of week.

    Identifies which days of the week show different completion rates,
    helping users understand weekly productivity patterns.

    Args:
        task_records: List of task completion records
        min_samples: Minimum number of samples required for a pattern
        min_confidence: Minimum confidence score to include pattern

    Returns:
        List of TaskCompletionPattern objects for day-of-week patterns

    Examples:
        Patterns like "Mondays are slowest" or "Fridays show high completion rates"
    """
    if not task_records:
        return []

    # Aggregate by day of week (0=Monday, 6=Sunday)
    daily_completions = defaultdict(list)

    for record in task_records:
        day_of_week = record.date.weekday()
        daily_completions[day_of_week].append(record.tasks_completed)

    patterns = []
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    # Calculate statistics for each day
    daily_stats = {}
    for day in range(7):
        if day in daily_completions and len(daily_completions[day]) >= min_samples:
            counts = daily_completions[day]
            daily_stats[day] = {
                'mean': statistics.mean(counts),
                'median': statistics.median(counts),
                'sample_size': len(counts),
                'total': sum(counts)
            }

    if not daily_stats:
        return []

    # Find overall average
    all_means = [stats['mean'] for stats in daily_stats.values()]
    overall_avg = statistics.mean(all_means)

    # Identify significant deviations from average
    for day, stats in daily_stats.items():
        deviation = (stats['mean'] - overall_avg) / overall_avg if overall_avg > 0 else 0

        # Only report significant deviations (>15% difference)
        if abs(deviation) > 0.15:
            confidence = _calculate_confidence(
                sample_size=stats['sample_size'],
                consistency=0.8,  # Moderate consistency for weekly patterns
                min_samples=min_samples
            )

            if confidence >= min_confidence:
                day_name = day_names[day]

                if deviation > 0:
                    description = f"{day_name}s show higher completion rate (+{abs(deviation):.0%})"
                else:
                    description = f"{day_name}s show lower completion rate (-{abs(deviation):.0%})"

                dates = [r.date for r in task_records if r.date.weekday() == day]
                date_start = min(dates)
                date_end = max(dates)

                completion_rate = stats['mean'] / overall_avg if overall_avg > 0 else 1.0

                evidence = [
                    f"Average {stats['mean']:.1f} tasks on {day_name}s",
                    f"Overall average: {overall_avg:.1f} tasks/day",
                    f"Based on {stats['sample_size']} {day_name}s"
                ]

                pattern = TaskCompletionPattern(
                    pattern_type=PatternType.DAILY,
                    description=description,
                    time_period=day_name,
                    completion_rate=completion_rate,
                    sample_size=stats['sample_size'],
                    confidence_score=confidence,
                    date_range_start=date_start,
                    date_range_end=date_end,
                    evidence=evidence,
                    metadata={
                        'day_of_week': day,
                        'deviation': deviation,
                        'overall_avg': overall_avg
                    }
                )
                patterns.append(pattern)

    return patterns


def analyze_task_type_patterns(
    task_records: List[TaskCompletionRecord],
    min_samples: int = 5,
    min_confidence: float = 0.7
) -> List[TaskCompletionPattern]:
    """Analyze when different task types are typically completed.

    Identifies patterns in what types of tasks are completed at different times,
    helping users optimize their schedule based on task type.

    Args:
        task_records: List of task completion records with task_types populated
        min_samples: Minimum number of samples required for a pattern
        min_confidence: Minimum confidence score to include pattern

    Returns:
        List of TaskCompletionPattern objects for task type patterns

    Examples:
        Patterns like "Deep work tasks completed best in morning" or
        "Administrative tasks typically done in afternoon"
    """
    if not task_records:
        return []

    # Aggregate task types by time of day
    task_type_hourly = defaultdict(lambda: defaultdict(int))
    task_type_totals = defaultdict(int)

    for record in task_records:
        for task_type, count in record.task_types.items():
            task_type_totals[task_type] += count

            # Get hourly distribution for this day
            hourly_dist = record.get_hourly_distribution()
            # Distribute task type counts proportionally across hours
            # (This is an approximation since we don't have per-task-type timing)
            total_completions = sum(hourly_dist.values())
            if total_completions > 0:
                for hour, hour_count in hourly_dist.items():
                    # Proportional allocation
                    allocated = (hour_count / total_completions) * count
                    task_type_hourly[task_type][hour] += allocated

    patterns = []

    # Analyze each task type
    for task_type, hourly_counts in task_type_hourly.items():
        if task_type_totals[task_type] < min_samples:
            continue

        # Find peak hours for this task type
        if not hourly_counts:
            continue

        total_count = sum(hourly_counts.values())
        hourly_percentages = {hour: count / total_count for hour, count in hourly_counts.items()}

        # Find hours with significant concentration (>15% of tasks for that type)
        peak_hours = [(hour, pct) for hour, pct in hourly_percentages.items() if pct > 0.15]

        if peak_hours:
            peak_hours.sort(key=lambda x: x[1], reverse=True)
            top_hour, top_pct = peak_hours[0]

            # Calculate confidence based on concentration and sample size
            concentration = top_pct
            confidence = _calculate_confidence(
                sample_size=task_type_totals[task_type],
                consistency=concentration,
                min_samples=min_samples
            )

            if confidence >= min_confidence:
                time_period = f"{top_hour:02d}:00-{top_hour+1:02d}:00"

                dates = [r.date for r in task_records if task_type in r.task_types]
                date_start = min(dates) if dates else datetime.now()
                date_end = max(dates) if dates else datetime.now()

                description = f"'{task_type}' tasks typically completed during {time_period} ({top_pct:.0%} concentration)"

                evidence = [
                    f"{top_pct:.0%} of '{task_type}' tasks done around {top_hour:02d}:00",
                    f"Total {task_type_totals[task_type]:.0f} '{task_type}' tasks analyzed",
                ]

                # Add secondary peak if exists
                if len(peak_hours) > 1:
                    second_hour, second_pct = peak_hours[1]
                    evidence.append(f"Secondary peak at {second_hour:02d}:00 ({second_pct:.0%})")

                pattern = TaskCompletionPattern(
                    pattern_type=PatternType.TASK_TYPE,
                    description=description,
                    time_period=time_period,
                    completion_rate=top_pct,
                    sample_size=int(task_type_totals[task_type]),
                    confidence_score=confidence,
                    date_range_start=date_start,
                    date_range_end=date_end,
                    evidence=evidence,
                    metadata={
                        'task_type': task_type,
                        'peak_hour': top_hour,
                        'concentration': top_pct,
                        'all_peak_hours': peak_hours
                    }
                )
                patterns.append(pattern)

    return patterns


def calculate_daily_completion_rate(
    task_records: List[TaskCompletionRecord],
    period_days: int = 30
) -> Tuple[float, float, Dict[str, float]]:
    """Calculate average daily task completion rate and statistics.

    Args:
        task_records: List of task completion records
        period_days: Number of days to analyze (default: 30)

    Returns:
        Tuple of (avg_rate, trend_direction, stats_dict)
        - avg_rate: Average tasks completed per day
        - trend_direction: Change percentage over period (positive = improving)
        - stats_dict: Dictionary with detailed statistics
    """
    if not task_records:
        return 0.0, 0.0, {}

    # Sort by date
    sorted_records = sorted(task_records, key=lambda r: r.date)

    # Filter to requested period
    if period_days:
        cutoff_date = sorted_records[-1].date - timedelta(days=period_days)
        sorted_records = [r for r in sorted_records if r.date >= cutoff_date]

    if not sorted_records:
        return 0.0, 0.0, {}

    # Calculate overall average
    total_tasks = sum(r.tasks_completed for r in sorted_records)
    avg_rate = total_tasks / len(sorted_records)

    # Calculate trend (compare first half vs second half)
    mid_point = len(sorted_records) // 2
    if mid_point > 0:
        first_half = sorted_records[:mid_point]
        second_half = sorted_records[mid_point:]

        first_avg = sum(r.tasks_completed for r in first_half) / len(first_half)
        second_avg = sum(r.tasks_completed for r in second_half) / len(second_half)

        trend = ((second_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0.0
    else:
        first_avg = avg_rate
        second_avg = avg_rate
        trend = 0.0

    # Calculate additional statistics
    completion_counts = [r.tasks_completed for r in sorted_records]

    stats = {
        'average_daily_rate': avg_rate,
        'median_daily_rate': statistics.median(completion_counts),
        'min_daily': min(completion_counts),
        'max_daily': max(completion_counts),
        'std_dev': statistics.stdev(completion_counts) if len(completion_counts) > 1 else 0.0,
        'total_days': len(sorted_records),
        'total_tasks': total_tasks,
        'trend_percentage': trend,
        'first_half_avg': first_avg,
        'second_half_avg': second_avg,
        'date_range_start': sorted_records[0].date,
        'date_range_end': sorted_records[-1].date
    }

    return avg_rate, trend, stats


def get_all_task_patterns(
    task_records: List[TaskCompletionRecord],
    min_samples_hourly: int = 5,
    min_samples_daily: int = 3,
    min_samples_task_type: int = 5,
    min_confidence: float = 0.7
) -> Dict[str, List[TaskCompletionPattern]]:
    """Run all task pattern analyses and return comprehensive results.

    Convenience function to analyze all pattern types at once.

    Args:
        task_records: List of task completion records
        min_samples_hourly: Minimum samples for hourly patterns
        min_samples_daily: Minimum samples for daily patterns
        min_samples_task_type: Minimum samples for task type patterns
        min_confidence: Minimum confidence score for all patterns

    Returns:
        Dictionary with keys: 'hourly', 'daily', 'task_type', 'summary'
        Each containing relevant patterns or statistics
    """
    results = {
        'hourly': analyze_hourly_patterns(
            task_records,
            min_samples=min_samples_hourly,
            min_confidence=min_confidence
        ),
        'daily': analyze_daily_patterns(
            task_records,
            min_samples=min_samples_daily,
            min_confidence=min_confidence
        ),
        'task_type': analyze_task_type_patterns(
            task_records,
            min_samples=min_samples_task_type,
            min_confidence=min_confidence
        ),
    }

    # Add summary statistics
    avg_rate, trend, stats = calculate_daily_completion_rate(task_records)
    results['summary'] = {
        'daily_completion_rate': stats,
        'total_patterns_found': sum(len(patterns) for patterns in results.values() if isinstance(patterns, list))
    }

    return results


def _group_consecutive_hours(
    hourly_data: List[Tuple[int, Dict]]
) -> List[Tuple[List[int], List[Tuple[int, Dict]]]]:
    """Group consecutive hours into time windows.

    Args:
        hourly_data: List of (hour, stats) tuples sorted by hour

    Returns:
        List of (hours_list, data_list) tuples representing consecutive windows
    """
    if not hourly_data:
        return []

    windows = []
    current_window_hours = [hourly_data[0][0]]
    current_window_data = [hourly_data[0]]

    for i in range(1, len(hourly_data)):
        hour, stats = hourly_data[i]
        prev_hour = hourly_data[i-1][0]

        # Check if consecutive (handle wrap-around at midnight)
        if hour == prev_hour + 1 or (prev_hour == 23 and hour == 0):
            current_window_hours.append(hour)
            current_window_data.append((hour, stats))
        else:
            # Start new window
            windows.append((current_window_hours, current_window_data))
            current_window_hours = [hour]
            current_window_data = [(hour, stats)]

    # Add last window
    windows.append((current_window_hours, current_window_data))

    return windows


def _calculate_confidence(
    sample_size: int,
    consistency: float,
    min_samples: int
) -> float:
    """Calculate confidence score based on sample size and consistency.

    Args:
        sample_size: Number of data points
        consistency: Measure of pattern consistency (0.0 to 1.0)
        min_samples: Minimum required samples

    Returns:
        Confidence score between 0.0 and 1.0
    """
    # Sample size component (0.0 to 1.0)
    # Reaches 0.9 at 3x min_samples, caps at 0.95
    sample_factor = min(0.95, 0.5 + (sample_size / (min_samples * 3)) * 0.4)

    # Consistency component (already 0.0 to 1.0)
    consistency_factor = max(0.0, min(1.0, consistency))

    # Weighted combination: 60% sample size, 40% consistency
    confidence = (sample_factor * 0.6) + (consistency_factor * 0.4)

    return max(0.0, min(1.0, confidence))
