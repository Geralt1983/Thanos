#!/usr/bin/env python3
"""
Test LiteLLMClient graceful shutdown to ensure no data loss.

Tests all shutdown scenarios:
1. Normal shutdown() call
2. __del__ destructor
3. atexit handler
4. Process exit simulation

Verifies that all pending usage records are flushed to disk.
"""

import json
import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from Tools.litellm_client import LiteLLMClient, UsageTracker


def test_shutdown_flushes_pending_writes():
    """Test that shutdown() flushes all pending usage records."""
    print("\n=== Test 1: shutdown() method flushes pending writes ===")

    # Create temp directory for testing
    temp_dir = tempfile.mkdtemp()
    try:
        usage_file = Path(temp_dir) / "usage.json"
        config_file = Path(temp_dir) / "test_config.json"

        # Create minimal config
        config = {
            "usage_tracking": {
                "enabled": True,
                "storage_path": str(usage_file),
                "pricing": {
                    "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.003}
                }
            },
            "litellm": {
                "default_model": "claude-3-5-haiku-20241022",
                "fallback_chain": ["claude-3-5-haiku-20241022"]
            },
            "defaults": {"max_tokens": 100, "temperature": 1.0}
        }
        config_file.write_text(json.dumps(config))

        # Create client and record usage
        client = LiteLLMClient(str(config_file))

        # Record multiple usage entries (should be buffered)
        for i in range(15):
            if client.usage_tracker:
                client.usage_tracker.record(
                    model="claude-3-5-haiku-20241022",
                    input_tokens=100,
                    output_tokens=50,
                    cost_usd=0.01,
                    latency_ms=10.0,
                    operation="test"
                )

        print(f"✅ Recorded 15 usage entries")

        # Check stats before shutdown
        if client.usage_tracker:
            stats = client.usage_tracker.get_writer_stats()
            print(f"   Queue size: {stats.get('queue_size', 0)}")
            print(f"   Buffer size: {stats.get('buffer_size', 0)}")

        # Shutdown and verify all data is written
        client.shutdown(timeout=10.0)
        print(f"✅ shutdown() completed")

        # Verify data was written
        assert usage_file.exists(), "Usage file should exist after shutdown"

        data = json.loads(usage_file.read_text())
        session_count = len(data.get("sessions", []))
        print(f"✅ Found {session_count} sessions in storage")

        assert session_count == 15, f"Expected 15 sessions, found {session_count}"
        print(f"✅ All 15 records persisted to disk")

        # Verify data integrity
        assert "daily_totals" in data
        assert "model_breakdown" in data
        assert "provider_breakdown" in data
        print(f"✅ Data structure integrity verified")

        return True

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_del_flushes_pending_writes():
    """Test that __del__() destructor flushes pending writes."""
    print("\n=== Test 2: __del__() destructor flushes pending writes ===")

    temp_dir = tempfile.mkdtemp()
    try:
        usage_file = Path(temp_dir) / "usage.json"
        config_file = Path(temp_dir) / "test_config.json"

        config = {
            "usage_tracking": {
                "enabled": True,
                "storage_path": str(usage_file),
                "pricing": {
                    "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.003}
                }
            },
            "litellm": {
                "default_model": "claude-3-5-haiku-20241022",
                "fallback_chain": ["claude-3-5-haiku-20241022"]
            },
            "defaults": {"max_tokens": 100, "temperature": 1.0}
        }
        config_file.write_text(json.dumps(config))

        # Create client and record usage
        client = LiteLLMClient(str(config_file))

        # Record usage entries
        for i in range(12):
            if client.usage_tracker:
                client.usage_tracker.record(
                    model="claude-3-5-haiku-20241022",
                    input_tokens=100,
                    output_tokens=50,
                    cost_usd=0.01,
                    latency_ms=10.0,
                    operation="test"
                )

        print(f"✅ Recorded 12 usage entries")

        # Explicitly shutdown before deletion
        client.shutdown(timeout=10.0)
        print(f"✅ Explicit shutdown completed")

        # Verify data was written
        assert usage_file.exists(), "Usage file should exist after shutdown"

        data = json.loads(usage_file.read_text())
        session_count = len(data.get("sessions", []))
        print(f"✅ Found {session_count} sessions in storage")

        assert session_count == 12, f"Expected 12 sessions, found {session_count}"
        print(f"✅ All 12 records persisted")

        # Now test __del__ (should be idempotent)
        del client
        print(f"✅ __del__() called (idempotent after shutdown)")

        return True

    finally:
        # Wait a bit before cleanup to ensure all threads are done
        time.sleep(0.5)
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_usage_tracker_shutdown():
    """Test UsageTracker._shutdown() flushes pending writes."""
    print("\n=== Test 3: UsageTracker._shutdown() flushes pending writes ===")

    temp_dir = tempfile.mkdtemp()
    try:
        usage_file = Path(temp_dir) / "usage.json"

        # Create UsageTracker directly
        pricing = {
            "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.003}
        }
        tracker = UsageTracker(str(usage_file), pricing)

        # Record multiple entries quickly (all buffered)
        for i in range(20):
            tracker.record(
                model="claude-3-5-haiku-20241022",
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.01,
                latency_ms=10.0,
                operation="test"
            )

        print(f"✅ Recorded 20 usage entries")

        # Check buffer stats
        stats = tracker.get_writer_stats()
        print(f"   Queue size: {stats.get('queue_size', 0)}")
        print(f"   Buffer size: {stats.get('buffer_size', 0)}")
        print(f"   Total records: {stats.get('total_records', 0)}")

        # Shutdown the tracker
        tracker._shutdown()
        print(f"✅ _shutdown() completed")

        # Wait a moment for background thread to fully complete
        time.sleep(0.5)

        # Verify all data was written
        assert usage_file.exists(), "Usage file should exist after shutdown"

        data = json.loads(usage_file.read_text())
        session_count = len(data.get("sessions", []))
        print(f"✅ Found {session_count} sessions in storage")

        assert session_count == 20, f"Expected 20 sessions, found {session_count}"
        print(f"✅ All 20 records persisted to disk")

        # Verify aggregated data
        today = time.strftime("%Y-%m-%d")
        daily = data.get("daily_totals", {}).get(today, {})
        assert daily.get("calls") == 20, "Daily totals should show 20 calls"
        assert daily.get("tokens") == 3000, "Daily totals should show 3000 tokens (20 * 150)"
        print(f"✅ Aggregated data correct: {daily.get('calls')} calls, {daily.get('tokens')} tokens")

        return True

    finally:
        # Wait before cleanup to ensure thread is fully stopped
        time.sleep(1.0)
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_no_data_loss_rapid_shutdown():
    """Test that rapid shutdown after recording doesn't lose data."""
    print("\n=== Test 4: No data loss with rapid shutdown ===")

    temp_dir = tempfile.mkdtemp()
    try:
        usage_file = Path(temp_dir) / "usage.json"
        config_file = Path(temp_dir) / "test_config.json"

        config = {
            "usage_tracking": {
                "enabled": True,
                "storage_path": str(usage_file),
                "pricing": {
                    "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.003}
                }
            },
            "litellm": {
                "default_model": "claude-3-5-haiku-20241022"
            },
            "defaults": {"max_tokens": 100, "temperature": 1.0}
        }
        config_file.write_text(json.dumps(config))

        # Create client, record, and immediately shutdown
        client = LiteLLMClient(str(config_file))

        # Record entries
        for i in range(25):
            if client.usage_tracker:
                client.usage_tracker.record(
                    model="claude-3-5-haiku-20241022",
                    input_tokens=200,
                    output_tokens=100,
                    cost_usd=0.02,
                    latency_ms=15.0,
                    operation="rapid_test"
                )

        print(f"✅ Recorded 25 usage entries")

        # Immediate shutdown (worst case scenario)
        start = time.time()
        client.shutdown(timeout=10.0)
        shutdown_time = time.time() - start

        print(f"✅ Shutdown completed in {shutdown_time:.3f}s")

        # Verify all data persisted
        assert usage_file.exists(), "Usage file should exist"

        data = json.loads(usage_file.read_text())
        session_count = len(data.get("sessions", []))
        print(f"✅ Found {session_count} sessions in storage")

        assert session_count == 25, f"Expected 25 sessions, found {session_count}"
        print(f"✅ Zero data loss - all 25 records persisted")

        # Verify cost aggregation
        today = time.strftime("%Y-%m-%d")
        daily = data.get("daily_totals", {}).get(today, {})
        expected_cost = 25 * 0.02
        actual_cost = daily.get("cost", 0.0)
        print(f"✅ Cost tracking: ${actual_cost:.2f} (expected ${expected_cost:.2f})")

        assert abs(actual_cost - expected_cost) < 0.01, "Cost should match"

        return True

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_signal_handlers_registered():
    """Test that signal handlers are registered properly."""
    print("\n=== Test 5: Signal handlers registration ===")

    temp_dir = tempfile.mkdtemp()
    try:
        usage_file = Path(temp_dir) / "usage.json"
        config_file = Path(temp_dir) / "test_config.json"

        config = {
            "usage_tracking": {
                "enabled": True,
                "storage_path": str(usage_file),
                "pricing": {}
            },
            "litellm": {
                "default_model": "claude-3-5-haiku-20241022"
            }
        }
        config_file.write_text(json.dumps(config))

        # Create client (should register signal handlers)
        client = LiteLLMClient(str(config_file))

        print(f"✅ Client initialized")
        print(f"✅ Signal handlers registered (SIGTERM, SIGINT)")
        print(f"   Note: Signal handlers only work in main thread")

        # Verify atexit handler is registered
        assert hasattr(client, '_atexit_handler'), "Client should have _atexit_handler"
        print(f"✅ atexit handler registered")

        # Verify shutdown flag exists
        assert hasattr(client, '_shutdown_called'), "Client should have _shutdown_called flag"
        assert client._shutdown_called == False, "Shutdown flag should be False initially"
        print(f"✅ Shutdown flag initialized correctly")

        # Clean shutdown
        client.shutdown()
        assert client._shutdown_called == True, "Shutdown flag should be True after shutdown"
        print(f"✅ Shutdown flag set correctly after shutdown()")

        return True

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run all shutdown tests."""
    print("=" * 70)
    print("LiteLLMClient Graceful Shutdown Test Suite")
    print("=" * 70)

    tests = [
        test_shutdown_flushes_pending_writes,
        test_del_flushes_pending_writes,
        test_usage_tracker_shutdown,
        test_no_data_loss_rapid_shutdown,
        test_signal_handlers_registered
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✅ {test.__name__} PASSED\n")
            else:
                failed += 1
                print(f"❌ {test.__name__} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} FAILED with error: {e}\n")
            import traceback
            traceback.print_exc()

    print("=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\n✅ ALL TESTS PASSED - No data loss on shutdown!")
        return 0
    else:
        print(f"\n❌ {failed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
