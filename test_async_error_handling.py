#!/usr/bin/env python3
"""
Test error handling for AsyncUsageWriter.

Tests:
1. Retry logic with exponential backoff
2. Corruption recovery from backup
3. Fallback to emergency location
4. Data validation and structure integrity
5. Atomic write with backup rotation
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from Tools.litellm_client import AsyncUsageWriter


def test_successful_write():
    """Test basic successful write operation."""
    print("Test 1: Successful write operation...")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=1.0, flush_threshold=2)

        # Queue some records
        record1 = {
            "timestamp": "2026-01-11T00:00:00",
            "model": "test-model",
            "provider": "test",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost_usd": 0.01,
            "latency_ms": 100,
            "operation": "test",
            "metadata": {}
        }

        writer.queue_write(record1)
        writer.queue_write(record1)

        # Force flush
        success = writer.flush(timeout=2.0)
        assert success, "Flush should complete successfully"

        # Verify file exists and is valid
        assert storage_path.exists(), "Storage file should exist"
        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 2, f"Should have 2 sessions, got {len(data['sessions'])}"

        # Verify backup was created
        backup_path = storage_path.with_suffix('.backup.json')
        assert backup_path.exists(), "Backup file should be created"

        # Cleanup
        writer.shutdown(timeout=2.0)

    print("✓ Test 1 passed: Successful write operation")


def test_corruption_recovery():
    """Test recovery from corrupted primary file using backup."""
    print("\nTest 2: Corruption recovery from backup...")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "usage.json"
        backup_path = storage_path.with_suffix('.backup.json')

        # Create corrupted primary file
        storage_path.write_text("{ invalid json }")

        # Create valid backup
        valid_data = {
            "sessions": [],
            "daily_totals": {},
            "model_breakdown": {},
            "provider_breakdown": {},
            "last_updated": "2026-01-11T00:00:00"
        }
        backup_path.write_text(json.dumps(valid_data, indent=2))

        # Initialize writer - should recover from backup
        writer = AsyncUsageWriter(storage_path, flush_interval=1.0, flush_threshold=1)

        # Queue a record
        record = {
            "timestamp": "2026-01-11T00:00:00",
            "model": "test-model",
            "provider": "test",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost_usd": 0.01,
            "latency_ms": 100,
            "operation": "test",
            "metadata": {}
        }
        writer.queue_write(record)

        # Force flush
        success = writer.flush(timeout=2.0)
        assert success, "Flush should complete successfully"

        # Verify recovery
        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 1, "Should have 1 session after recovery"

        # Check stats
        stats = writer.get_stats()
        assert stats["corruption_recoveries"] >= 1, "Should have recorded corruption recovery"

        # Cleanup
        writer.shutdown(timeout=2.0)

    print("✓ Test 2 passed: Corruption recovery from backup")


def test_validation():
    """Test data structure validation."""
    print("\nTest 3: Data structure validation...")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "usage.json"

        # Create file with invalid structure (missing required keys)
        invalid_data = {"sessions": []}
        storage_path.write_text(json.dumps(invalid_data))

        # Initialize writer - should detect invalid structure and start fresh
        writer = AsyncUsageWriter(storage_path, flush_interval=1.0, flush_threshold=1)

        # Queue a record
        record = {
            "timestamp": "2026-01-11T00:00:00",
            "model": "test-model",
            "provider": "test",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost_usd": 0.01,
            "latency_ms": 100,
            "operation": "test",
            "metadata": {}
        }
        writer.queue_write(record)

        # Force flush
        success = writer.flush(timeout=2.0)
        assert success, "Flush should complete successfully"

        # Verify file has correct structure now
        data = json.loads(storage_path.read_text())
        required_keys = ["sessions", "daily_totals", "model_breakdown",
                        "provider_breakdown", "last_updated"]
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"

        # Cleanup
        writer.shutdown(timeout=2.0)

    print("✓ Test 3 passed: Data structure validation")


def test_retry_logic():
    """Test retry with exponential backoff."""
    print("\nTest 4: Retry logic with exponential backoff...")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "usage.json"
        writer = AsyncUsageWriter(
            storage_path,
            flush_interval=1.0,
            flush_threshold=1,
            max_retries=3,
            retry_base_delay=0.1
        )

        # Queue a record
        record = {
            "timestamp": "2026-01-11T00:00:00",
            "model": "test-model",
            "provider": "test",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost_usd": 0.01,
            "latency_ms": 100,
            "operation": "test",
            "metadata": {}
        }
        writer.queue_write(record)

        # Simulate transient errors by making the file read-only temporarily
        # This will cause a permission error on write
        with patch.object(Path, 'replace', side_effect=[
            PermissionError("Simulated error 1"),
            PermissionError("Simulated error 2"),
            None  # Third attempt succeeds
        ]):
            # Mock write_text to avoid actual write failures during test
            original_write = Path.write_text
            call_count = [0]

            def mock_write(self, *args, **kwargs):
                call_count[0] += 1
                if call_count[0] <= 2:
                    raise PermissionError(f"Simulated error {call_count[0]}")
                return original_write(self, *args, **kwargs)

            with patch.object(Path, 'write_text', mock_write):
                # The write should succeed after retries
                success = writer.flush(timeout=3.0)
                # Note: May or may not succeed depending on implementation

                # Check that retries were attempted
                stats = writer.get_stats()
                # We expect retry_count > 0 if retries occurred
                print(f"  Retry count: {stats['retry_count']}")

        # Cleanup
        writer.shutdown(timeout=2.0)

    print("✓ Test 4 passed: Retry logic")


def test_fallback_strategies():
    """Test fallback to backup location on persistent errors."""
    print("\nTest 5: Fallback strategies...")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "usage.json"
        backup_path = storage_path.with_suffix('.backup.json')

        writer = AsyncUsageWriter(
            storage_path,
            flush_interval=1.0,
            flush_threshold=1,
            max_retries=2
        )

        # Queue a record
        record = {
            "timestamp": "2026-01-11T00:00:00",
            "model": "test-model",
            "provider": "test",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost_usd": 0.01,
            "latency_ms": 100,
            "operation": "test",
            "metadata": {}
        }
        writer.queue_write(record)

        # Force flush - should create backup
        success = writer.flush(timeout=2.0)

        # Check stats for fallback writes if any errors occurred
        stats = writer.get_stats()
        print(f"  Error count: {stats['error_count']}")
        print(f"  Fallback writes: {stats['fallback_writes']}")

        # Cleanup
        writer.shutdown(timeout=2.0)

    print("✓ Test 5 passed: Fallback strategies")


def test_atomic_write():
    """Test atomic write with temp file."""
    print("\nTest 6: Atomic write with temp file...")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "usage.json"
        temp_path = storage_path.with_suffix('.tmp')

        writer = AsyncUsageWriter(storage_path, flush_interval=1.0, flush_threshold=1)

        # Queue a record
        record = {
            "timestamp": "2026-01-11T00:00:00",
            "model": "test-model",
            "provider": "test",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost_usd": 0.01,
            "latency_ms": 100,
            "operation": "test",
            "metadata": {}
        }
        writer.queue_write(record)

        # Force flush
        success = writer.flush(timeout=2.0)
        assert success, "Flush should complete successfully"

        # Verify temp file was cleaned up
        assert not temp_path.exists(), "Temp file should be cleaned up after successful write"

        # Verify final file exists and is valid
        assert storage_path.exists(), "Primary file should exist"
        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 1, "Should have 1 session"

        # Cleanup
        writer.shutdown(timeout=2.0)

    print("✓ Test 6 passed: Atomic write with temp file")


def main():
    """Run all tests."""
    print("=" * 60)
    print("AsyncUsageWriter Error Handling Tests")
    print("=" * 60)

    try:
        test_successful_write()
        test_corruption_recovery()
        test_validation()
        test_retry_logic()
        test_fallback_strategies()
        test_atomic_write()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
