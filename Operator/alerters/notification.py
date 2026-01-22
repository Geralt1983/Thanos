"""
macOS Notification Alerter - Send native macOS notifications.

Sends alerts as native macOS Notification Center notifications using osascript:
- Different sounds for severity levels
- Error handling for non-macOS environments
- Graceful degradation
"""

import os
import sys
import asyncio
import logging
import subprocess
from typing import Optional
from pathlib import Path

from .base import Alert, AlerterInterface, AlertSeverity


logger = logging.getLogger("thanos.operator.alerters.notification")


class NotificationAlerter(AlerterInterface):
    """
    Send alerts via macOS Notification Center.

    Features:
    - Native macOS notifications via osascript
    - Severity-based sounds:
        - info: "Glass" sound
        - warning: "Basso" sound
        - high: "Funk" sound
        - critical: "Sosumi" sound
    - Graceful handling on non-macOS systems
    - Dry-run mode for testing

    Environment Variables:
        OPERATOR_DRY_RUN: Set to "true" to disable actual sending
    """

    # Sound mapping for severity levels
    SEVERITY_SOUNDS = {
        "info": "Glass",
        "warning": "Basso",
        "high": "Funk",
        "critical": "Sosumi"
    }

    # Timeout for osascript command
    TIMEOUT_SECONDS = 5.0

    def __init__(
        self,
        min_severity: AlertSeverity = "warning",
        dry_run: Optional[bool] = None
    ):
        """
        Initialize macOS notification alerter.

        Args:
            min_severity: Minimum severity to send (info|warning|high|critical)
            dry_run: If True, log instead of sending (defaults to OPERATOR_DRY_RUN env var)
        """
        self.min_severity = min_severity
        self.dry_run = dry_run if dry_run is not None else (
            os.getenv("OPERATOR_DRY_RUN", "false").lower() == "true"
        )

        # Check if we're on macOS
        self.is_macos = sys.platform == "darwin"

        if not self.is_macos and not self.dry_run:
            logger.warning("Not running on macOS - notification alerter disabled")

    def is_enabled(self) -> bool:
        """Check if macOS notification alerter is enabled."""
        if self.dry_run:
            return True  # Allow dry-run even on non-macOS

        return self.is_macos

    def should_send(self, alert: Alert) -> bool:
        """Check if alert meets minimum severity threshold."""
        if not self.is_enabled():
            return False

        severity_levels = ["info", "warning", "high", "critical"]
        alert_level = severity_levels.index(alert.severity)
        min_level = severity_levels.index(self.min_severity)

        return alert_level >= min_level

    def _build_osascript_command(self, alert: Alert) -> list:
        """
        Build osascript command for notification.

        Args:
            alert: The alert to send

        Returns:
            List of command arguments for subprocess
        """
        # Get sound for severity level
        sound = self.SEVERITY_SOUNDS.get(alert.severity, "Glass")

        # Build AppleScript
        # Note: We escape quotes in the message/title
        escaped_title = alert.title.replace('"', '\\"')
        escaped_message = alert.message.replace('"', '\\"')

        script_parts = [
            'display notification',
            f'"{escaped_message}"',
            f'with title "{escaped_title}"',
            f'subtitle "Thanos Operator"',
            f'sound name "{sound}"'
        ]

        script = " ".join(script_parts)

        return ["osascript", "-e", script]

    async def send(self, alert: Alert) -> bool:
        """
        Send alert via macOS Notification Center.

        Args:
            alert: The alert to send

        Returns:
            True if sent successfully, False otherwise

        Note:
            Never raises exceptions - all errors are caught and logged.
        """
        try:
            # Check if we should send this alert
            if not self.should_send(alert):
                logger.debug(
                    f"Skipping alert (severity={alert.severity}, min={self.min_severity})"
                )
                return False

            # Build command
            cmd = self._build_osascript_command(alert)

            # Dry-run mode: log instead of sending
            if self.dry_run:
                logger.info(
                    f"[DRY RUN] Would send macOS notification:\n"
                    f"  Title: {alert.title}\n"
                    f"  Message: {alert.message}\n"
                    f"  Sound: {self.SEVERITY_SOUNDS.get(alert.severity, 'Glass')}"
                )
                return True

            # Not on macOS - can't send
            if not self.is_macos:
                logger.debug("Skipping notification - not on macOS")
                return False

            # Run osascript command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.TIMEOUT_SECONDS
                )

                if process.returncode == 0:
                    logger.info(f"macOS notification sent: {alert.title}")
                    return True
                else:
                    stderr_text = stderr.decode() if stderr else "unknown error"
                    logger.error(
                        f"osascript failed (return code {process.returncode}): {stderr_text}"
                    )
                    return False

            except asyncio.TimeoutError:
                logger.error("osascript command timeout")
                process.kill()
                await process.wait()
                return False

        except FileNotFoundError:
            logger.error("osascript not found - macOS notifications unavailable")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in macOS notification alerter: {e}")
            return False
