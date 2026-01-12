"""
Time-series data utilities for pattern recognition.

Structures historical data in time-series format for analysis. Supports
daily, weekly, and monthly aggregations of task completions, health metrics,
and productivity scores.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .data_aggregator import (
    AggregatedData,
    TaskCompletionRecord,
    HealthMetrics,
    CommitmentRecord,
    SessionRecord,
)


class AggregationPeriod(Enum):
    """Supported time-series aggregation periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class TimeSeriesPoint:
    """
    Single point in a time series.

    Represents aggregated data for a specific time period (day, week, or month).
    """
    period_start: date
    period_end: date
    period_type: AggregationPeriod

    # Task completion metrics
    tasks_completed: int = 0
    task_points: int = 0
    tasks_by_domain: Dict[str, int] = field(default_factory=dict)

    # Health metrics (averages for the period)
    avg_readiness_score: Optional[float] = None
    avg_sleep_score: Optional[float] = None
    avg_activity_score: Optional[float] = None
    avg_sleep_duration: Optional[float] = None  # hours
    avg_deep_sleep: Optional[float] = None  # hours
    avg_rem_sleep: Optional[float] = None  # hours
    avg_hrv: Optional[float] = None
    avg_resting_hr: Optional[int] = None
    avg_steps: Optional[int] = None

    # Commitment metrics
    commitments_created: int = 0
    commitments_completed: int = 0
    commitments_by_status: Dict[str, int] = field(default_factory=dict)

    # Session metrics
    sessions_count: int = 0
    avg_energy_level: Optional[float] = None
    total_session_minutes: int = 0

    # Productivity score (composite metric)
    productivity_score: Optional[float] = None

    # Raw data counts for statistical significance
    health_data_points: int = 0
    task_data_points: int = 0

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeSeries:
    """
    Complete time series with aggregated data points.

    Contains chronologically ordered data points and metadata about the series.
    """
    period_type: AggregationPeriod
    start_date: date
    end_date: date
    data_points: List[TimeSeriesPoint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_metric_series(self, metric_name: str) -> List[tuple[date, Optional[float]]]:
        """
        Extract a specific metric as a simple (date, value) series.

        Args:
            metric_name: Name of the metric to extract (e.g., "productivity_score", "avg_readiness_score")

        Returns:
            List of (period_start, value) tuples
        """
        series = []
        for point in self.data_points:
            value = getattr(point, metric_name, None)
            series.append((point.period_start, value))
        return series

    def get_points_in_range(self, start: date, end: date) -> List[TimeSeriesPoint]:
        """
        Get all data points within a specific date range.

        Args:
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            Filtered list of TimeSeriesPoint objects
        """
        return [
            point for point in self.data_points
            if start <= point.period_start <= end
        ]

    def filter_by_condition(
        self, condition: Callable[[TimeSeriesPoint], bool]
    ) -> List[TimeSeriesPoint]:
        """
        Filter data points by a custom condition.

        Args:
            condition: Function that takes a TimeSeriesPoint and returns bool

        Returns:
            Filtered list of TimeSeriesPoint objects

        Example:
            # Get all points with high productivity
            high_prod = series.filter_by_condition(
                lambda p: p.productivity_score and p.productivity_score > 0.8
            )
        """
        return [point for point in self.data_points if condition(point)]


class TimeSeriesBuilder:
    """
    Builder for creating time-series data from aggregated historical data.

    Takes raw AggregatedData and structures it into time-series format
    with support for different aggregation periods (daily, weekly, monthly).
    """

    def __init__(self, aggregated_data: AggregatedData):
        """
        Initialize the builder with historical data.

        Args:
            aggregated_data: Historical data from DataAggregator
        """
        self.data = aggregated_data

    def build(
        self,
        period: AggregationPeriod = AggregationPeriod.DAILY,
        calculate_productivity_score: bool = True
    ) -> TimeSeries:
        """
        Build a time series with the specified aggregation period.

        Args:
            period: Aggregation period (daily, weekly, or monthly)
            calculate_productivity_score: Whether to calculate composite productivity score

        Returns:
            TimeSeries object with aggregated data points
        """
        if not self.data.date_range:
            # No date range specified - use data to infer range
            start_date, end_date = self._infer_date_range()
        else:
            start_date, end_date = self.data.date_range

        # Generate period boundaries
        periods = self._generate_periods(start_date, end_date, period)

        # Create data points for each period
        data_points = []
        for period_start, period_end in periods:
            point = self._create_data_point(
                period_start, period_end, period, calculate_productivity_score
            )
            data_points.append(point)

        return TimeSeries(
            period_type=period,
            start_date=start_date,
            end_date=end_date,
            data_points=data_points,
            metadata={
                "total_periods": len(data_points),
                "source_data_ranges": {
                    "tasks": len(self.data.task_completions),
                    "health_metrics": len(self.data.health_metrics),
                    "commitments": len(self.data.commitments),
                    "sessions": len(self.data.sessions)
                }
            }
        )

    def _infer_date_range(self) -> tuple[date, date]:
        """Infer date range from available data."""
        all_dates = []

        # Collect dates from all data sources
        for task in self.data.task_completions:
            all_dates.append(task.completed_date)

        for health in self.data.health_metrics:
            all_dates.append(health.date)

        for session in self.data.sessions:
            all_dates.append(session.start_time.date())

        if not all_dates:
            # No data - use today as fallback
            today = date.today()
            return today, today

        return min(all_dates), max(all_dates)

    def _generate_periods(
        self, start_date: date, end_date: date, period: AggregationPeriod
    ) -> List[tuple[date, date]]:
        """
        Generate list of (start, end) date tuples for each period.

        Args:
            start_date: Overall start date
            end_date: Overall end date
            period: Aggregation period type

        Returns:
            List of (period_start, period_end) tuples
        """
        periods = []
        current = start_date

        while current <= end_date:
            if period == AggregationPeriod.DAILY:
                period_start = current
                period_end = current
                current = current + timedelta(days=1)

            elif period == AggregationPeriod.WEEKLY:
                # Week starts on Monday (ISO calendar)
                period_start = current - timedelta(days=current.weekday())
                period_end = period_start + timedelta(days=6)
                # Clamp to end_date
                period_end = min(period_end, end_date)
                current = period_end + timedelta(days=1)

            elif period == AggregationPeriod.MONTHLY:
                period_start = current.replace(day=1)
                # Last day of month
                if period_start.month == 12:
                    next_month = period_start.replace(year=period_start.year + 1, month=1)
                else:
                    next_month = period_start.replace(month=period_start.month + 1)
                period_end = next_month - timedelta(days=1)
                # Clamp to end_date
                period_end = min(period_end, end_date)
                current = period_end + timedelta(days=1)

            periods.append((period_start, period_end))

        return periods

    def _create_data_point(
        self,
        period_start: date,
        period_end: date,
        period_type: AggregationPeriod,
        calculate_productivity: bool
    ) -> TimeSeriesPoint:
        """
        Create a single time-series data point for the given period.

        Aggregates all data within the period into a single point.
        """
        point = TimeSeriesPoint(
            period_start=period_start,
            period_end=period_end,
            period_type=period_type
        )

        # Aggregate task completions
        self._aggregate_tasks(point, period_start, period_end)

        # Aggregate health metrics
        self._aggregate_health(point, period_start, period_end)

        # Aggregate commitments
        self._aggregate_commitments(point, period_start, period_end)

        # Aggregate sessions
        self._aggregate_sessions(point, period_start, period_end)

        # Calculate productivity score if requested
        if calculate_productivity:
            point.productivity_score = self._calculate_productivity_score(point)

        return point

    def _aggregate_tasks(
        self, point: TimeSeriesPoint, start: date, end: date
    ) -> None:
        """Aggregate task completion data for the period."""
        tasks_in_period = [
            task for task in self.data.task_completions
            if start <= task.completed_date <= end
        ]

        point.tasks_completed = len(tasks_in_period)
        point.task_data_points = len(tasks_in_period)

        # Sum points
        total_points = 0
        for task in tasks_in_period:
            if task.points:
                total_points += task.points
        point.task_points = total_points

        # Count by domain
        domain_counts: Dict[str, int] = defaultdict(int)
        for task in tasks_in_period:
            domain_counts[task.domain] += 1
        point.tasks_by_domain = dict(domain_counts)

    def _aggregate_health(
        self, point: TimeSeriesPoint, start: date, end: date
    ) -> None:
        """Aggregate health metrics for the period (averages)."""
        metrics_in_period = [
            metric for metric in self.data.health_metrics
            if start <= metric.date <= end
        ]

        if not metrics_in_period:
            return

        point.health_data_points = len(metrics_in_period)

        # Calculate averages for each metric
        def avg(values: List[Optional[float]]) -> Optional[float]:
            """Calculate average of non-None values."""
            valid = [v for v in values if v is not None]
            return sum(valid) / len(valid) if valid else None

        point.avg_readiness_score = avg([m.readiness_score for m in metrics_in_period])
        point.avg_sleep_score = avg([m.sleep_score for m in metrics_in_period])
        point.avg_activity_score = avg([m.activity_score for m in metrics_in_period])

        # Convert sleep durations from minutes to hours
        sleep_durations = [
            m.total_sleep_duration / 60.0 if m.total_sleep_duration else None
            for m in metrics_in_period
        ]
        point.avg_sleep_duration = avg(sleep_durations)

        deep_sleep = [
            m.deep_sleep_duration / 60.0 if m.deep_sleep_duration else None
            for m in metrics_in_period
        ]
        point.avg_deep_sleep = avg(deep_sleep)

        rem_sleep = [
            m.rem_sleep_duration / 60.0 if m.rem_sleep_duration else None
            for m in metrics_in_period
        ]
        point.avg_rem_sleep = avg(rem_sleep)

        point.avg_hrv = avg([m.hrv_average for m in metrics_in_period])
        point.avg_resting_hr = avg([m.resting_heart_rate for m in metrics_in_period])
        point.avg_steps = avg([m.steps for m in metrics_in_period])

    def _aggregate_commitments(
        self, point: TimeSeriesPoint, start: date, end: date
    ) -> None:
        """Aggregate commitment data for the period."""
        # Count commitments created in this period
        created_in_period = []
        completed_in_period = []
        status_counts: Dict[str, int] = defaultdict(int)

        for commitment in self.data.commitments:
            # Check if created in period
            if commitment.created_at:
                try:
                    from datetime import datetime
                    created_date = datetime.fromisoformat(commitment.created_at).date()
                    if start <= created_date <= end:
                        created_in_period.append(commitment)
                except (ValueError, AttributeError):
                    pass

            # Check if completed in period
            if commitment.completed_at:
                try:
                    from datetime import datetime
                    completed_date = datetime.fromisoformat(commitment.completed_at).date()
                    if start <= completed_date <= end:
                        completed_in_period.append(commitment)
                except (ValueError, AttributeError):
                    pass

            # Count by status (all commitments, not just in period)
            status_counts[commitment.status] += 1

        point.commitments_created = len(created_in_period)
        point.commitments_completed = len(completed_in_period)
        point.commitments_by_status = dict(status_counts)

    def _aggregate_sessions(
        self, point: TimeSeriesPoint, start: date, end: date
    ) -> None:
        """Aggregate session data for the period."""
        sessions_in_period = [
            session for session in self.data.sessions
            if start <= session.start_time.date() <= end
        ]

        if not sessions_in_period:
            return

        point.sessions_count = len(sessions_in_period)

        # Average energy level
        energy_levels = [
            s.energy_level for s in sessions_in_period
            if s.energy_level is not None
        ]
        if energy_levels:
            point.avg_energy_level = sum(energy_levels) / len(energy_levels)

        # Total session time
        total_minutes = sum(
            s.duration_minutes for s in sessions_in_period
            if s.duration_minutes is not None
        )
        point.total_session_minutes = total_minutes

    def _calculate_productivity_score(self, point: TimeSeriesPoint) -> Optional[float]:
        """
        Calculate composite productivity score for a time period.

        Combines multiple factors:
        - Task completions (normalized)
        - Task points (if available)
        - Session energy levels
        - Health metrics (readiness, sleep quality)

        Returns score between 0.0 and 1.0, or None if insufficient data.
        """
        scores = []

        # Task completion score (0-1)
        # Normalize based on typical daily task count (assume 5 tasks/day is 1.0)
        if point.tasks_completed > 0:
            days_in_period = (point.period_end - point.period_start).days + 1
            expected_tasks = days_in_period * 5  # 5 tasks/day baseline
            task_score = min(1.0, point.tasks_completed / expected_tasks)
            scores.append(("tasks", task_score, 0.3))  # 30% weight

        # Health score (average of readiness and sleep scores, normalized to 0-1)
        health_components = []
        if point.avg_readiness_score:
            health_components.append(point.avg_readiness_score / 100.0)
        if point.avg_sleep_score:
            health_components.append(point.avg_sleep_score / 100.0)

        if health_components:
            health_score = sum(health_components) / len(health_components)
            scores.append(("health", health_score, 0.3))  # 30% weight

        # Energy score (normalize 1-10 scale to 0-1)
        if point.avg_energy_level:
            energy_score = (point.avg_energy_level - 1) / 9.0  # Map 1-10 to 0-1
            scores.append(("energy", energy_score, 0.2))  # 20% weight

        # Commitment completion score
        if point.commitments_created > 0:
            completion_rate = point.commitments_completed / point.commitments_created
            scores.append(("commitments", completion_rate, 0.2))  # 20% weight

        if not scores:
            return None

        # Calculate weighted average
        total_weight = sum(weight for _, _, weight in scores)
        weighted_sum = sum(score * weight for _, score, weight in scores)

        final_score = weighted_sum / total_weight

        # Store breakdown in metadata
        point.metadata["productivity_breakdown"] = {
            name: score for name, score, _ in scores
        }
        point.metadata["productivity_weights"] = {
            name: weight for name, _, weight in scores
        }

        return final_score


def build_time_series(
    aggregated_data: AggregatedData,
    period: AggregationPeriod = AggregationPeriod.DAILY
) -> TimeSeries:
    """
    Convenience function to build a time series from aggregated data.

    Args:
        aggregated_data: Historical data from DataAggregator
        period: Aggregation period (daily, weekly, or monthly)

    Returns:
        TimeSeries object with aggregated data points

    Example:
        # Build daily time series
        aggregator = DataAggregator()
        data = await aggregator.aggregate_data(days_back=30)
        daily_series = build_time_series(data, AggregationPeriod.DAILY)

        # Build weekly time series
        weekly_series = build_time_series(data, AggregationPeriod.WEEKLY)
    """
    builder = TimeSeriesBuilder(aggregated_data)
    return builder.build(period=period)
