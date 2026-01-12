"""
Task completion pattern analyzer.

Analyzes task completion patterns to identify:
- Most productive times of day
- Day of week performance variations
- Task type completion timing patterns
- Average daily completion rates
"""

from collections import defaultdict
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple

from ..models import TaskCompletionPattern
from ..data_aggregator import AggregatedData, TaskCompletionRecord
from ..time_series import TimeSeries, AggregationPeriod


class TaskPatternAnalyzer:
    """
    Analyzes task completion patterns from historical data.

    This analyzer examines when and how tasks are completed to identify
    patterns in productivity, timing preferences, and task type distributions.
    """

    def __init__(self, min_data_points: int = 10, min_confidence: float = 0.6):
        """
        Initialize the task pattern analyzer.

        Args:
            min_data_points: Minimum number of data points required for pattern detection
            min_confidence: Minimum confidence threshold for reporting patterns
        """
        self.min_data_points = min_data_points
        self.min_confidence = min_confidence

    def analyze(
        self,
        aggregated_data: AggregatedData,
        time_series: Optional[TimeSeries] = None
    ) -> List[TaskCompletionPattern]:
        """
        Analyze all task completion patterns from the data.

        Args:
            aggregated_data: Historical task completion records
            time_series: Optional pre-built time series data

        Returns:
            List of detected TaskCompletionPattern objects
        """
        patterns = []

        # Ensure we have enough data
        if len(aggregated_data.task_completions) < self.min_data_points:
            return patterns

        # Analyze different pattern types
        patterns.extend(self._analyze_time_of_day(aggregated_data))
        patterns.extend(self._analyze_day_of_week(aggregated_data))
        patterns.extend(self._analyze_task_type_timing(aggregated_data))
        patterns.extend(self._analyze_daily_completion_rate(aggregated_data, time_series))

        # Filter by confidence threshold
        patterns = [p for p in patterns if p.confidence_score >= self.min_confidence]

        return patterns

    def _analyze_time_of_day(
        self, aggregated_data: AggregatedData
    ) -> List[TaskCompletionPattern]:
        """
        Analyze task completion patterns by hour of day.

        Identifies peak productivity hours (e.g., "most productive 9-11am").

        Args:
            aggregated_data: Historical task completion data

        Returns:
            List of time-of-day patterns
        """
        patterns = []

        # Note: We don't have hour-level completion data in the current data structure
        # Task completions only have dates, not times
        # This would need enhancement to track completion timestamps

        # For now, we'll return an empty list with a note in metadata
        # Future enhancement: Store completion timestamps in TaskCompletionRecord

        return patterns

    def _analyze_day_of_week(
        self, aggregated_data: AggregatedData
    ) -> List[TaskCompletionPattern]:
        """
        Analyze task completion patterns by day of week.

        Identifies which days are most/least productive (e.g., "Mondays are slowest").

        Args:
            aggregated_data: Historical task completion data

        Returns:
            List of day-of-week patterns
        """
        patterns = []

        if not aggregated_data.task_completions:
            return patterns

        # Count completions by day of week (0=Monday, 6=Sunday)
        completions_by_day: Dict[int, List[TaskCompletionRecord]] = defaultdict(list)

        for task in aggregated_data.task_completions:
            day_of_week = task.completed_date.weekday()
            completions_by_day[day_of_week].append(task)

        # Calculate average completions per day of week
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_averages = {}

        for day_num in range(7):
            if day_num in completions_by_day:
                # Count unique dates to get average per occurrence
                unique_dates = set(task.completed_date for task in completions_by_day[day_num])
                total_tasks = len(completions_by_day[day_num])
                avg_per_day = total_tasks / len(unique_dates) if unique_dates else 0
                day_averages[day_num] = avg_per_day
            else:
                day_averages[day_num] = 0.0

        # Only proceed if we have data for multiple days
        days_with_data = sum(1 for avg in day_averages.values() if avg > 0)
        if days_with_data < 2:
            return patterns

        # Find most and least productive days
        max_day = max(day_averages.items(), key=lambda x: x[1])
        min_day = min(((k, v) for k, v in day_averages.items() if v > 0), key=lambda x: x[1])

        overall_avg = sum(day_averages.values()) / len([v for v in day_averages.values() if v > 0])

        # Calculate date range
        all_dates = [task.completed_date for task in aggregated_data.task_completions]
        start_date = min(all_dates)
        end_date = max(all_dates)

        # Most productive day pattern
        if max_day[1] > 0:
            percent_above = ((max_day[1] - overall_avg) / overall_avg * 100) if overall_avg > 0 else 0

            # Calculate confidence based on sample size and effect size
            sample_size = len(completions_by_day[max_day[0]])
            confidence = min(0.95, (sample_size / 50) * 0.5 + (min(abs(percent_above), 50) / 50) * 0.5)

            if abs(percent_above) >= 10:  # Only report if >= 10% difference
                patterns.append(TaskCompletionPattern(
                    pattern_type="day_of_week",
                    description=f"{day_names[max_day[0]]}s are your most productive day "
                                f"({max_day[1]:.1f} tasks/day avg, {percent_above:+.0f}% vs average)",
                    confidence_score=confidence,
                    start_date=start_date,
                    end_date=end_date,
                    evidence={
                        "day_of_week": day_names[max_day[0]],
                        "avg_completions": max_day[1],
                        "overall_avg": overall_avg,
                        "percent_difference": percent_above,
                        "sample_size": len(completions_by_day[max_day[0]]),
                        "unique_occurrences": len(set(t.completed_date for t in completions_by_day[max_day[0]])),
                        "all_day_averages": {day_names[k]: v for k, v in day_averages.items()}
                    },
                    metadata={"direction": "high"}
                ))

        # Least productive day pattern
        if min_day[1] > 0 and min_day[0] != max_day[0]:
            percent_below = ((min_day[1] - overall_avg) / overall_avg * 100) if overall_avg > 0 else 0

            sample_size = len(completions_by_day[min_day[0]])
            confidence = min(0.95, (sample_size / 50) * 0.5 + (min(abs(percent_below), 50) / 50) * 0.5)

            if abs(percent_below) >= 10:  # Only report if >= 10% difference
                patterns.append(TaskCompletionPattern(
                    pattern_type="day_of_week",
                    description=f"{day_names[min_day[0]]}s are your least productive day "
                                f"({min_day[1]:.1f} tasks/day avg, {percent_below:+.0f}% vs average)",
                    confidence_score=confidence,
                    start_date=start_date,
                    end_date=end_date,
                    evidence={
                        "day_of_week": day_names[min_day[0]],
                        "avg_completions": min_day[1],
                        "overall_avg": overall_avg,
                        "percent_difference": percent_below,
                        "sample_size": len(completions_by_day[min_day[0]]),
                        "unique_occurrences": len(set(t.completed_date for t in completions_by_day[min_day[0]])),
                        "all_day_averages": {day_names[k]: v for k, v in day_averages.items()}
                    },
                    metadata={"direction": "low"}
                ))

        return patterns

    def _analyze_task_type_timing(
        self, aggregated_data: AggregatedData
    ) -> List[TaskCompletionPattern]:
        """
        Analyze when different types of tasks are typically completed.

        Identifies task domain preferences by day of week
        (e.g., "Work tasks primarily on weekdays, personal on weekends").

        Args:
            aggregated_data: Historical task completion data

        Returns:
            List of task type timing patterns
        """
        patterns = []

        if not aggregated_data.task_completions:
            return patterns

        # Group tasks by domain and day type (weekday vs weekend)
        domain_by_day_type: Dict[str, Dict[str, List[TaskCompletionRecord]]] = defaultdict(
            lambda: {"weekday": [], "weekend": []}
        )

        for task in aggregated_data.task_completions:
            day_of_week = task.completed_date.weekday()
            day_type = "weekend" if day_of_week >= 5 else "weekday"
            domain_by_day_type[task.domain][day_type].append(task)

        # Analyze each domain
        all_dates = [task.completed_date for task in aggregated_data.task_completions]
        start_date = min(all_dates)
        end_date = max(all_dates)

        for domain, day_types in domain_by_day_type.items():
            weekday_count = len(day_types["weekday"])
            weekend_count = len(day_types["weekend"])
            total_count = weekday_count + weekend_count

            if total_count < self.min_data_points:
                continue

            weekday_ratio = weekday_count / total_count if total_count > 0 else 0
            weekend_ratio = weekend_count / total_count if total_count > 0 else 0

            # If strongly skewed toward weekdays or weekends (>75%)
            if weekday_ratio >= 0.75:
                confidence = min(0.95, (total_count / 50) * 0.6 + weekday_ratio * 0.4)

                patterns.append(TaskCompletionPattern(
                    pattern_type="task_type_timing",
                    description=f"{domain.capitalize()} tasks are primarily completed on weekdays "
                                f"({weekday_ratio*100:.0f}% of {total_count} tasks)",
                    confidence_score=confidence,
                    start_date=start_date,
                    end_date=end_date,
                    evidence={
                        "domain": domain,
                        "weekday_count": weekday_count,
                        "weekend_count": weekend_count,
                        "weekday_ratio": weekday_ratio,
                        "total_tasks": total_count
                    },
                    metadata={"preference": "weekday"}
                ))

            elif weekend_ratio >= 0.75:
                confidence = min(0.95, (total_count / 50) * 0.6 + weekend_ratio * 0.4)

                patterns.append(TaskCompletionPattern(
                    pattern_type="task_type_timing",
                    description=f"{domain.capitalize()} tasks are primarily completed on weekends "
                                f"({weekend_ratio*100:.0f}% of {total_count} tasks)",
                    confidence_score=confidence,
                    start_date=start_date,
                    end_date=end_date,
                    evidence={
                        "domain": domain,
                        "weekday_count": weekday_count,
                        "weekend_count": weekend_count,
                        "weekend_ratio": weekend_ratio,
                        "total_tasks": total_count
                    },
                    metadata={"preference": "weekend"}
                ))

        return patterns

    def _analyze_daily_completion_rate(
        self,
        aggregated_data: AggregatedData,
        time_series: Optional[TimeSeries] = None
    ) -> List[TaskCompletionPattern]:
        """
        Analyze average daily task completion rate.

        Calculates overall productivity baseline (e.g., "Average 4.2 tasks per day").

        Args:
            aggregated_data: Historical task completion data
            time_series: Optional pre-built time series for more accurate daily rates

        Returns:
            List of completion rate patterns
        """
        patterns = []

        if not aggregated_data.task_completions:
            return patterns

        # Calculate using time series if available, otherwise use simple calculation
        if time_series and time_series.data_points:
            # Use time series for accurate daily counts
            daily_counts = [point.tasks_completed for point in time_series.data_points]
            days_with_data = len([c for c in daily_counts if c > 0])
            total_tasks = sum(daily_counts)
            avg_per_day = total_tasks / len(daily_counts) if daily_counts else 0

            start_date = time_series.start_date
            end_date = time_series.end_date
        else:
            # Simple calculation from aggregated data
            all_dates = [task.completed_date for task in aggregated_data.task_completions]
            unique_dates = set(all_dates)
            days_with_data = len(unique_dates)
            total_tasks = len(aggregated_data.task_completions)

            start_date = min(all_dates)
            end_date = max(all_dates)

            # Calculate average
            total_days = (end_date - start_date).days + 1
            avg_per_day = total_tasks / total_days if total_days > 0 else 0

        if days_with_data < 3:  # Need at least 3 days of data
            return patterns

        # Calculate confidence based on sample size
        confidence = min(0.95, days_with_data / 30)  # Max confidence at 30+ days

        # Calculate task points if available
        total_points = sum(task.points for task in aggregated_data.task_completions if task.points)
        has_points = any(task.points for task in aggregated_data.task_completions)

        description_parts = [f"Average of {avg_per_day:.1f} tasks completed per day"]
        if has_points and total_points > 0:
            total_days = (end_date - start_date).days + 1
            avg_points = total_points / total_days if total_days > 0 else 0
            description_parts.append(f"({avg_points:.0f} points/day)")

        patterns.append(TaskCompletionPattern(
            pattern_type="daily_completion_rate",
            description=" ".join(description_parts),
            confidence_score=confidence,
            start_date=start_date,
            end_date=end_date,
            evidence={
                "avg_tasks_per_day": avg_per_day,
                "total_tasks": total_tasks,
                "days_analyzed": days_with_data,
                "total_points": total_points if has_points else None,
                "avg_points_per_day": total_points / days_with_data if has_points and days_with_data > 0 else None,
                "date_range_days": (end_date - start_date).days + 1
            },
            metadata={
                "baseline": True,
                "has_points_data": has_points
            }
        ))

        return patterns

    def get_completion_statistics(
        self, aggregated_data: AggregatedData
    ) -> Dict[str, any]:
        """
        Get general task completion statistics.

        Args:
            aggregated_data: Historical task completion data

        Returns:
            Dictionary containing various statistics about task completions
        """
        if not aggregated_data.task_completions:
            return {
                "total_tasks": 0,
                "unique_days": 0,
                "avg_per_day": 0.0,
                "domains": {},
                "date_range": None
            }

        all_dates = [task.completed_date for task in aggregated_data.task_completions]
        unique_dates = set(all_dates)

        # Count by domain
        domain_counts = defaultdict(int)
        for task in aggregated_data.task_completions:
            domain_counts[task.domain] += 1

        # Calculate averages
        total_tasks = len(aggregated_data.task_completions)
        total_days = (max(all_dates) - min(all_dates)).days + 1
        avg_per_day = total_tasks / total_days if total_days > 0 else 0

        return {
            "total_tasks": total_tasks,
            "unique_days": len(unique_dates),
            "total_days_in_range": total_days,
            "avg_per_day": avg_per_day,
            "domains": dict(domain_counts),
            "date_range": (min(all_dates), max(all_dates)),
            "start_date": min(all_dates).isoformat(),
            "end_date": max(all_dates).isoformat()
        }
