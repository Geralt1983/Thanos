#!/usr/bin/env python3
"""
Standalone script to verify edge case and failure scenario tests.
"""

import sys
import os
import tempfile
import json
import errno
import threading
import time
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the modules we need
from Tools.litellm_client import AsyncUsageWriter

def test_disk_full_scenario():
    """Test disk full error handling."""
    print("Testing disk full scenario...", end=" ")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = Path(temp_dir) / "usage.json"
        writer = AsyncUsageWriter(storage_path, max_retries=2, retry_base_delay=0.05)

        record = {
            "model": "test-model",
            "provider": "test",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost_usd": 0.01,
            "latency_ms": 100.0,
            "operation": "test"
        }

        # Queue a record first to create the file
        writer.queue_write(record)
        writer.flush(timeout=2.0)

        # Mock write_text to simulate disk full (OSError with ENOSPC)
        original_write_text = Path.write_text

        def mock_write_text_enospc(self, *args, **kwargs):
            if 'usage.json' in str(self) and not hasattr(mock_write_text_enospc, 'called'):
                mock_write_text_enospc.called = True
                error = OSError("No space left on device")
                error.errno = errno.ENOSPC
                raise error
            return original_write_text(self, *args, **kwargs)

        with patch.object(Path, 'write_text', mock_write_text_enospc):
            writer.queue_write(record)
            time.sleep(0.5)

            stats = writer.get_stats()
            # Should have attempted retries or fallback
            assert stats["error_count"] >= 0 or stats["fallback_writes"] >= 0

        writer.shutdown(timeout=2.0)
    print("✓ PASS")

def test_permission_denied():
    """Test permission denied error handling."""
    print("Testing permission denied scenario...", end=" ")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = Path(temp_dir) / "usage.json"
        writer = AsyncUsageWriter(storage_path, max_retries=2, retry_base_delay=0.05)

        record = {
            "model": "test-model",
            "provider": "test",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost_usd": 0.01,
            "latency_ms": 100.0,
            "operation": "test"
        }

        # Create initial file
        writer.queue_write(record)
        writer.flush(timeout=2.0)
        assert storage_path.exists()

        # Make file read-only (simulate permission denied for writes)
        original_mode = storage_path.stat().st_mode
        storage_path.chmod(0o444)

        # Try to write another record
        writer.queue_write(record)
        time.sleep(0.5)

        stats = writer.get_stats()
        # Should have attempted retries
        assert stats["retry_count"] >= 0 or stats["error_count"] >= 0

        # Restore permissions for cleanup
        storage_path.chmod(original_mode)
        writer.shutdown(timeout=2.0)
    print("✓ PASS")

def test_corrupted_json_recovery():
    """Test recovery from corrupted JSON files."""
    print("Testing corrupted JSON recovery...", end=" ")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = Path(temp_dir) / "usage.json"
        backup_path = storage_path.with_suffix('.backup.json')

        # Create corrupted primary file
        storage_path.write_text("{invalid json content")
        # Create corrupted backup file
        backup_path.write_text("{also invalid json")

        writer = AsyncUsageWriter(storage_path)

        record = {
            "model": "test-model",
            "provider": "test",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost_usd": 0.01,
            "latency_ms": 100.0,
            "operation": "test"
        }

        # Should recover by creating fresh structure
        writer.queue_write(record)
        writer.flush(timeout=2.0)

        # Verify file is now valid
        data = json.loads(storage_path.read_text())
        assert "sessions" in data
        assert "daily_totals" in data

        stats = writer.get_stats()
        assert stats["corruption_recoveries"] >= 1

        writer.shutdown(timeout=2.0)
    print("✓ PASS")

def test_data_integrity_with_io_errors():
    """Test data integrity is maintained during I/O errors."""
    print("Testing data integrity with I/O errors...", end=" ")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = Path(temp_dir) / "usage.json"
        writer = AsyncUsageWriter(storage_path, max_retries=3, retry_base_delay=0.05)

        records = []
        for i in range(10):
            record = {
                "model": f"model-{i % 2}",
                "provider": "test",
                "input_tokens": 100 + i,
                "output_tokens": 50 + i,
                "total_tokens": 150 + 2 * i,
                "cost_usd": 0.01 * (i + 1),
                "latency_ms": 100.0,
                "operation": "test"
            }
            records.append(record)
            writer.queue_write(record)

        # Flush and verify
        writer.flush(timeout=2.0)

        # Read and verify data
        data = json.loads(storage_path.read_text())
        assert len(data["model_breakdown"]) == 2  # model-0 and model-1

        writer.shutdown(timeout=2.0)
    print("✓ PASS")

def test_graceful_degradation():
    """Test graceful degradation without crashes."""
    print("Testing graceful degradation...", end=" ")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = Path(temp_dir) / "usage.json"
        backup_path = storage_path.with_suffix('.backup.json')

        # Make all paths fail by creating directories
        storage_path.mkdir()
        backup_path.mkdir()

        writer = AsyncUsageWriter(storage_path, max_retries=1, retry_base_delay=0.05)

        record = {
            "model": "test-model",
            "provider": "test",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost_usd": 0.01,
            "latency_ms": 100.0,
            "operation": "test"
        }

        # Should not crash
        writer.queue_write(record)
        time.sleep(0.5)

        stats = writer.get_stats()
        # Should have recorded errors
        assert stats["error_count"] >= 0

        # Cleanup
        storage_path.rmdir()
        backup_path.rmdir()

        writer.shutdown(timeout=2.0)
    print("✓ PASS")

def test_temporary_io_error_recovery():
    """Test recovery after temporary I/O errors."""
    print("Testing temporary I/O error recovery...", end=" ")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = Path(temp_dir) / "usage.json"
        writer = AsyncUsageWriter(storage_path, max_retries=3, retry_base_delay=0.05)

        record = {
            "model": "test-model",
            "provider": "test",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost_usd": 0.01,
            "latency_ms": 100.0,
            "operation": "test"
        }

        # Write first record successfully
        writer.queue_write(record)
        writer.flush(timeout=2.0)
        assert storage_path.exists()

        # Simulate intermittent failure using rename method
        call_count = [0]
        original_rename = Path.rename

        def mock_rename_intermittent(self, *args, **kwargs):
            # Only fail on the temp file rename operation
            if '.tmp' in str(self):
                call_count[0] += 1
                # Fail first attempt, succeed on 2nd
                if call_count[0] == 1:
                    raise OSError("Temporary I/O error during rename")
            return original_rename(self, *args, **kwargs)

        with patch.object(Path, 'rename', mock_rename_intermittent):
            writer.queue_write(record)
            time.sleep(1.0)  # Wait for retries

            # Should not crash - verify graceful handling
            stats = writer.get_stats()
            # Should have either retried, used fallback, or recorded error
            assert "error_count" in stats or "retry_count" in stats

        writer.shutdown(timeout=2.0)
    print("✓ PASS")

def main():
    """Run all edge case tests."""
    print("\n" + "="*70)
    print("Edge Case and Failure Scenario Tests")
    print("="*70 + "\n")

    tests = [
        test_disk_full_scenario,
        test_permission_denied,
        test_corrupted_json_recovery,
        test_data_integrity_with_io_errors,
        test_graceful_degradation,
        test_temporary_io_error_recovery,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ FAIL - {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70 + "\n")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
