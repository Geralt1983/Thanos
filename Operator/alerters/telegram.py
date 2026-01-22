"""
Telegram Alerter - Send alerts via Telegram Bot API.

Sends formatted alerts to a Telegram chat with:
- Severity-based emoji prefixes
- Thanos voice formatting
- Rate limiting (max 1 message per minute)
- Retry logic with exponential backoff
- Error handling without raising exceptions
"""

import os
import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from .base import Alert, AlerterInterface, AlertSeverity


logger = logging.getLogger("thanos.operator.alerters.telegram")


class TelegramAlerter(AlerterInterface):
    """
    Send alerts via Telegram Bot API.

    Features:
    - Severity-based emoji prefixes
    - Markdown formatting with Thanos voice
    - Rate limiting (1 message per minute)
    - Retry with exponential backoff (3 attempts)
    - Dry-run mode for testing

    Environment Variables:
        TELEGRAM_BOT_TOKEN: Bot API token
        TELEGRAM_CHAT_ID: Target chat ID
        OPERATOR_DRY_RUN: Set to "true" to disable actual sending
    """

    # Emoji mapping for severity levels
    SEVERITY_EMOJI = {
        "info": "ℹ️",
        "warning": "⚠️",
        "high": "🟠",
        "critical": "🔴"
    }

    # Rate limiting: max 1 message per minute
    RATE_LIMIT_SECONDS = 60

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1.0  # seconds
    RETRY_BACKOFF_MULTIPLIER = 2.0

    # API timeout
    TIMEOUT_SECONDS = 10.0

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
        min_severity: AlertSeverity = "warning",
        dry_run: Optional[bool] = None
    ):
        """
        Initialize Telegram alerter.

        Args:
            token: Telegram bot token (defaults to TELEGRAM_BOT_TOKEN env var)
            chat_id: Target chat ID (defaults to TELEGRAM_CHAT_ID env var)
            min_severity: Minimum severity to send (info|warning|high|critical)
            dry_run: If True, log instead of sending (defaults to OPERATOR_DRY_RUN env var)
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.min_severity = min_severity
        self.dry_run = dry_run if dry_run is not None else (
            os.getenv("OPERATOR_DRY_RUN", "false").lower() == "true"
        )

        # Rate limiting state
        self.last_send_time: Optional[datetime] = None

        # Validate configuration
        if not HTTPX_AVAILABLE:
            logger.warning("httpx not installed - Telegram alerter disabled. Install with: pip install httpx")
            self.token = None

        if not self.token or not self.chat_id:
            if not self.dry_run:
                logger.warning("Telegram not configured (missing token or chat_id) - alerter disabled")

    def is_enabled(self) -> bool:
        """Check if Telegram alerter is enabled."""
        if self.dry_run:
            return True  # Allow dry-run even without credentials

        return bool(self.token and self.chat_id and HTTPX_AVAILABLE)

    def should_send(self, alert: Alert) -> bool:
        """Check if alert meets minimum severity threshold."""
        if not self.is_enabled():
            return False

        severity_levels = ["info", "warning", "high", "critical"]
        alert_level = severity_levels.index(alert.severity)
        min_level = severity_levels.index(self.min_severity)

        return alert_level >= min_level

    def _check_rate_limit(self) -> bool:
        """
        Check if we can send now based on rate limit.

        Returns:
            True if we can send, False if rate limited
        """
        if self.last_send_time is None:
            return True

        elapsed = (datetime.now() - self.last_send_time).total_seconds()
        return elapsed >= self.RATE_LIMIT_SECONDS

    def _format_message(self, alert: Alert) -> str:
        """
        Format alert message for Telegram with Thanos voice.

        Args:
            alert: The alert to format

        Returns:
            Formatted message string with Markdown
        """
        emoji = self.SEVERITY_EMOJI.get(alert.severity, "📢")
        severity_label = alert.severity.upper()

        # Build message parts
        parts = [
            f"{emoji} *{severity_label}: {alert.title}*",
            "",
            alert.message,
            "",
            f"_Source: {alert.source_type} monitor_",
            f"_Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}_"
        ]

        # Add Thanos quote for critical alerts
        if alert.severity == "critical":
            thanos_quotes = [
                "Dread it. Run from it. Destiny arrives all the same.",
                "The hardest choices require the strongest wills.",
                "Reality is often disappointing.",
            ]
            # Use source_id as seed for consistent quote per alert type
            seed = hash(alert.source_id or alert.source_type) % len(thanos_quotes)
            parts.append("")
            parts.append(f"_{thanos_quotes[seed]}_")

        return "\n".join(parts)

    async def _send_with_retry(self, message: str) -> bool:
        """
        Send message with retry logic and exponential backoff.

        Args:
            message: The formatted message to send

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.token or not self.chat_id:
            logger.error("Cannot send - missing token or chat_id")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        delay = self.INITIAL_RETRY_DELAY

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        json={
                            "chat_id": self.chat_id,
                            "text": message,
                            "parse_mode": "Markdown",
                            "disable_web_page_preview": True
                        },
                        timeout=self.TIMEOUT_SECONDS
                    )

                    if response.status_code == 200:
                        logger.info(f"Telegram alert sent successfully (attempt {attempt})")
                        return True
                    else:
                        logger.warning(
                            f"Telegram API error (attempt {attempt}): "
                            f"{response.status_code} - {response.text}"
                        )

                        # Don't retry on 4xx errors (bad request, auth issues)
                        if 400 <= response.status_code < 500:
                            logger.error("Client error - not retrying")
                            return False

            except httpx.TimeoutException:
                logger.warning(f"Telegram request timeout (attempt {attempt})")
            except Exception as e:
                logger.error(f"Telegram send error (attempt {attempt}): {e}")

            # Wait before retry (except on last attempt)
            if attempt < self.MAX_RETRIES:
                logger.info(f"Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
                delay *= self.RETRY_BACKOFF_MULTIPLIER

        logger.error(f"Telegram send failed after {self.MAX_RETRIES} attempts")
        return False

    async def send(self, alert: Alert) -> bool:
        """
        Send alert via Telegram.

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

            # Check rate limit
            if not self._check_rate_limit():
                wait_time = self.RATE_LIMIT_SECONDS - (
                    datetime.now() - self.last_send_time
                ).total_seconds()
                logger.warning(
                    f"Rate limited - skipping alert (wait {wait_time:.0f}s)"
                )
                return False

            # Format message
            message = self._format_message(alert)

            # Dry-run mode: log instead of sending
            if self.dry_run:
                logger.info(f"[DRY RUN] Would send Telegram alert:\n{message}")
                return True

            # Send with retry
            success = await self._send_with_retry(message)

            # Update rate limit timestamp on success
            if success:
                self.last_send_time = datetime.now()

            return success

        except Exception as e:
            logger.error(f"Unexpected error in Telegram alerter: {e}")
            return False
