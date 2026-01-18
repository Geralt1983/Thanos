#!/usr/bin/env python3
"""
Base Alert Checker for Thanos.

Abstract base class for all alert checkers with common functionality.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

import sys
sys.path.insert(0, str(__file__).rsplit('/Tools', 1)[0])

from Tools.journal import EventType


@dataclass
class Alert:
    """A single alert from a checker."""
    type: EventType
    severity: str  # debug, info, warning, alert, critical
    title: str
    data: Dict[str, Any] = field(default_factory=dict)
    dedup_key: Optional[str] = None  # For deduplication

    def __post_init__(self):
        """Generate dedup key if not provided."""
        if self.dedup_key is None:
            # Create dedup key from type and key data fields
            key_data = self.data.get('dedup_key', str(self.data))
            self.dedup_key = f"{self.type.value}:{key_data}"


class AlertChecker(ABC):
    """Abstract base class for alert checkers."""

    # Source identifier for journal logging
    source: str = "unknown"

    # Check interval hint (seconds)
    check_interval: int = 900  # 15 minutes default

    def __init__(self):
        """Initialize checker."""
        self.last_check: Optional[datetime] = None
        self.last_error: Optional[Exception] = None
        self.check_count: int = 0
        self.error_count: int = 0

    @abstractmethod
    async def check(self) -> List[Alert]:
        """
        Run check and return any alerts.

        Subclasses must implement this method to perform their specific
        checks and return a list of Alert objects.

        Returns:
            List of Alert objects (empty list if no alerts)
        """
        pass

    async def safe_check(self) -> List[Alert]:
        """
        Run check with error handling.

        Wraps the check() method with error handling to ensure
        one failing checker doesn't break the entire daemon.

        Returns:
            List of Alert objects (empty list on error)
        """
        try:
            self.check_count += 1
            self.last_check = datetime.now()
            alerts = await self.check()
            self.last_error = None
            return alerts

        except Exception as e:
            self.error_count += 1
            self.last_error = e
            # Return error alert so it gets logged
            return [Alert(
                type=EventType.SYNC_FAILED,
                severity="warning",
                title=f"Check failed for {self.source}: {str(e)[:100]}",
                data={'error': str(e), 'checker': self.source}
            )]

    def get_status(self) -> Dict[str, Any]:
        """Get checker status for monitoring."""
        return {
            'source': self.source,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'check_count': self.check_count,
            'error_count': self.error_count,
            'last_error': str(self.last_error) if self.last_error else None,
            'check_interval': self.check_interval
        }


class ThresholdChecker(AlertChecker):
    """
    Base class for checkers that compare values against thresholds.

    Provides helper methods for common threshold-based alerting patterns.
    """

    def check_threshold(
        self,
        value: float,
        warning_threshold: float,
        critical_threshold: float,
        metric_name: str,
        comparison: str = "below",  # "below" or "above"
        unit: str = ""
    ) -> Optional[Alert]:
        """
        Check a value against thresholds.

        Args:
            value: Current value
            warning_threshold: Threshold for warning
            critical_threshold: Threshold for critical
            metric_name: Name of the metric for alert title
            comparison: "below" if lower is worse, "above" if higher is worse
            unit: Unit for display (e.g., "$", "ms", "%")

        Returns:
            Alert if threshold exceeded, None otherwise
        """
        if comparison == "below":
            is_critical = value < critical_threshold
            is_warning = value < warning_threshold
        else:
            is_critical = value > critical_threshold
            is_warning = value > warning_threshold

        if is_critical:
            return Alert(
                type=EventType.HEALTH_ALERT,
                severity="critical",
                title=f"Critical: {metric_name} at {unit}{value:.1f}",
                data={
                    'metric': metric_name,
                    'value': value,
                    'threshold': critical_threshold,
                    'unit': unit
                },
                dedup_key=f"{metric_name}:critical"
            )
        elif is_warning:
            return Alert(
                type=EventType.HEALTH_ALERT,
                severity="warning",
                title=f"Warning: {metric_name} at {unit}{value:.1f}",
                data={
                    'metric': metric_name,
                    'value': value,
                    'threshold': warning_threshold,
                    'unit': unit
                },
                dedup_key=f"{metric_name}:warning"
            )

        return None

    def check_multiple_thresholds(
        self,
        metrics: Dict[str, float],
        thresholds: Dict[str, Dict[str, float]]
    ) -> List[Alert]:
        """
        Check multiple metrics against their thresholds.

        Args:
            metrics: Dict of metric_name -> value
            thresholds: Dict of metric_name -> {warning, critical, comparison, unit}

        Returns:
            List of alerts for exceeded thresholds
        """
        alerts = []

        for metric_name, value in metrics.items():
            if metric_name not in thresholds:
                continue

            t = thresholds[metric_name]
            alert = self.check_threshold(
                value=value,
                warning_threshold=t.get('warning', 0),
                critical_threshold=t.get('critical', 0),
                metric_name=metric_name,
                comparison=t.get('comparison', 'below'),
                unit=t.get('unit', '')
            )

            if alert:
                alerts.append(alert)

        return alerts
