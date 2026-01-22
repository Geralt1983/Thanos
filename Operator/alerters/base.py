"""
Base alerter interface and data classes for Operator daemon.

All alerters must implement the AlerterInterface protocol to ensure
consistent behavior across different notification channels.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any
from datetime import datetime


# Type alias for severity levels
AlertSeverity = Literal["info", "warning", "high", "critical"]


@dataclass
class Alert:
    """
    Alert data structure.

    Attributes:
        title: Alert title (e.g., "Low Readiness")
        message: Alert body (e.g., "Your readiness is 48. Rest today.")
        severity: Alert severity level (info|warning|high|critical)
        source_type: Type of monitor that generated this (health|task|pattern)
        source_id: Unique identifier for the source entity
        timestamp: When the alert was generated
        metadata: Additional context for routing/formatting
        dedup_key: Key for deduplication (format: "type:entity_id")
    """
    title: str
    message: str
    severity: AlertSeverity
    source_type: str  # health, task, pattern
    source_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    dedup_key: Optional[str] = None

    def __post_init__(self):
        """Set default values after initialization."""
        if self.timestamp is None:
            self.timestamp = datetime.now()

        if self.dedup_key is None and self.source_id:
            self.dedup_key = f"{self.source_type}:{self.source_id}"


class AlerterInterface(ABC):
    """
    Base interface for all alerters.

    Alerters send notifications through various channels (Telegram, macOS, journal).
    All alerters must implement the send() method and handle errors gracefully.
    """

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """
        Send an alert through this alerter's channel.

        Args:
            alert: The alert to send

        Returns:
            True if alert was sent successfully, False otherwise

        Note:
            Implementations MUST NOT raise exceptions. All errors should be
            caught, logged, and return False.
        """
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """
        Check if this alerter is enabled and ready to send.

        Returns:
            True if alerter is configured and ready, False otherwise
        """
        pass

    def should_send(self, alert: Alert) -> bool:
        """
        Check if this alerter should send the given alert based on severity.

        Override this method to implement custom filtering logic.

        Args:
            alert: The alert to evaluate

        Returns:
            True if this alerter should send the alert, False otherwise
        """
        return self.is_enabled()
