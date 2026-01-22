#!/usr/bin/env python3
"""
Thanos Notification System

Multi-channel notifications: macOS Notification Center + Telegram

Features:
- Priority-based routing (info → macOS only, warning/critical → macOS + Telegram)
- Notification queue with rate limiting (max 10/minute)
- Deduplication (same message within 5 minutes)
- Automatic retry logic for failed sends
- Dry-run mode for testing
- Voice alerts for critical notifications
"""

import os
import sys
import subprocess
from typing import Literal, Optional, Dict, Any
import logging
import requests
import hashlib
from datetime import datetime, timedelta
from collections import deque
from pathlib import Path
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("thanos.notifications")

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Rate limiting constants
MAX_NOTIFICATIONS_PER_MINUTE = 10
DEDUPLICATION_WINDOW_SECONDS = 300  # 5 minutes
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2

NotificationPriority = Literal["info", "warning", "critical"]


class NotificationRouter:
    """
    Route notifications to appropriate channels based on priority.

    Features:
    - Rate limiting (max 10 notifications per minute)
    - Deduplication (same message within 5 minutes)
    - Automatic retry for failed sends
    - Dry-run mode for testing
    """

    ROUTING = {
        "critical": ["notification_center", "telegram", "voice"],
        "warning": ["notification_center", "telegram"],
        "info": ["notification_center"],
    }

    def __init__(
        self,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        dry_run: bool = False,
    ):
        self.telegram_token = telegram_token or TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = telegram_chat_id or TELEGRAM_CHAT_ID
        self.dry_run = dry_run

        # Rate limiting: track notification timestamps
        self.notification_timestamps: deque = deque(maxlen=MAX_NOTIFICATIONS_PER_MINUTE)

        # Deduplication: track recent notifications by hash
        self.recent_notifications: Dict[str, datetime] = {}

        if not self.telegram_token:
            logger.warning("No TELEGRAM_BOT_TOKEN set - Telegram disabled")

        if self.dry_run:
            logger.info("DRY-RUN MODE: Notifications will be logged but not sent")

    def send(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = "info",
        subtitle: Optional[str] = None,
        sound: bool = True,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Send notification via appropriate channels.

        Args:
            title: Notification title
            message: Notification body
            priority: info|warning|critical
            subtitle: Optional subtitle
            sound: Whether to play sound
            force: Skip rate limiting and deduplication checks

        Returns:
            dict: {
                'notification_center': bool,
                'telegram': bool,
                'voice': bool,
                'skipped': str|None,  # Reason if notification was skipped
                'dry_run': bool
            }
        """
        # Check rate limiting (unless forced)
        if not force and not self._check_rate_limit():
            logger.warning(f"Rate limit exceeded - dropping notification: {title}")
            return {
                "notification_center": False,
                "telegram": False,
                "voice": False,
                "skipped": "rate_limit_exceeded",
                "dry_run": self.dry_run,
            }

        # Check deduplication (unless forced)
        if not force and self._is_duplicate(title, message):
            logger.debug(f"Duplicate notification suppressed: {title}")
            return {
                "notification_center": False,
                "telegram": False,
                "voice": False,
                "skipped": "duplicate",
                "dry_run": self.dry_run,
            }

        # Dry-run mode
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would send: [{priority}] {title}: {message}")
            # Still record for rate limiting and deduplication
            self._record_notification(title, message)
            return {
                "notification_center": True,
                "telegram": True,
                "voice": priority == "critical",
                "skipped": None,
                "dry_run": True,
            }

        # Send to appropriate channels
        channels = self.ROUTING.get(priority, ["notification_center"])
        results: Dict[str, Any] = {"skipped": None, "dry_run": False}

        for channel in channels:
            if channel == "notification_center":
                results["notification_center"] = self._send_with_retry(
                    lambda: self._send_macos_notification(title, message, subtitle, sound)
                )

            elif channel == "telegram":
                results["telegram"] = self._send_with_retry(
                    lambda: self._send_telegram_message(title, message, priority)
                )

            elif channel == "voice":
                results["voice"] = self._send_with_retry(
                    lambda: self._send_voice_alert(message)
                )

        # Record notification for rate limiting and deduplication
        self._record_notification(title, message)

        return results

    def _send_macos_notification(
        self,
        title: str,
        message: str,
        subtitle: Optional[str] = None,
        sound: bool = True,
    ) -> bool:
        """Send notification via macOS Notification Center."""
        try:
            # Build osascript command
            script_parts = [
                'display notification',
                f'"{message}"',
                f'with title "{title}"',
            ]

            if subtitle:
                script_parts.append(f'subtitle "{subtitle}"')

            if sound:
                script_parts.append('sound name "Submarine"')

            script = " ".join(script_parts)
            cmd = ["osascript", "-e", script]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                logger.info(f"macOS notification sent: {title}")
                return True
            else:
                logger.error(f"macOS notification failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"macOS notification error: {e}")
            return False

    def _send_telegram_message(
        self, title: str, message: str, priority: NotificationPriority
    ) -> bool:
        """Send notification via Telegram."""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram not configured - skipping")
            return False

        try:
            # Format message with priority emoji
            priority_emoji = {
                "info": "ℹ️",
                "warning": "⚠️",
                "critical": "🔴",
            }

            emoji = priority_emoji.get(priority, "📢")
            formatted_message = f"{emoji} *{title}*\n\n{message}"

            # Send via Telegram API
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"

            data = {
                "chat_id": self.telegram_chat_id,
                "text": formatted_message,
                "parse_mode": "Markdown",
            }

            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            logger.info(f"Telegram message sent: {title}")
            return True

        except Exception as e:
            logger.error(f"Telegram message error: {e}")
            return False

    def _send_voice_alert(self, message: str) -> bool:
        """Send voice alert (if voice synthesis available)."""
        try:
            # Import voice module
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path(__file__).parent))
            from voice import synthesize

            result = synthesize(message, play=True)
            return result is not None

        except Exception as e:
            logger.error(f"Voice alert error: {e}")
            return False

    def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.

        Returns:
            True if notification can be sent, False if rate limit exceeded
        """
        now = datetime.now()

        # Remove timestamps older than 1 minute
        cutoff = now - timedelta(seconds=60)
        while self.notification_timestamps and self.notification_timestamps[0] < cutoff:
            self.notification_timestamps.popleft()

        # Check if we can send another notification
        if len(self.notification_timestamps) >= MAX_NOTIFICATIONS_PER_MINUTE:
            return False

        return True

    def _is_duplicate(self, title: str, message: str) -> bool:
        """
        Check if notification was sent recently (within 5 minutes).

        Args:
            title: Notification title
            message: Notification body

        Returns:
            True if this is a duplicate, False otherwise
        """
        # Create hash key
        key = hashlib.md5(f"{title}:{message}".encode()).hexdigest()

        # Clean up old entries
        now = datetime.now()
        cutoff = now - timedelta(seconds=DEDUPLICATION_WINDOW_SECONDS)
        expired_keys = [k for k, v in self.recent_notifications.items() if v < cutoff]
        for expired_key in expired_keys:
            del self.recent_notifications[expired_key]

        # Check if this notification was sent recently
        if key in self.recent_notifications:
            last_sent = self.recent_notifications[key]
            if now - last_sent < timedelta(seconds=DEDUPLICATION_WINDOW_SECONDS):
                return True

        return False

    def _record_notification(self, title: str, message: str):
        """
        Record notification for rate limiting and deduplication.

        Args:
            title: Notification title
            message: Notification body
        """
        now = datetime.now()

        # Record for rate limiting
        self.notification_timestamps.append(now)

        # Record for deduplication
        key = hashlib.md5(f"{title}:{message}".encode()).hexdigest()
        self.recent_notifications[key] = now

    def _send_with_retry(self, send_func, max_attempts: int = RETRY_ATTEMPTS) -> bool:
        """
        Send notification with automatic retry on failure.

        Args:
            send_func: Function to call to send notification
            max_attempts: Maximum number of attempts

        Returns:
            True if successful, False if all attempts failed
        """
        for attempt in range(1, max_attempts + 1):
            try:
                success = send_func()
                if success:
                    return True

                # Log failure and retry
                if attempt < max_attempts:
                    logger.warning(f"Send failed (attempt {attempt}/{max_attempts}), retrying...")
                    time.sleep(RETRY_DELAY_SECONDS)

            except Exception as e:
                logger.error(f"Send error (attempt {attempt}/{max_attempts}): {e}")
                if attempt < max_attempts:
                    time.sleep(RETRY_DELAY_SECONDS)

        logger.error(f"All {max_attempts} send attempts failed")
        return False


# Global router instance
_router = None


def get_router(dry_run: bool = False) -> NotificationRouter:
    """
    Get or create global router instance.

    Args:
        dry_run: Enable dry-run mode (notifications logged but not sent)

    Returns:
        NotificationRouter instance
    """
    global _router
    if _router is None:
        _router = NotificationRouter(dry_run=dry_run)
    return _router


def notify(
    title: str,
    message: str,
    priority: NotificationPriority = "info",
    subtitle: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to send notification.

    Args:
        title: Notification title
        message: Notification body
        priority: info|warning|critical (default: info)
        subtitle: Optional subtitle for macOS notification
        force: Skip rate limiting and deduplication checks (default: False)
        dry_run: Log notification but don't actually send (default: False)

    Returns:
        dict: Results from each channel including:
            - notification_center: bool (success)
            - telegram: bool (success)
            - voice: bool (success, if critical priority)
            - skipped: str|None (reason if notification was skipped)
            - dry_run: bool (whether this was a dry run)
    """
    router = get_router(dry_run=dry_run)
    return router.send(title, message, priority, subtitle, force=force)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Thanos Unified Notification System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send info notification (macOS only)
  %(prog)s info "Task Complete" "Code review finished"

  # Send warning (macOS + Telegram)
  %(prog)s warning "Low Energy" "Readiness: 45"

  # Send critical alert (macOS + Telegram + Voice)
  %(prog)s critical "System Alert" "Daemon crashed"

  # Test with dry-run mode
  %(prog)s --dry-run critical "Test Alert" "This won't actually send"

  # Force send (bypass rate limiting and deduplication)
  %(prog)s --force warning "Important" "Send immediately"

Priority Routing:
  info     → macOS Notification Center only
  warning  → macOS + Telegram
  critical → macOS + Telegram + Voice Alert
        """,
    )

    parser.add_argument(
        "priority",
        choices=["info", "warning", "critical"],
        help="Notification priority level",
    )
    parser.add_argument("title", help="Notification title")
    parser.add_argument("message", nargs="*", help="Notification message")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log notification but don't actually send",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip rate limiting and deduplication checks",
    )
    parser.add_argument(
        "--subtitle",
        help="Optional subtitle for macOS notification",
    )

    args = parser.parse_args()

    # Join message parts
    message = " ".join(args.message) if args.message else ""

    # Send notification
    results = notify(
        title=args.title,
        message=message,
        priority=args.priority,  # type: ignore
        subtitle=args.subtitle,
        force=args.force,
        dry_run=args.dry_run,
    )

    # Print results
    if results.get("dry_run"):
        print(f"[DRY-RUN] Would send: {args.title}")
    elif results.get("skipped"):
        print(f"⊘ Notification skipped: {results['skipped']}")
        sys.exit(1)
    else:
        print(f"✓ Notification sent: {args.title}")

    print(f"  Priority: {args.priority}")

    # Show which channels succeeded
    successful_channels = [k for k in ["notification_center", "telegram", "voice"] if results.get(k)]
    if successful_channels:
        print(f"  Channels: {', '.join(successful_channels)}")
    else:
        print("  Channels: none (all failed)")
        sys.exit(1)


if __name__ == "__main__":
    main()
