"""
Health correlation analyzer.

Analyzes correlations between health metrics (from Oura Ring) and productivity/behavior:
- Sleep duration vs tasks completed
- Readiness score vs productivity
- Deep sleep vs next-day focus
- Sleep timing vs morning energy
"""

from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import statistics

from ..models import HealthCorrelation
from ..data_aggregator import AggregatedData, HealthMetrics
from ..time_series import TimeSeries, TimeSeriesPoint


class HealthCorrelationAnalyzer:
    """
    Analyzes correlations between health metrics and productivity.

    This analyzer examines relationships between Oura Ring health data
    (sleep, readiness, activity) and productivity metrics (task completion,
    energy levels, focus) to identify actionable patterns.
    """

    def __init__(self, min_data_points: int = 7, min_confidence: float = 0.6):
        """
        Initialize the health correlation analyzer.

        Args:
            min_data_points: Minimum number of paired data points for correlation
            min_confidence: Minimum confidence threshold for reporting correlations
        """
        self.min_data_points = min_data_points
        self.min_confidence = min_confidence

    def analyze(
        self,
        aggregated_data: AggregatedData,
        time_series: Optional[TimeSeries] = None
    ) -> List[HealthCorrelation]:
        """
        Analyze all health-productivity correlations from the data.

        Args:
            aggregated_data: Historical health and productivity data
            time_series: Optional pre-built time series data

        Returns:
            List of detected HealthCorrelation objects
        """
        correlations = []

        # Ensure we have enough health data
        if len(aggregated_data.health_metrics) < self.min_data_points:
            return correlations

        # Analyze different correlation types
        correlations.extend(self._analyze_sleep_duration_vs_tasks(aggregated_data, time_series))
        correlations.extend(self._analyze_readiness_vs_productivity(aggregated_data, time_series))
        correlations.extend(self._analyze_deep_sleep_vs_focus(aggregated_data, time_series))
        correlations.extend(self._analyze_sleep_score_vs_tasks(aggregated_data, time_series))

        # Filter by confidence threshold
        correlations = [c for c in correlations if c.confidence_score >= self.min_confidence]

        return correlations

    def _analyze_sleep_duration_vs_tasks(
        self,
        aggregated_data: AggregatedData,
        time_series: Optional[TimeSeries] = None
    ) -> List[HealthCorrelation]:
        """
        Correlate sleep duration with task completion.

        Examines whether more sleep leads to more tasks completed the next day.

        Args:
            aggregated_data: Historical data
            time_series: Optional time series

        Returns:
            List of sleep duration correlations
        """
        correlations = []

        # Build paired data: sleep duration on day N -> tasks completed on day N+1
        paired_data = self._pair_health_with_next_day_tasks(
            aggregated_data, "total_sleep_duration"
        )

        if len(paired_data) < self.min_data_points:
            return correlations

        # Extract values and convert sleep from minutes to hours
        sleep_hours = [duration / 60.0 for duration, _ in paired_data]
        task_counts = [tasks for _, tasks in paired_data]

        # Calculate Pearson correlation
        correlation_coef = self._pearson_correlation(sleep_hours, task_counts)

        if correlation_coef is None:
            return correlations

        # Calculate confidence based on sample size and correlation strength
        confidence = self._calculate_confidence(len(paired_data), abs(correlation_coef))

        # Determine date range
        start_date, end_date = self._get_date_range(aggregated_data.health_metrics)

        # Generate human-readable description
        description = self._generate_sleep_duration_description(
            correlation_coef, sleep_hours, task_counts
        )

        correlations.append(HealthCorrelation(
            health_metric="sleep_duration",
            productivity_metric="tasks_completed",
            correlation_coefficient=correlation_coef,
            description=description,
            confidence_score=confidence,
            start_date=start_date,
            end_date=end_date,
            sample_size=len(paired_data),
            evidence={
                "avg_sleep_hours": statistics.mean(sleep_hours),
                "avg_tasks": statistics.mean(task_counts),
                "sleep_range": (min(sleep_hours), max(sleep_hours)),
                "tasks_range": (min(task_counts), max(task_counts)),
                "correlation_strength": self._correlation_strength_label(correlation_coef)
            },
            metadata={"analysis_type": "next_day_impact"}
        ))

        return correlations

    def _analyze_readiness_vs_productivity(
        self,
        aggregated_data: AggregatedData,
        time_series: Optional[TimeSeries] = None
    ) -> List[HealthCorrelation]:
        """
        Correlate readiness score with productivity score.

        Examines whether higher readiness scores lead to higher productivity.

        Args:
            aggregated_data: Historical data
            time_series: Optional time series

        Returns:
            List of readiness correlations
        """
        correlations = []

        # Use time series if available (has productivity scores)
        if not time_series or not time_series.data_points:
            return correlations

        # Build paired data: readiness score -> productivity score (same day)
        paired_data = []
        for point in time_series.data_points:
            if (point.avg_readiness_score is not None and
                point.productivity_score is not None):
                paired_data.append((point.avg_readiness_score, point.productivity_score))

        if len(paired_data) < self.min_data_points:
            return correlations

        readiness_scores = [r for r, _ in paired_data]
        productivity_scores = [p for _, p in paired_data]

        # Calculate correlation
        correlation_coef = self._pearson_correlation(readiness_scores, productivity_scores)

        if correlation_coef is None:
            return correlations

        confidence = self._calculate_confidence(len(paired_data), abs(correlation_coef))

        # Generate description
        description = self._generate_readiness_description(
            correlation_coef, readiness_scores, productivity_scores
        )

        correlations.append(HealthCorrelation(
            health_metric="readiness_score",
            productivity_metric="productivity_score",
            correlation_coefficient=correlation_coef,
            description=description,
            confidence_score=confidence,
            start_date=time_series.start_date,
            end_date=time_series.end_date,
            sample_size=len(paired_data),
            evidence={
                "avg_readiness": statistics.mean(readiness_scores),
                "avg_productivity": statistics.mean(productivity_scores),
                "readiness_range": (min(readiness_scores), max(readiness_scores)),
                "productivity_range": (min(productivity_scores), max(productivity_scores)),
                "correlation_strength": self._correlation_strength_label(correlation_coef)
            },
            metadata={"analysis_type": "same_day"}
        ))

        return correlations

    def _analyze_deep_sleep_vs_focus(
        self,
        aggregated_data: AggregatedData,
        time_series: Optional[TimeSeries] = None
    ) -> List[HealthCorrelation]:
        """
        Correlate deep sleep with next-day focus/task completion.

        Examines whether more deep sleep leads to better focus the next day.
        Uses task completion as a proxy for focus when direct focus metrics unavailable.

        Args:
            aggregated_data: Historical data
            time_series: Optional time series

        Returns:
            List of deep sleep correlations
        """
        correlations = []

        # Build paired data: deep sleep on day N -> tasks on day N+1
        paired_data = self._pair_health_with_next_day_tasks(
            aggregated_data, "deep_sleep_duration"
        )

        if len(paired_data) < self.min_data_points:
            return correlations

        # Convert deep sleep from minutes to hours
        deep_sleep_hours = [duration / 60.0 for duration, _ in paired_data]
        task_counts = [tasks for _, tasks in paired_data]

        # Calculate correlation
        correlation_coef = self._pearson_correlation(deep_sleep_hours, task_counts)

        if correlation_coef is None:
            return correlations

        confidence = self._calculate_confidence(len(paired_data), abs(correlation_coef))

        start_date, end_date = self._get_date_range(aggregated_data.health_metrics)

        description = self._generate_deep_sleep_description(
            correlation_coef, deep_sleep_hours, task_counts
        )

        correlations.append(HealthCorrelation(
            health_metric="deep_sleep",
            productivity_metric="next_day_focus",
            correlation_coefficient=correlation_coef,
            description=description,
            confidence_score=confidence,
            start_date=start_date,
            end_date=end_date,
            sample_size=len(paired_data),
            evidence={
                "avg_deep_sleep_hours": statistics.mean(deep_sleep_hours),
                "avg_next_day_tasks": statistics.mean(task_counts),
                "deep_sleep_range": (min(deep_sleep_hours), max(deep_sleep_hours)),
                "tasks_range": (min(task_counts), max(task_counts)),
                "correlation_strength": self._correlation_strength_label(correlation_coef)
            },
            metadata={
                "analysis_type": "next_day_impact",
                "focus_proxy": "task_completion"
            }
        ))

        return correlations

    def _analyze_sleep_score_vs_tasks(
        self,
        aggregated_data: AggregatedData,
        time_series: Optional[TimeSeries] = None
    ) -> List[HealthCorrelation]:
        """
        Correlate overall sleep score with next-day task completion.

        Sleep score combines duration, efficiency, timing, and other factors.

        Args:
            aggregated_data: Historical data
            time_series: Optional time series

        Returns:
            List of sleep score correlations
        """
        correlations = []

        # Build paired data: sleep score on day N -> tasks on day N+1
        paired_data = self._pair_health_with_next_day_tasks(
            aggregated_data, "sleep_score"
        )

        if len(paired_data) < self.min_data_points:
            return correlations

        sleep_scores = [score for score, _ in paired_data]
        task_counts = [tasks for _, tasks in paired_data]

        # Calculate correlation
        correlation_coef = self._pearson_correlation(sleep_scores, task_counts)

        if correlation_coef is None:
            return correlations

        confidence = self._calculate_confidence(len(paired_data), abs(correlation_coef))

        start_date, end_date = self._get_date_range(aggregated_data.health_metrics)

        description = self._generate_sleep_score_description(
            correlation_coef, sleep_scores, task_counts
        )

        correlations.append(HealthCorrelation(
            health_metric="sleep_score",
            productivity_metric="tasks_completed",
            correlation_coefficient=correlation_coef,
            description=description,
            confidence_score=confidence,
            start_date=start_date,
            end_date=end_date,
            sample_size=len(paired_data),
            evidence={
                "avg_sleep_score": statistics.mean(sleep_scores),
                "avg_tasks": statistics.mean(task_counts),
                "sleep_score_range": (min(sleep_scores), max(sleep_scores)),
                "tasks_range": (min(task_counts), max(task_counts)),
                "correlation_strength": self._correlation_strength_label(correlation_coef)
            },
            metadata={"analysis_type": "next_day_impact"}
        ))

        return correlations

    # Helper methods

    def _pair_health_with_next_day_tasks(
        self,
        aggregated_data: AggregatedData,
        health_metric_name: str
    ) -> List[Tuple[float, int]]:
        """
        Create paired data of health metric on day N and tasks on day N+1.

        Args:
            aggregated_data: Historical data
            health_metric_name: Name of health metric attribute (e.g., "total_sleep_duration")

        Returns:
            List of (health_value, next_day_task_count) tuples
        """
        # Create health metrics lookup by date
        health_by_date: Dict[date, HealthMetrics] = {
            h.date: h for h in aggregated_data.health_metrics
        }

        # Create task count lookup by date
        task_count_by_date: Dict[date, int] = defaultdict(int)
        for task in aggregated_data.task_completions:
            task_count_by_date[task.completed_date] += 1

        # Pair health metric on day N with tasks on day N+1
        paired_data = []
        for health in aggregated_data.health_metrics:
            health_value = getattr(health, health_metric_name, None)
            if health_value is None:
                continue

            # Look for tasks the next day
            next_day = health.date + timedelta(days=1)
            next_day_tasks = task_count_by_date.get(next_day, 0)

            # Only include if we have task data for next day
            if next_day in task_count_by_date or next_day_tasks > 0:
                paired_data.append((health_value, next_day_tasks))

        return paired_data

    def _pearson_correlation(
        self,
        x_values: List[float],
        y_values: List[float]
    ) -> Optional[float]:
        """
        Calculate Pearson correlation coefficient between two variables.

        Args:
            x_values: First variable values
            y_values: Second variable values

        Returns:
            Correlation coefficient (-1 to 1), or None if calculation fails
        """
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return None

        try:
            # Calculate means
            mean_x = statistics.mean(x_values)
            mean_y = statistics.mean(y_values)

            # Calculate standard deviations
            stdev_x = statistics.stdev(x_values)
            stdev_y = statistics.stdev(y_values)

            # Avoid division by zero
            if stdev_x == 0 or stdev_y == 0:
                return None

            # Calculate correlation
            n = len(x_values)
            covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values)) / n
            correlation = covariance / (stdev_x * stdev_y)

            # Clamp to [-1, 1] to handle floating point errors
            return max(-1.0, min(1.0, correlation))

        except (statistics.StatisticsError, ZeroDivisionError):
            return None

    def _calculate_confidence(self, sample_size: int, correlation_strength: float) -> float:
        """
        Calculate confidence score based on sample size and correlation strength.

        Args:
            sample_size: Number of data points
            correlation_strength: Absolute value of correlation coefficient

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Sample size component (0-0.5)
        # Reaches 0.5 at 30 samples
        size_score = min(0.5, sample_size / 60.0)

        # Correlation strength component (0-0.5)
        # Stronger correlation = higher confidence
        strength_score = correlation_strength * 0.5

        # Combined confidence
        confidence = size_score + strength_score

        return min(0.95, confidence)

    def _correlation_strength_label(self, correlation: float) -> str:
        """
        Get human-readable label for correlation strength.

        Args:
            correlation: Correlation coefficient

        Returns:
            Label like "strong_positive", "weak_negative", etc.
        """
        abs_corr = abs(correlation)
        direction = "positive" if correlation > 0 else "negative"

        if abs_corr >= 0.7:
            strength = "strong"
        elif abs_corr >= 0.4:
            strength = "moderate"
        elif abs_corr >= 0.2:
            strength = "weak"
        else:
            strength = "very_weak"

        return f"{strength}_{direction}"

    def _get_date_range(self, health_metrics: List[HealthMetrics]) -> Tuple[date, date]:
        """Get start and end date from health metrics."""
        if not health_metrics:
            today = date.today()
            return today, today

        dates = [h.date for h in health_metrics]
        return min(dates), max(dates)

    # Description generators

    def _generate_sleep_duration_description(
        self,
        correlation: float,
        sleep_hours: List[float],
        task_counts: List[int]
    ) -> str:
        """Generate human-readable description for sleep duration correlation."""
        avg_sleep = statistics.mean(sleep_hours)
        avg_tasks = statistics.mean(task_counts)

        if correlation > 0.4:
            # Find high/low sleep productivity
            paired = list(zip(sleep_hours, task_counts))
            paired.sort(key=lambda x: x[0], reverse=True)

            # Average tasks for top 1/3 sleep vs bottom 1/3
            top_third = paired[:len(paired)//3]
            bottom_third = paired[-len(paired)//3:]

            high_sleep_tasks = statistics.mean([t for _, t in top_third]) if top_third else avg_tasks
            low_sleep_tasks = statistics.mean([t for _, t in bottom_third]) if bottom_third else avg_tasks

            if high_sleep_tasks > low_sleep_tasks:
                percent_diff = ((high_sleep_tasks - low_sleep_tasks) / low_sleep_tasks * 100) if low_sleep_tasks > 0 else 0
                return f"More sleep correlates with higher productivity (+{percent_diff:.0f}% more tasks with {avg_sleep:.1f}+ hours sleep)"

        elif correlation < -0.4:
            return f"Negative correlation detected: more sleep associated with fewer tasks (unusual pattern worth investigating)"

        # Weak or no correlation
        return f"Sleep duration shows weak correlation with task completion (avg {avg_sleep:.1f} hours sleep, {avg_tasks:.1f} tasks/day)"

    def _generate_readiness_description(
        self,
        correlation: float,
        readiness: List[float],
        productivity: List[float]
    ) -> str:
        """Generate description for readiness-productivity correlation."""
        avg_readiness = statistics.mean(readiness)
        avg_productivity = statistics.mean(productivity)

        if correlation > 0.4:
            return f"Higher readiness scores strongly correlate with better productivity (avg readiness {avg_readiness:.0f} → {avg_productivity:.2f} productivity score)"
        elif correlation > 0.2:
            return f"Moderate positive correlation between readiness and productivity (r={correlation:.2f})"
        else:
            return f"Weak correlation between readiness score and productivity"

    def _generate_deep_sleep_description(
        self,
        correlation: float,
        deep_sleep_hours: List[float],
        task_counts: List[int]
    ) -> str:
        """Generate description for deep sleep correlation."""
        avg_deep_sleep = statistics.mean(deep_sleep_hours)
        avg_tasks = statistics.mean(task_counts)

        if correlation > 0.3:
            return f"More deep sleep correlates with better next-day focus and task completion (avg {avg_deep_sleep:.1f}h deep sleep → {avg_tasks:.1f} tasks)"
        else:
            return f"Deep sleep shows weak correlation with next-day productivity"

    def _generate_sleep_score_description(
        self,
        correlation: float,
        sleep_scores: List[float],
        task_counts: List[int]
    ) -> str:
        """Generate description for sleep score correlation."""
        avg_score = statistics.mean(sleep_scores)
        avg_tasks = statistics.mean(task_counts)

        if correlation > 0.4:
            # Find high vs low score productivity
            paired = list(zip(sleep_scores, task_counts))
            high_score_tasks = statistics.mean([t for s, t in paired if s >= 85]) if any(s >= 85 for s, _ in paired) else avg_tasks
            low_score_tasks = statistics.mean([t for s, t in paired if s < 70]) if any(s < 70 for s, _ in paired) else avg_tasks

            if high_score_tasks > low_score_tasks and low_score_tasks > 0:
                percent_diff = ((high_score_tasks - low_score_tasks) / low_score_tasks * 100)
                return f"High sleep scores (85+) correlate with {percent_diff:.0f}% more tasks completed the next day"

        return f"Sleep quality (score avg {avg_score:.0f}) shows correlation with task completion"
