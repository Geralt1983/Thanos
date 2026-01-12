"""Habit streak analyzer.

Identifies recurring habits, tracks streak lengths, detects streak breaks with root causes,
and calculates habit consistency scores. Helps users understand their habit formation
patterns and what factors contribute to breaking streaks.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics

from ..models import HabitStreak
from ..time_series import TaskCompletionRecord, HealthMetricRecord


def identify_recurring_habits(
    task_records: List[TaskCompletionRecord],
    min_occurrences: int = 5,
    min_days_span: int = 7
) -> List[str]:
    """Identify recurring habits from task completion records.

    Analyzes task types to identify which ones appear frequently enough
    to be considered habits worthy of tracking.

    Args:
        task_records: List of task completion records
        min_occurrences: Minimum number of times a task must appear
        min_days_span: Minimum number of days the task must span

    Returns:
        List of habit names (task types) that qualify as recurring habits

    Examples:
        ["daily_review", "exercise", "meditation"]
    """
    if not task_records:
        return []

    # Count occurrences and track date range for each task type
    task_type_occurrences = defaultdict(int)
    task_type_dates = defaultdict(set)

    for record in task_records:
        for task_type, count in record.task_types.items():
            if count > 0:
                task_type_occurrences[task_type] += count
                task_type_dates[task_type].add(record.date.date())

    # Filter to habits that meet criteria
    habits = []
    for task_type, occurrences in task_type_occurrences.items():
        if occurrences < min_occurrences:
            continue

        # Check date span
        dates = sorted(task_type_dates[task_type])
        if len(dates) < 2:
            continue

        days_span = (dates[-1] - dates[0]).days + 1
        if days_span >= min_days_span:
            habits.append(task_type)

    return sorted(habits)


def analyze_habit_streak(
    habit_name: str,
    task_records: List[TaskCompletionRecord],
    expected_frequency_days: int = 1,
    min_confidence: float = 0.6
) -> Optional[HabitStreak]:
    """Analyze streak information for a specific habit.

    Tracks current and longest streaks, identifies breaks, and calculates
    consistency scores for a given habit.

    Args:
        habit_name: Name of the habit to analyze
        task_records: List of task completion records
        expected_frequency_days: Expected frequency (1=daily, 7=weekly, etc.)
        min_confidence: Minimum confidence score to return result

    Returns:
        HabitStreak object with streak information, or None if insufficient data

    Examples:
        Tracks "daily_review" showing 45-day current streak with 89% consistency
    """
    if not task_records:
        return None

    # Sort records by date
    sorted_records = sorted(task_records, key=lambda r: r.date)

    # Extract dates where habit was completed
    completion_dates = []
    for record in sorted_records:
        if habit_name in record.task_types and record.task_types[habit_name] > 0:
            completion_dates.append(record.date.date())

    if not completion_dates:
        return None

    # Remove duplicates and sort
    completion_dates = sorted(set(completion_dates))

    if len(completion_dates) < 2:
        return None

    # Calculate streaks
    current_streak, longest_streak, all_streaks = _calculate_streaks(
        completion_dates,
        expected_frequency_days
    )

    # Determine if streak is currently active
    last_completion = completion_dates[-1]
    today = datetime.now().date()
    days_since_completion = (today - last_completion).days
    is_active = days_since_completion <= expected_frequency_days

    # Calculate consistency score
    date_range_start = sorted_records[0].date.date()
    date_range_end = sorted_records[-1].date.date()
    total_days = (date_range_end - date_range_start).days + 1
    expected_completions = total_days / expected_frequency_days
    consistency_score = min(1.0, len(completion_dates) / expected_completions) if expected_completions > 0 else 0.0

    # Identify break date if not active
    break_date = None
    if not is_active and len(completion_dates) >= 2:
        # Last completion + expected frequency = when it should have been done
        break_date = last_completion + timedelta(days=expected_frequency_days)

    # Calculate confidence based on sample size and consistency
    confidence = _calculate_confidence(
        sample_size=len(completion_dates),
        consistency=consistency_score,
        min_samples=5
    )

    if confidence < min_confidence:
        return None

    # Build evidence list
    evidence = [
        f"Completed {len(completion_dates)} times over {total_days} days",
        f"Current streak: {current_streak} days",
        f"Longest streak: {longest_streak} days",
        f"Consistency: {consistency_score:.0%}"
    ]

    if not is_active:
        evidence.append(f"Last completed {days_since_completion} days ago")

    # Create metadata with streak history
    metadata = {
        "expected_frequency_days": expected_frequency_days,
        "all_streaks": all_streaks,
        "completion_dates": [str(d) for d in completion_dates[-10:]],  # Last 10
        "days_since_completion": days_since_completion,
        "total_expected_completions": expected_completions
    }

    return HabitStreak(
        habit_name=habit_name,
        streak_length=current_streak,
        is_active=is_active,
        last_completion_date=datetime.combine(last_completion, datetime.min.time()),
        break_date=datetime.combine(break_date, datetime.min.time()) if break_date else None,
        break_reasons=[],  # Will be populated by analyze_streak_breaks
        consistency_score=consistency_score,
        longest_streak=longest_streak,
        total_completions=len(completion_dates),
        confidence_score=confidence,
        date_range_start=datetime.combine(date_range_start, datetime.min.time()),
        date_range_end=datetime.combine(date_range_end, datetime.min.time()),
        evidence=evidence,
        metadata=metadata
    )


def analyze_streak_breaks(
    habit_streak: HabitStreak,
    task_records: List[TaskCompletionRecord],
    health_records: Optional[List[HealthMetricRecord]] = None
) -> HabitStreak:
    """Analyze reasons for streak breaks and update the HabitStreak object.

    Examines periods when streaks were broken and attempts to identify
    root causes by correlating with task completion patterns, health metrics,
    and temporal factors (day of week, etc.).

    Args:
        habit_streak: HabitStreak object to analyze
        task_records: List of task completion records
        health_records: Optional list of health metrics for correlation

    Returns:
        Updated HabitStreak object with break_reasons populated

    Examples:
        Break reasons might include:
        - "Breaks often occur on Fridays (3 of 5 breaks)"
        - "Low readiness score (<70) precedes 60% of breaks"
        - "Travel days show 80% break rate"
    """
    if not habit_streak or habit_streak.total_completions < 5:
        return habit_streak

    # Get completion dates from metadata
    completion_dates_str = habit_streak.metadata.get("completion_dates", [])
    if not completion_dates_str:
        return habit_streak

    # Identify break periods (gaps longer than expected frequency)
    expected_freq = habit_streak.metadata.get("expected_frequency_days", 1)
    break_reasons = []

    # Analyze day-of-week patterns for breaks
    break_day_pattern = _analyze_day_of_week_breaks(
        habit_streak.habit_name,
        task_records,
        expected_freq
    )
    if break_day_pattern:
        break_reasons.append(break_day_pattern)

    # Analyze health correlations if available
    if health_records:
        health_pattern = _analyze_health_related_breaks(
            habit_streak.habit_name,
            task_records,
            health_records,
            expected_freq
        )
        if health_pattern:
            break_reasons.append(health_pattern)

    # Analyze task completion load correlation
    load_pattern = _analyze_task_load_breaks(
        habit_streak.habit_name,
        task_records,
        expected_freq
    )
    if load_pattern:
        break_reasons.append(load_pattern)

    # Update habit streak with break reasons
    habit_streak.break_reasons = break_reasons

    if break_reasons:
        habit_streak.evidence.append(f"Identified {len(break_reasons)} break pattern(s)")

    return habit_streak


def get_all_habit_streaks(
    task_records: List[TaskCompletionRecord],
    health_records: Optional[List[HealthMetricRecord]] = None,
    min_occurrences: int = 5,
    min_confidence: float = 0.6,
    expected_frequency: int = 1
) -> List[HabitStreak]:
    """Analyze all recurring habits and return comprehensive streak information.

    Convenience function to identify habits and analyze their streaks in one call.

    Args:
        task_records: List of task completion records
        health_records: Optional list of health metrics for break analysis
        min_occurrences: Minimum times habit must appear to be tracked
        min_confidence: Minimum confidence score for returned streaks
        expected_frequency: Expected frequency in days (1=daily, 7=weekly)

    Returns:
        List of HabitStreak objects for all identified habits

    Examples:
        Returns streaks for all daily habits like reviews, exercise, meditation
    """
    # Identify recurring habits
    habits = identify_recurring_habits(
        task_records,
        min_occurrences=min_occurrences
    )

    if not habits:
        return []

    # Analyze each habit
    habit_streaks = []
    for habit_name in habits:
        streak = analyze_habit_streak(
            habit_name=habit_name,
            task_records=task_records,
            expected_frequency_days=expected_frequency,
            min_confidence=min_confidence
        )

        if streak:
            # Analyze break reasons
            streak = analyze_streak_breaks(
                habit_streak=streak,
                task_records=task_records,
                health_records=health_records
            )
            habit_streaks.append(streak)

    # Sort by longest streak (most established habits first)
    habit_streaks.sort(key=lambda s: s.longest_streak, reverse=True)

    return habit_streaks


def _calculate_streaks(
    completion_dates: List,  # List of date objects
    expected_frequency_days: int
) -> Tuple[int, int, List[int]]:
    """Calculate current streak, longest streak, and all streak lengths.

    Args:
        completion_dates: Sorted list of completion dates
        expected_frequency_days: Expected days between completions

    Returns:
        Tuple of (current_streak_days, longest_streak_days, all_streak_lengths)
    """
    if not completion_dates:
        return 0, 0, []

    all_streaks = []
    current_streak_days = 1
    longest_streak_days = 1

    for i in range(1, len(completion_dates)):
        gap_days = (completion_dates[i] - completion_dates[i-1]).days

        if gap_days <= expected_frequency_days:
            # Streak continues
            current_streak_days += gap_days
        else:
            # Streak broken
            all_streaks.append(current_streak_days)
            longest_streak_days = max(longest_streak_days, current_streak_days)
            current_streak_days = 1

    # Don't forget the last streak
    all_streaks.append(current_streak_days)
    longest_streak_days = max(longest_streak_days, current_streak_days)

    # Current streak is the last one only if it's still active
    today = datetime.now().date()
    days_since_last = (today - completion_dates[-1]).days

    if days_since_last > expected_frequency_days:
        # Streak is broken
        final_current_streak = 0
    else:
        final_current_streak = current_streak_days

    return final_current_streak, longest_streak_days, all_streaks


def _analyze_day_of_week_breaks(
    habit_name: str,
    task_records: List[TaskCompletionRecord],
    expected_frequency: int
) -> Optional[str]:
    """Analyze if breaks correlate with specific days of the week.

    Args:
        habit_name: Name of habit to analyze
        task_records: List of task completion records
        expected_frequency: Expected days between completions

    Returns:
        String description of pattern if found, None otherwise
    """
    # Find days when habit was NOT completed
    sorted_records = sorted(task_records, key=lambda r: r.date)

    missed_days = []
    for record in sorted_records:
        if habit_name not in record.task_types or record.task_types[habit_name] == 0:
            missed_days.append(record.date.weekday())

    if len(missed_days) < 3:
        return None

    # Count misses by day of week
    day_counts = defaultdict(int)
    for day in missed_days:
        day_counts[day] += 1

    if not day_counts:
        return None

    # Find most common miss day
    most_common_day = max(day_counts.items(), key=lambda x: x[1])
    day_num, count = most_common_day

    # Check if significant (>30% of all misses)
    total_misses = len(missed_days)
    percentage = count / total_misses

    if percentage > 0.3:
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return f"Breaks often occur on {day_names[day_num]}s ({count} of {total_misses} misses, {percentage:.0%})"

    return None


def _analyze_health_related_breaks(
    habit_name: str,
    task_records: List[TaskCompletionRecord],
    health_records: List[HealthMetricRecord],
    expected_frequency: int
) -> Optional[str]:
    """Analyze if breaks correlate with poor health metrics.

    Args:
        habit_name: Name of habit to analyze
        task_records: List of task completion records
        health_records: List of health metric records
        expected_frequency: Expected days between completions

    Returns:
        String description of health correlation if found, None otherwise
    """
    if not health_records:
        return None

    # Create date-indexed health lookup
    health_by_date = {h.date.date(): h for h in health_records}

    # Find dates when habit was missed
    missed_dates = []
    for record in task_records:
        if habit_name not in record.task_types or record.task_types[habit_name] == 0:
            missed_dates.append(record.date.date())

    if len(missed_dates) < 3:
        return None

    # Check readiness scores on missed days
    readiness_on_misses = []
    for missed_date in missed_dates:
        if missed_date in health_by_date:
            health = health_by_date[missed_date]
            if health.readiness_score is not None:
                readiness_on_misses.append(health.readiness_score)

    if len(readiness_on_misses) < 3:
        return None

    # Calculate average readiness on miss days
    avg_readiness_miss = statistics.mean(readiness_on_misses)

    # Calculate overall average readiness
    all_readiness = [h.readiness_score for h in health_records if h.readiness_score is not None]
    if not all_readiness:
        return None

    avg_readiness_overall = statistics.mean(all_readiness)

    # Check if significantly lower
    if avg_readiness_miss < avg_readiness_overall - 10:  # 10 point threshold
        low_count = sum(1 for r in readiness_on_misses if r < 70)
        percentage = low_count / len(readiness_on_misses)

        if percentage > 0.5:
            return f"Low readiness score (<70) precedes {percentage:.0%} of breaks (avg {avg_readiness_miss:.0f} vs overall {avg_readiness_overall:.0f})"

    return None


def _analyze_task_load_breaks(
    habit_name: str,
    task_records: List[TaskCompletionRecord],
    expected_frequency: int
) -> Optional[str]:
    """Analyze if breaks correlate with high/low task completion load.

    Args:
        habit_name: Name of habit to analyze
        task_records: List of task completion records
        expected_frequency: Expected days between completions

    Returns:
        String description of task load correlation if found, None otherwise
    """
    # Find dates when habit was missed
    missed_records = []
    completed_records = []

    for record in task_records:
        if habit_name not in record.task_types or record.task_types[habit_name] == 0:
            missed_records.append(record)
        else:
            completed_records.append(record)

    if len(missed_records) < 3 or len(completed_records) < 3:
        return None

    # Calculate average task load on miss vs completion days
    avg_tasks_on_misses = statistics.mean([r.tasks_completed for r in missed_records])
    avg_tasks_on_completions = statistics.mean([r.tasks_completed for r in completed_records])

    # Check for significant difference (>30%)
    if avg_tasks_on_misses > avg_tasks_on_completions * 1.3:
        return f"Breaks correlate with high task load (avg {avg_tasks_on_misses:.1f} tasks on miss days vs {avg_tasks_on_completions:.1f} on completion days)"
    elif avg_tasks_on_misses < avg_tasks_on_completions * 0.7:
        return f"Breaks correlate with low task load (avg {avg_tasks_on_misses:.1f} tasks on miss days vs {avg_tasks_on_completions:.1f} on completion days)"

    return None


def _calculate_confidence(
    sample_size: int,
    consistency: float,
    min_samples: int
) -> float:
    """Calculate confidence score based on sample size and consistency.

    Args:
        sample_size: Number of data points
        consistency: Measure of habit consistency (0.0 to 1.0)
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
