#!/usr/bin/env python3
"""
Test script for Operator alerters.

Usage:
    # Test all alerters in dry-run mode
    python Operator/alerters/test_alerters.py

    # Test specific alerter
    python Operator/alerters/test_alerters.py --alerter telegram

    # Test with actual sending (requires credentials)
    python Operator/alerters/test_alerters.py --no-dry-run
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Operator.alerters import (
    Alert,
    TelegramAlerter,
    NotificationAlerter,
    JournalAlerter
)


async def test_telegram_alerter(dry_run: bool = True):
    """Test Telegram alerter with various severity levels."""
    print("\n=== Testing Telegram Alerter ===")

    alerter = TelegramAlerter(
        min_severity="info",
        dry_run=dry_run
    )

    print(f"Enabled: {alerter.is_enabled()}")
    print(f"Dry-run: {dry_run}")

    # Test alerts at different severity levels
    test_alerts = [
        Alert(
            title="System Info",
            message="Operator daemon started successfully",
            severity="info",
            source_type="health",
            source_id="daemon_startup"
        ),
        Alert(
            title="Low Readiness",
            message="Your readiness is 62. Consider lighter tasks today.",
            severity="warning",
            source_type="health",
            source_id="readiness_check"
        ),
        Alert(
            title="Task Overdue",
            message="Memphis optimization report is 2 days overdue",
            severity="high",
            source_type="task",
            source_id="task_123"
        ),
        Alert(
            title="Critical Health Alert",
            message="Your readiness is 48. You're at risk of burnout. Rest today.",
            severity="critical",
            source_type="health",
            source_id="readiness_check"
        )
    ]

    for alert in test_alerts:
        print(f"\nSending {alert.severity} alert: {alert.title}")
        success = await alerter.send(alert)
        print(f"  Result: {'✓ Success' if success else '✗ Failed'}")

        # Small delay to avoid rate limiting in real mode
        if not dry_run:
            await asyncio.sleep(2)


async def test_notification_alerter(dry_run: bool = True):
    """Test macOS notification alerter."""
    print("\n=== Testing macOS Notification Alerter ===")

    alerter = NotificationAlerter(
        min_severity="warning",
        dry_run=dry_run
    )

    print(f"Enabled: {alerter.is_enabled()}")
    print(f"Dry-run: {dry_run}")

    # Test alerts
    test_alerts = [
        Alert(
            title="Low Energy Warning",
            message="Readiness score is 58. Take it easy today.",
            severity="warning",
            source_type="health",
            source_id="readiness_check"
        ),
        Alert(
            title="Deadline Alert",
            message="3 tasks due today",
            severity="high",
            source_type="task",
            source_id="deadline_check"
        ),
        Alert(
            title="Critical System Alert",
            message="Circuit breaker tripped - MCP unavailable",
            severity="critical",
            source_type="health",
            source_id="circuit_breaker"
        )
    ]

    for alert in test_alerts:
        print(f"\nSending {alert.severity} notification: {alert.title}")
        success = await alerter.send(alert)
        print(f"  Result: {'✓ Success' if success else '✗ Failed'}")

        # Delay between notifications
        if not dry_run:
            await asyncio.sleep(1)


async def test_journal_alerter(dry_run: bool = True):
    """Test journal alerter."""
    print("\n=== Testing Journal Alerter ===")

    alerter = JournalAlerter(dry_run=dry_run)

    print(f"Enabled: {alerter.is_enabled()}")
    print(f"Dry-run: {dry_run}")

    # Test alerts
    test_alerts = [
        Alert(
            title="Info Log",
            message="Check cycle completed successfully",
            severity="info",
            source_type="health",
            source_id="check_cycle"
        ),
        Alert(
            title="Warning Log",
            message="Health check took longer than expected (2.3s)",
            severity="warning",
            source_type="health",
            source_id="performance"
        ),
        Alert(
            title="Critical Log",
            message="Database connection failed - using fallback",
            severity="critical",
            source_type="health",
            source_id="database"
        )
    ]

    for alert in test_alerts:
        print(f"\nLogging {alert.severity} alert: {alert.title}")
        success = await alerter.send(alert)
        print(f"  Result: {'✓ Success' if success else '✗ Failed'}")


async def test_all_alerters(dry_run: bool = True):
    """Test all alerters together."""
    print("\n" + "="*60)
    print("TESTING ALL ALERTERS")
    print("="*60)

    await test_telegram_alerter(dry_run)
    await test_notification_alerter(dry_run)
    await test_journal_alerter(dry_run)

    print("\n" + "="*60)
    print("ALL TESTS COMPLETE")
    print("="*60)


async def main():
    """Run alerter tests."""
    parser = argparse.ArgumentParser(description="Test Operator alerters")
    parser.add_argument(
        "--alerter",
        choices=["telegram", "notification", "journal", "all"],
        default="all",
        help="Which alerter to test"
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually send alerts (requires credentials)"
    )

    args = parser.parse_args()
    dry_run = not args.no_dry_run

    if dry_run:
        print("Running in DRY-RUN mode (no actual sending)")
    else:
        print("WARNING: Running with ACTUAL SENDING enabled")
        print("Make sure you have proper credentials configured!")
        await asyncio.sleep(2)

    if args.alerter == "telegram":
        await test_telegram_alerter(dry_run)
    elif args.alerter == "notification":
        await test_notification_alerter(dry_run)
    elif args.alerter == "journal":
        await test_journal_alerter(dry_run)
    else:
        await test_all_alerters(dry_run)


if __name__ == "__main__":
    asyncio.run(main())
