"""Time-series data storage and aggregation utilities.

This module provides utilities for structuring historical data in time-series format
and performing daily, weekly, and monthly aggregations of task completions, health
metrics, and productivity scores.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import statistics


class AggregationPeriod(Enum):
    """Time period for data aggregation."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class DataPoint:
    """A single data point in a time series.

    Represents a measurement or event at a specific point in time.
    """
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure timestamp is a datetime object."""
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")


@dataclass
class TimeSeriesData:
    """Collection of data points forming a time series.

    Provides methods for querying, filtering, and analyzing temporal data.
    """
    metric_name: str
    data_points: List[DataPoint] = field(default_factory=list)
    unit: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_point(self, timestamp: datetime, value: float, metadata: Optional[Dict[str, Any]] = None):
        """Add a data point to the time series.

        Args:
            timestamp: When the measurement was taken
            value: The measured value
            metadata: Optional additional information about this data point
        """
        point = DataPoint(
            timestamp=timestamp,
            value=value,
            metadata=metadata or {}
        )
        self.data_points.append(point)

    def get_date_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get the date range covered by this time series.

        Returns:
            Tuple of (start_date, end_date) or (None, None) if empty
        """
        if not self.data_points:
            return None, None

        timestamps = [point.timestamp for point in self.data_points]
        return min(timestamps), max(timestamps)

    def filter_by_date_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> "TimeSeriesData":
        """Filter data points within a date range.

        Args:
            start_date: Include points on or after this date (None = no lower bound)
            end_date: Include points on or before this date (None = no upper bound)

        Returns:
            New TimeSeriesData with filtered points
        """
        filtered_points = []

        for point in self.data_points:
            if start_date and point.timestamp < start_date:
                continue
            if end_date and point.timestamp > end_date:
                continue
            filtered_points.append(point)

        return TimeSeriesData(
            metric_name=self.metric_name,
            data_points=filtered_points,
            unit=self.unit,
            metadata=self.metadata.copy()
        )

    def get_values(self) -> List[float]:
        """Get all values as a list.

        Returns:
            List of values in chronological order
        """
        sorted_points = sorted(self.data_points, key=lambda p: p.timestamp)
        return [point.value for point in sorted_points]

    def calculate_statistics(self) -> Dict[str, float]:
        """Calculate basic statistics for this time series.

        Returns:
            Dictionary with mean, median, min, max, std_dev
        """
        if not self.data_points:
            return {
                "mean": 0.0,
                "median": 0.0,
                "min": 0.0,
                "max": 0.0,
                "std_dev": 0.0,
                "count": 0
            }

        values = self.get_values()

        return {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "count": len(values)
        }


