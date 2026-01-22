#!/usr/bin/env python3
"""
Test script for Thanos Notification System.

Demonstrates rate limiting, deduplication, and retry logic.
"""

import time
from notifications import NotificationRouter

def test_deduplication():
    """Test that duplicate notifications are suppressed."""
    print("\n=== Testing Deduplication ===")
    router = NotificationRouter(dry_run=True)

    # First notification should send
    result1 = router.send("Test", "Duplicate message", "info")
    print(f"1st send: skipped={result1.get('skipped')}")

    # Immediate duplicate should be suppressed
    result2 = router.send("Test", "Duplicate message", "info")
    print(f"2nd send (immediate): skipped={result2.get('skipped')}")

    # Different message should send
    result3 = router.send("Test", "Different message", "info")
    print(f"3rd send (different): skipped={result3.get('skipped')}")

    # Force flag should bypass deduplication
    result4 = router.send("Test", "Duplicate message", "info", force=True)
    print(f"4th send (forced): skipped={result4.get('skipped')}")


def test_rate_limiting():
    """Test that rate limiting works correctly."""
    print("\n=== Testing Rate Limiting ===")
    router = NotificationRouter(dry_run=True)

    # Send 10 notifications (should all succeed)
    for i in range(10):
        result = router.send(f"Message {i}", f"Content {i}", "info")
        print(f"Message {i}: skipped={result.get('skipped')}")

    # 11th should be rate limited
    result = router.send("Message 11", "Should be rate limited", "info")
    print(f"Message 11 (rate limited): skipped={result.get('skipped')}")

    # Force flag should bypass rate limiting
    result = router.send("Message 12", "Forced send", "info", force=True)
    print(f"Message 12 (forced): skipped={result.get('skipped')}")


def test_priority_routing():
    """Test that priority routing works correctly."""
    print("\n=== Testing Priority Routing ===")
    router = NotificationRouter(dry_run=True)

    # Info: only notification_center
    result = router.send("Info Test", "Info priority", "info")
    print(f"Info: {[k for k in ['notification_center', 'telegram', 'voice'] if result.get(k)]}")

    # Warning: notification_center + telegram
    result = router.send("Warning Test", "Warning priority", "warning")
    print(f"Warning: {[k for k in ['notification_center', 'telegram', 'voice'] if result.get(k)]}")

    # Critical: all channels
    result = router.send("Critical Test", "Critical priority", "critical")
    print(f"Critical: {[k for k in ['notification_center', 'telegram', 'voice'] if result.get(k)]}")


def test_retry_logic():
    """Test retry logic with a failing send function."""
    print("\n=== Testing Retry Logic ===")

    # Create a router with mock failing sends
    router = NotificationRouter(dry_run=False)

    attempts = [0]
    def mock_send():
        """Mock send that fails first 2 times."""
        attempts[0] += 1
        print(f"  Attempt {attempts[0]}")
        if attempts[0] < 3:
            return False  # Fail first 2 times
        return True  # Succeed on 3rd attempt

    success = router._send_with_retry(mock_send, max_attempts=3)
    print(f"Result after retries: success={success}")


if __name__ == "__main__":
    test_deduplication()
    test_rate_limiting()
    test_priority_routing()
    test_retry_logic()

    print("\n=== All Tests Complete ===")
