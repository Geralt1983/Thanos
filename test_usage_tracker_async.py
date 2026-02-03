#!/usr/bin/env python3
"""
Test script to verify UsageTracker async functionality.
"""
import json
import time
import tempfile
from pathlib import Path
from Tools.litellm_client import UsageTracker

def test_async_writes():
    """Test that UsageTracker uses async writes correctly."""
    # Create temporary storage path
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_usage.json"

        # Initialize tracker
        pricing = {
            "claude": {"input": 0.015, "output": 0.075}
        }
        tracker = UsageTracker(str(storage_path), pricing)

        print("✓ UsageTracker initialized with AsyncUsageWriter")

        # Record multiple calls rapidly
        start_time = time.time()
        for i in range(10):
            tracker.record(
                model="anthropic/claude-sonnet-4-5",
                input_tokens=100,
                output_tokens=200,
                cost_usd=0.01,
                latency_ms=50.0,
                operation="test",
                metadata={"test_id": i}
            )
        record_time = time.time() - start_time

        print(f"✓ Recorded 10 entries in {record_time*1000:.2f}ms (avg: {record_time*100:.2f}ms per call)")

        # Verify non-blocking behavior (should be very fast)
        if record_time < 0.1:  # Should complete in <100ms for 10 calls
            print("✓ record() method is non-blocking (fast completion)")
        else:
            print(f"✗ record() seems to be blocking (took {record_time*1000:.2f}ms)")

        # Check writer stats before flush
        stats = tracker.get_writer_stats()
        print(f"✓ Writer stats before flush: {stats}")

        # Give background thread a moment to process the queue
        time.sleep(0.2)

        # Force flush
        flush_start = time.time()
        success = tracker.flush(timeout=5.0)
        flush_time = time.time() - flush_start

        if success:
            print(f"✓ Flush completed successfully in {flush_time*1000:.2f}ms")
        else:
            print("✗ Flush timed out")
            return False

        # Verify data was written
        if storage_path.exists():
            data = json.loads(storage_path.read_text())
            session_count = len(data.get("sessions", []))
            print(f"✓ Storage file created with {session_count} sessions")

            if session_count == 10:
                print("✓ All records written successfully")
            else:
                print(f"✗ Expected 10 records, found {session_count}")
                return False
        else:
            print("✗ Storage file not created")
            return False

        # Test get_summary and get_today
        summary = tracker.get_summary(days=1)
        print(f"✓ Summary: {summary['total_calls']} calls, ${summary['total_cost_usd']:.4f}")

        today = tracker.get_today()
        print(f"✓ Today's stats: {today['calls']} calls, {today['tokens']} tokens")

        # Cleanup (shutdown async writer)
        tracker._shutdown()
        print("✓ Graceful shutdown completed")

        return True

if __name__ == "__main__":
    print("Testing UsageTracker async functionality...")
    print("=" * 60)

    try:
        success = test_async_writes()
        if success:
            print("\n" + "=" * 60)
            print("✅ All tests passed!")
            exit(0)
        else:
            print("\n" + "=" * 60)
            print("❌ Some tests failed")
            exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