@dataclass
class AggregatedData:
    """Aggregated data for a specific time period.

    Contains statistical summaries and metadata for a time bucket (day/week/month).
    """
    period: AggregationPeriod
    start_date: datetime
    end_date: datetime
    metric_name: str
    count: int = 0
    sum: float = 0.0
    mean: float = 0.0
    median: float = 0.0
    min: float = 0.0
    max: float = 0.0
    std_dev: float = 0.0
    raw_values: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate statistics if raw_values are provided."""
        if self.raw_values and self.count == 0:
            self.count = len(self.raw_values)
            self.sum = sum(self.raw_values)
            self.mean = statistics.mean(self.raw_values)
            self.median = statistics.median(self.raw_values)
            self.min = min(self.raw_values)
            self.max = max(self.raw_values)
            self.std_dev = statistics.stdev(self.raw_values) if len(self.raw_values) > 1 else 0.0


@dataclass
class TaskCompletionRecord:
    """Record of task completions for time-series analysis."""
    date: datetime
    tasks_completed: int
    tasks_created: int = 0
    completion_rate: float = 0.0  # completed / (completed + pending)
    task_types: Dict[str, int] = field(default_factory=dict)  # type -> count
    completion_times: List[datetime] = field(default_factory=list)  # when tasks were completed
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_hourly_distribution(self) -> Dict[int, int]:
        """Get distribution of task completions by hour of day.

        Returns:
            Dictionary mapping hour (0-23) to count of tasks
        """
        hourly = defaultdict(int)
        for completion_time in self.completion_times:
            hour = completion_time.hour
            hourly[hour] += 1
        return dict(hourly)


@dataclass
class HealthMetricRecord:
    """Record of health metrics for time-series analysis."""
    date: datetime
    sleep_duration: Optional[float] = None  # hours
    deep_sleep_duration: Optional[float] = None  # hours
    rem_sleep_duration: Optional[float] = None  # hours
    sleep_score: Optional[float] = None  # 0-100
    readiness_score: Optional[float] = None  # 0-100
    activity_score: Optional[float] = None  # 0-100
    hrv: Optional[float] = None  # heart rate variability
    resting_heart_rate: Optional[float] = None  # bpm
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_all_metrics(self) -> Dict[str, float]:
        """Get all non-None metrics as a dictionary.

        Returns:
            Dictionary of metric_name -> value
        """
        metrics = {}
        for field_name in [
            "sleep_duration", "deep_sleep_duration", "rem_sleep_duration",
            "sleep_score", "readiness_score", "activity_score",
            "hrv", "resting_heart_rate"
        ]:
            value = getattr(self, field_name)
            if value is not None:
                metrics[field_name] = value
        return metrics


@dataclass
class ProductivityRecord:
    """Combined record of productivity metrics for time-series analysis."""
    date: datetime
    tasks_completed: int = 0
    focus_time: float = 0.0  # hours of focused work
    energy_level: Optional[float] = None  # subjective 0-10 or from health data
    productivity_score: float = 0.0  # calculated composite score
    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_productivity_score(
        self,
        tasks_weight: float = 0.5,
        focus_weight: float = 0.3,
        energy_weight: float = 0.2
    ) -> float:
        """Calculate a composite productivity score.

        Args:
            tasks_weight: Weight for task completion (0-1)
            focus_weight: Weight for focus time (0-1)
            energy_weight: Weight for energy level (0-1)

        Returns:
            Normalized productivity score (0-100)
        """
        # Normalize tasks (assume 10 tasks/day is 100%)
        tasks_normalized = min(self.tasks_completed / 10.0, 1.0) * 100

        # Normalize focus time (assume 4 hours is 100%)
        focus_normalized = min(self.focus_time / 4.0, 1.0) * 100

        # Energy is already 0-10, scale to 0-100
        energy_normalized = (self.energy_level or 5.0) * 10

        score = (
            tasks_normalized * tasks_weight +
            focus_normalized * focus_weight +
            energy_normalized * energy_weight
        )

        self.productivity_score = score
        return score


class TimeSeriesAggregator:
    """Aggregates time-series data into daily, weekly, or monthly summaries."""

    @staticmethod
    def aggregate_time_series(
        time_series: TimeSeriesData,
        period: AggregationPeriod,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AggregatedData]:
        """Aggregate time series data into specified time periods.

        Args:
            time_series: The time series to aggregate
            period: Aggregation period (daily/weekly/monthly)
            start_date: Optional start date for aggregation
            end_date: Optional end date for aggregation

        Returns:
            List of AggregatedData objects, one per time bucket
        """
        # Filter to date range if specified
        filtered = time_series.filter_by_date_range(start_date, end_date)

        if not filtered.data_points:
            return []

        # Sort data points by timestamp
        sorted_points = sorted(filtered.data_points, key=lambda p: p.timestamp)

        # Group by period
        buckets = defaultdict(list)

        for point in sorted_points:
            bucket_key = TimeSeriesAggregator._get_bucket_key(point.timestamp, period)
            buckets[bucket_key].append(point)

        # Create aggregated data for each bucket
        aggregated = []
        for bucket_key, points in sorted(buckets.items()):
            bucket_start, bucket_end = TimeSeriesAggregator._get_bucket_range(bucket_key, period)
            values = [p.value for p in points]

            agg = AggregatedData(
                period=period,
                start_date=bucket_start,
                end_date=bucket_end,
                metric_name=time_series.metric_name,
                raw_values=values
            )
            aggregated.append(agg)

        return aggregated

    @staticmethod
    def _get_bucket_key(timestamp: datetime, period: AggregationPeriod) -> str:
        """Get bucket key for grouping data points.

        Args:
            timestamp: The timestamp to bucket
            period: The aggregation period

        Returns:
            String key for the bucket (e.g., "2024-01-15" for daily)
        """
        if period == AggregationPeriod.DAILY:
            return timestamp.strftime("%Y-%m-%d")
        elif period == AggregationPeriod.WEEKLY:
            # Use ISO week number and year
            iso_year, iso_week, _ = timestamp.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        elif period == AggregationPeriod.MONTHLY:
            return timestamp.strftime("%Y-%m")
        else:
            raise ValueError(f"Unknown aggregation period: {period}")

    @staticmethod
    def _get_bucket_range(bucket_key: str, period: AggregationPeriod) -> Tuple[datetime, datetime]:
        """Get the date range for a bucket key.

        Args:
            bucket_key: The bucket key (e.g., "2024-01-15")
            period: The aggregation period

        Returns:
            Tuple of (start_datetime, end_datetime) for the bucket
        """
        if period == AggregationPeriod.DAILY:
            date = datetime.strptime(bucket_key, "%Y-%m-%d")
            return date, date + timedelta(days=1) - timedelta(microseconds=1)

        elif period == AggregationPeriod.WEEKLY:
            # Parse ISO week format "YYYY-Www"
            parts = bucket_key.split("-W")
            year = int(parts[0])
            week = int(parts[1])

            # Get first day of the ISO week
            jan4 = datetime(year, 1, 4)
            week_one_monday = jan4 - timedelta(days=jan4.weekday())
            week_start = week_one_monday + timedelta(weeks=week - 1)
            week_end = week_start + timedelta(days=7) - timedelta(microseconds=1)

            return week_start, week_end

        elif period == AggregationPeriod.MONTHLY:
            date = datetime.strptime(bucket_key + "-01", "%Y-%m-%d")
            # Get last day of month
            if date.month == 12:
                next_month = datetime(date.year + 1, 1, 1)
            else:
                next_month = datetime(date.year, date.month + 1, 1)
            month_end = next_month - timedelta(microseconds=1)

            return date, month_end

        else:
            raise ValueError(f"Unknown aggregation period: {period}")

    @staticmethod
    def aggregate_task_completions(
        records: List[TaskCompletionRecord],
        period: AggregationPeriod
    ) -> List[AggregatedData]:
        """Aggregate task completion records.

        Args:
            records: List of task completion records
            period: Aggregation period

        Returns:
            List of aggregated data for task completions
        """
        # Convert to time series
        ts = TimeSeriesData(metric_name="tasks_completed", unit="tasks")
        for record in records:
            ts.add_point(
                timestamp=record.date,
                value=float(record.tasks_completed),
                metadata={"task_types": record.task_types}
            )

        return TimeSeriesAggregator.aggregate_time_series(ts, period)

    @staticmethod
    def aggregate_health_metrics(
        records: List[HealthMetricRecord],
        metric_name: str,
        period: AggregationPeriod
    ) -> List[AggregatedData]:
        """Aggregate health metric records.

        Args:
            records: List of health metric records
            metric_name: Which metric to aggregate (e.g., "sleep_duration", "readiness_score")
            period: Aggregation period

        Returns:
            List of aggregated data for the specified metric
        """
        # Convert to time series
        ts = TimeSeriesData(metric_name=metric_name)
        for record in records:
            value = getattr(record, metric_name, None)
            if value is not None:
                ts.add_point(timestamp=record.date, value=float(value))

        return TimeSeriesAggregator.aggregate_time_series(ts, period)

    @staticmethod
    def aggregate_productivity_scores(
        records: List[ProductivityRecord],
        period: AggregationPeriod
    ) -> List[AggregatedData]:
        """Aggregate productivity score records.

        Args:
            records: List of productivity records
            period: Aggregation period

        Returns:
            List of aggregated data for productivity scores
        """
        # Convert to time series
        ts = TimeSeriesData(metric_name="productivity_score", unit="score")
        for record in records:
            ts.add_point(
                timestamp=record.date,
                value=record.productivity_score,
                metadata={
                    "tasks": record.tasks_completed,
                    "focus_time": record.focus_time,
                    "energy": record.energy_level
                }
            )

        return TimeSeriesAggregator.aggregate_time_series(ts, period)


def create_time_series_from_dict(
    metric_name: str,
    data: Dict[datetime, float],
    unit: str = ""
) -> TimeSeriesData:
    """Helper function to create a TimeSeriesData from a dictionary.

    Args:
        metric_name: Name of the metric
        data: Dictionary mapping datetime to value
        unit: Optional unit of measurement

    Returns:
        TimeSeriesData object populated with the data
    """
    ts = TimeSeriesData(metric_name=metric_name, unit=unit)
    for timestamp, value in data.items():
        ts.add_point(timestamp, value)
    return ts


def merge_time_series(
    time_series_list: List[TimeSeriesData],
    metric_name: str
) -> TimeSeriesData:
    """Merge multiple time series into one.

    Useful for combining data from different sources.

    Args:
        time_series_list: List of time series to merge
        metric_name: Name for the merged time series

    Returns:
        New TimeSeriesData with all data points combined
    """
    merged = TimeSeriesData(metric_name=metric_name)

    for ts in time_series_list:
        merged.data_points.extend(ts.data_points)

    # Sort by timestamp
    merged.data_points.sort(key=lambda p: p.timestamp)

    return merged
