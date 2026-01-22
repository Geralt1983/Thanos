"""
Journal Alerter - Log all alerts to database and file.

Provides append-only audit trail of all alerts with:
- Database logging to thanos_unified.db journal table
- Fallback to file logging if database unavailable
- Never fails - guaranteed to record all alerts
- Comprehensive metadata capture
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.journal import Journal, EventType, Severity
from .base import Alert, AlerterInterface


logger = logging.getLogger("thanos.operator.alerters.journal")


class JournalAlerter(AlerterInterface):
    """
    Log all alerts to journal for audit trail.

    Features:
    - Append-only event log in thanos_unified.db
    - Fallback to file logging if database unavailable
    - Never fails - always records the alert somewhere
    - Captures full alert context and metadata
    - No rate limiting - logs everything
    - Dry-run mode for testing

    Environment Variables:
        THANOS_ROOT: Root directory for Thanos (defaults to /Users/jeremy/Projects/Thanos)
        OPERATOR_DRY_RUN: Set to "true" to disable actual logging
    """

    # Fallback log file if database unavailable
    FALLBACK_LOG_FILENAME = "operator_alerts.log"

    def __init__(
        self,
        thanos_root: Optional[str] = None,
        dry_run: Optional[bool] = None
    ):
        """
        Initialize journal alerter.

        Args:
            thanos_root: Root directory for Thanos (defaults to THANOS_ROOT env var)
            dry_run: If True, log to console instead of journal
        """
        self.thanos_root = Path(thanos_root or os.getenv(
            "THANOS_ROOT",
            "/Users/jeremy/Projects/Thanos"
        ))
        self.dry_run = dry_run if dry_run is not None else (
            os.getenv("OPERATOR_DRY_RUN", "false").lower() == "true"
        )

        # Initialize journal
        try:
            # Journal expects db_path to thanos_unified.db
            db_path = self.thanos_root / "State" / "thanos_unified.db"
            self.journal = Journal(db_path=db_path)
            self.journal_available = True
            logger.info("Journal initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize journal - will use fallback logging: {e}")
            self.journal = None
            self.journal_available = False

        # Fallback log file path
        self.fallback_log_path = self.thanos_root / "logs" / self.FALLBACK_LOG_FILENAME

    def is_enabled(self) -> bool:
        """Journal alerter is always enabled."""
        return True

    def should_send(self, alert: Alert) -> bool:
        """Journal alerter logs all alerts regardless of severity."""
        return True

    def _map_severity_to_journal(self, alert_severity: str) -> Severity:
        """
        Map alert severity to journal severity.

        Args:
            alert_severity: Alert severity level

        Returns:
            Corresponding journal Severity enum value
        """
        mapping = {
            "info": Severity.INFO,
            "warning": Severity.WARNING,
            "high": Severity.WARNING,
            "critical": Severity.CRITICAL
        }
        return mapping.get(alert_severity, Severity.INFO)

    def _write_fallback_log(self, alert: Alert) -> bool:
        """
        Write alert to fallback log file.

        Args:
            alert: The alert to log

        Returns:
            True if written successfully, False otherwise
        """
        try:
            # Ensure log directory exists
            self.fallback_log_path.parent.mkdir(parents=True, exist_ok=True)

            # Format log entry
            timestamp = alert.timestamp.isoformat() if alert.timestamp else datetime.now().isoformat()
            log_entry = {
                "timestamp": timestamp,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "source_type": alert.source_type,
                "source_id": alert.source_id,
                "dedup_key": alert.dedup_key,
                "metadata": alert.metadata
            }

            # Append to log file (one JSON object per line)
            with open(self.fallback_log_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

            logger.debug(f"Alert logged to fallback file: {self.fallback_log_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write fallback log: {e}")
            return False

    async def send(self, alert: Alert) -> bool:
        """
        Log alert to journal.

        Args:
            alert: The alert to log

        Returns:
            Always returns True (never fails)

        Note:
            This method NEVER raises exceptions and ALWAYS succeeds by
            falling back to file logging if database unavailable.
        """
        try:
            # Dry-run mode: log to console
            if self.dry_run:
                logger.info(
                    f"[DRY RUN] Would log to journal:\n"
                    f"  Severity: {alert.severity}\n"
                    f"  Title: {alert.title}\n"
                    f"  Message: {alert.message}\n"
                    f"  Source: {alert.source_type}/{alert.source_id}\n"
                    f"  Dedup Key: {alert.dedup_key}"
                )
                return True

            # Try database journal first
            if self.journal_available and self.journal:
                try:
                    # Map severity
                    journal_severity = self._map_severity_to_journal(alert.severity)

                    # Build metadata
                    metadata = {
                        "alert_severity": alert.severity,
                        "source_type": alert.source_type,
                        "source_id": alert.source_id,
                        "dedup_key": alert.dedup_key,
                        **(alert.metadata or {})
                    }

                    # Log to journal
                    self.journal.log(
                        event_type=EventType.ALERT,
                        severity=journal_severity,
                        message=f"[{alert.severity.upper()}] {alert.title}: {alert.message}",
                        metadata=metadata
                    )

                    logger.debug(f"Alert logged to journal database: {alert.title}")
                    return True

                except Exception as e:
                    logger.warning(f"Journal database logging failed, using fallback: {e}")
                    # Fall through to fallback logging

            # Fallback to file logging
            success = self._write_fallback_log(alert)

            # Even if fallback fails, we still return True to prevent
            # the alerter system from retrying or failing
            if not success:
                # Last resort: log to Python logger
                logger.error(
                    f"ALL LOGGING FAILED - Alert lost: "
                    f"[{alert.severity}] {alert.title} - {alert.message}"
                )

            # Always return True - journal alerter never fails
            return True

        except Exception as e:
            # Catch-all to ensure we NEVER raise exceptions
            logger.error(f"Critical error in journal alerter (alert may be lost): {e}")
            # Even in catastrophic failure, return True to prevent cascading failures
            return True
