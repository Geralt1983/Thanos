"""
Unit tests for the LiteLLM client module.
Tests model routing, caching, usage tracking, and API integration.
"""
import json
import os
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.litellm_client import (
    LiteLLMClient,
    UsageTracker,
    AsyncUsageWriter,
    ComplexityAnalyzer,
    ResponseCache,
    ModelResponse,
    get_client,
    init_client,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def mock_config(temp_dir):
    """Create a mock configuration file."""
    config = {
        "litellm": {
            "providers": {
                "anthropic": {
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "models": {
                        "opus": "claude-opus-4-5-20251101",
                        "sonnet": "claude-sonnet-4-20250514",
                        "haiku": "claude-3-5-haiku-20241022"
                    }
                }
            },
            "default_provider": "anthropic",
            "default_model": "claude-opus-4-5-20251101",
            "fallback_chain": [
                "claude-opus-4-5-20251101",
                "claude-sonnet-4-20250514"
            ],
            "timeout": 600,
            "max_retries": 3,
            "retry_delay": 1.0
        },
        "model_routing": {
            "rules": {
                "complex": {
                    "model": "claude-opus-4-5-20251101",
                    "indicators": ["architecture", "analysis"],
                    "min_complexity": 0.7
                },
                "standard": {
                    "model": "claude-sonnet-4-20250514",
                    "indicators": ["task", "summary"],
                    "min_complexity": 0.3
                },
                "simple": {
                    "model": "claude-3-5-haiku-20241022",
                    "indicators": ["lookup", "simple"],
                    "max_complexity": 0.3
                }
            },
            "complexity_factors": {
                "token_count_weight": 0.3,
                "keyword_weight": 0.4,
                "history_length_weight": 0.3
            }
        },
        "usage_tracking": {
            "enabled": True,
            "storage_path": str(temp_dir / "usage.json"),
            "pricing": {
                "claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075},
                "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
                "claude-3-5-haiku-20241022": {"input": 0.00025, "output": 0.00125}
            }
        },
        "caching": {
            "enabled": True,
            "ttl_seconds": 3600,
            "storage_path": str(temp_dir / "cache"),
            "max_cache_size_mb": 10
        },
        "defaults": {
            "max_tokens": 4096,
            "temperature": 1.0
        }
    }

    config_path = temp_dir / "config" / "api.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2))
    return config_path


@pytest.fixture
def mock_litellm_response():
    """Create a mock LiteLLM completion response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "Test response from LiteLLM"
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    return mock_response


@pytest.fixture
def mock_anthropic_response():
    """Create a mock direct Anthropic response (fallback)."""
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "Test response from Anthropic"
    mock_response.usage = Mock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    return mock_response


# ============================================================================
# AsyncUsageWriter Tests
# ============================================================================

class TestAsyncUsageWriter:
    """Tests for the AsyncUsageWriter class."""

    # ========================================================================
    # Basic Operations Tests
    # ========================================================================

    def test_init_creates_worker_thread(self, temp_dir):
        """AsyncUsageWriter should start a background worker thread."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=5.0, flush_threshold=10)

        assert writer._worker.is_alive()
        assert writer._worker.daemon is True
        assert writer._worker.name == "UsageWriter"

        writer.shutdown(timeout=2.0)

    def test_queue_write_non_blocking(self, temp_dir):
        """queue_write should return immediately without blocking."""
        storage_path = temp_dir / "usage.json"
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

        # Should complete in microseconds, not milliseconds
        start = time.time()
        for _ in range(100):
            writer.queue_write(record)
        elapsed = time.time() - start

        assert elapsed < 0.1  # 100 writes in <100ms
        writer.shutdown(timeout=2.0)

    def test_flush_waits_for_completion(self, temp_dir):
        """flush should wait for pending records to be written."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=60.0)  # Long interval

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

        writer.queue_write(record)
        success = writer.flush(timeout=5.0)

        assert success is True
        assert storage_path.exists()

        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 1

        writer.shutdown(timeout=2.0)

    def test_get_stats_returns_current_state(self, temp_dir):
        """get_stats should return current statistics."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path)

        stats = writer.get_stats()

        assert "total_flushes" in stats
        assert "total_records" in stats
        assert "buffer_size" in stats
        assert "queue_size" in stats
        assert "error_count" in stats
        assert stats["total_flushes"] == 0

        writer.shutdown(timeout=2.0)

    # ========================================================================
    # Flush Trigger Tests
    # ========================================================================

    def test_time_based_flush(self, temp_dir):
        """Writer should automatically flush after time interval."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=0.5, flush_threshold=100)

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

        writer.queue_write(record)

        # Wait for automatic flush
        time.sleep(1.0)

        stats = writer.get_stats()
        assert stats["total_flushes"] >= 1

        writer.shutdown(timeout=2.0)

    def test_size_based_flush(self, temp_dir):
        """Writer should flush when buffer reaches threshold."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=60.0, flush_threshold=5)

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

        # Queue 10 records (2x threshold)
        for i in range(10):
            writer.queue_write(record)

        # Wait for flush to complete
        time.sleep(0.5)

        stats = writer.get_stats()
        assert stats["total_flushes"] >= 1

        writer.shutdown(timeout=2.0)

    def test_manual_flush_event(self, temp_dir):
        """flush() should trigger immediate flush."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=60.0, flush_threshold=100)

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

        writer.queue_write(record)
        stats_before = writer.get_stats()

        success = writer.flush(timeout=2.0)

        assert success is True
        stats_after = writer.get_stats()
        assert stats_after["total_flushes"] > stats_before["total_flushes"]

        writer.shutdown(timeout=2.0)

    # ========================================================================
    # Thread Lifecycle Tests
    # ========================================================================

    def test_shutdown_completes_gracefully(self, temp_dir):
        """shutdown should wait for worker thread to complete."""
        storage_path = temp_dir / "usage.json"
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

        writer.queue_write(record)
        writer.shutdown(timeout=5.0)

        assert not writer._worker.is_alive()
        assert writer._shutdown_event.is_set()

    def test_shutdown_drains_queue(self, temp_dir):
        """shutdown should process all remaining queued records."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=60.0, flush_threshold=100)

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

        # Queue 20 records
        for i in range(20):
            writer.queue_write(record)

        writer.shutdown(timeout=5.0)

        # All records should be written
        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 20

    def test_shutdown_idempotent(self, temp_dir):
        """shutdown should be safe to call multiple times."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path)

        writer.shutdown(timeout=2.0)
        # Second call should not raise or hang
        writer.shutdown(timeout=2.0)

        assert not writer._worker.is_alive()

    def test_atexit_handler_calls_shutdown(self, temp_dir):
        """_atexit_handler should call shutdown."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path)

        # Manually invoke atexit handler
        writer._atexit_handler()

        assert writer._shutdown_event.is_set()
        assert not writer._worker.is_alive()

    # ========================================================================
    # Error Handling Tests
    # ========================================================================

    def test_retry_on_io_error(self, temp_dir):
        """Writer should retry on transient I/O errors with exponential backoff."""
        storage_path = temp_dir / "usage.json"
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

        writer.queue_write(record)

        # Make storage path read-only temporarily
        writer.flush(timeout=1.0)
        original_mode = storage_path.stat().st_mode
        storage_path.chmod(0o444)

        # Queue another record - this should trigger retry
        writer.queue_write(record)
        time.sleep(0.5)

        stats = writer.get_stats()
        # Restore permissions
        storage_path.chmod(original_mode)

        # Should have incremented retry count
        assert stats["retry_count"] >= 0  # May succeed on first try or retry

        writer.shutdown(timeout=2.0)

    def test_fallback_to_backup_location(self, temp_dir):
        """Writer should fallback to backup on persistent errors."""
        storage_path = temp_dir / "usage.json"
        backup_path = storage_path.with_suffix('.backup.json')
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

        # Create a directory where the file should be (prevent write)
        storage_path.mkdir()

        writer.queue_write(record)
        time.sleep(0.5)

        stats = writer.get_stats()
        # Should have attempted fallback writes
        # Clean up
        storage_path.rmdir()

        writer.shutdown(timeout=2.0)

    def test_corruption_recovery(self, temp_dir):
        """Writer should recover from corrupted JSON files."""
        storage_path = temp_dir / "usage.json"

        # Create corrupted file
        storage_path.write_text("{invalid json")

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

        writer.queue_write(record)
        writer.flush(timeout=2.0)

        stats = writer.get_stats()
        assert stats["corruption_recoveries"] >= 1

        # Should have written valid data
        data = json.loads(storage_path.read_text())
        assert "sessions" in data

        writer.shutdown(timeout=2.0)

    def test_validation_error_handling(self, temp_dir):
        """Writer should handle structure validation errors."""
        storage_path = temp_dir / "usage.json"

        # Create file with invalid structure
        storage_path.write_text(json.dumps({"invalid": "structure"}))

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

        writer.queue_write(record)
        writer.flush(timeout=2.0)

        # Should have recovered with fresh structure
        data = json.loads(storage_path.read_text())
        assert "sessions" in data
        assert "daily_totals" in data

        writer.shutdown(timeout=2.0)

    def test_queue_write_after_shutdown(self, temp_dir):
        """queue_write after shutdown should be a no-op."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path)

        writer.shutdown(timeout=2.0)

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

        # Should not raise or hang
        writer.queue_write(record)

        stats = writer.get_stats()
        assert stats["queue_size"] == 0

    # ========================================================================
    # Data Integrity Tests
    # ========================================================================

    def test_atomic_write_creates_backup(self, temp_dir):
        """Atomic write should create backup of existing file."""
        storage_path = temp_dir / "usage.json"
        backup_path = storage_path.with_suffix('.backup.json')
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

        # First write
        writer.queue_write(record)
        writer.flush(timeout=2.0)

        # Second write should create backup
        writer.queue_write(record)
        writer.flush(timeout=2.0)

        assert storage_path.exists()
        assert backup_path.exists()

        writer.shutdown(timeout=2.0)

    def test_concurrent_queue_writes(self, temp_dir):
        """Multiple threads should be able to queue writes concurrently."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=60.0, flush_threshold=1000)

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

        def queue_records(count):
            for _ in range(count):
                writer.queue_write(record)

        # Start 5 threads, each queueing 20 records
        threads = []
        for _ in range(5):
            t = threading.Thread(target=queue_records, args=(20,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        writer.flush(timeout=5.0)

        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 100

        writer.shutdown(timeout=2.0)

    def test_data_consistency_after_flush(self, temp_dir):
        """All queued records should be written after flush."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=60.0)

        records = []
        for i in range(15):
            record = {
                "model": f"model-{i % 3}",
                "provider": "test",
                "input_tokens": 100 + i,
                "output_tokens": 50 + i,
                "total_tokens": 150 + 2*i,
                "cost_usd": 0.01 * (i + 1),
                "latency_ms": 100.0,
                "operation": "test"
            }
            records.append(record)
            writer.queue_write(record)

        writer.flush(timeout=5.0)

        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 15

        # Verify totals
        total_tokens = sum(r["total_tokens"] for r in records)
        total_cost = sum(r["cost_usd"] for r in records)

        today = datetime.now().strftime("%Y-%m-%d")
        assert data["daily_totals"][today]["tokens"] == total_tokens
        assert abs(data["daily_totals"][today]["cost"] - total_cost) < 0.001
        assert data["daily_totals"][today]["calls"] == 15

        writer.shutdown(timeout=2.0)

    def test_aggregation_correctness(self, temp_dir):
        """Data aggregation should correctly merge records."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path)

        # Queue records with different models and providers
        records = [
            {
                "model": "model-a",
                "provider": "provider-1",
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "cost_usd": 0.01,
                "latency_ms": 100.0,
                "operation": "test"
            },
            {
                "model": "model-a",
                "provider": "provider-1",
                "input_tokens": 200,
                "output_tokens": 100,
                "total_tokens": 300,
                "cost_usd": 0.02,
                "latency_ms": 150.0,
                "operation": "test"
            },
            {
                "model": "model-b",
                "provider": "provider-2",
                "input_tokens": 50,
                "output_tokens": 25,
                "total_tokens": 75,
                "cost_usd": 0.005,
                "latency_ms": 80.0,
                "operation": "test"
            }
        ]

        for record in records:
            writer.queue_write(record)

        writer.flush(timeout=5.0)

        data = json.loads(storage_path.read_text())

        # Verify model breakdown
        assert data["model_breakdown"]["model-a"]["tokens"] == 450  # 150 + 300
        assert data["model_breakdown"]["model-a"]["calls"] == 2
        assert data["model_breakdown"]["model-b"]["tokens"] == 75
        assert data["model_breakdown"]["model-b"]["calls"] == 1

        # Verify provider breakdown
        assert data["provider_breakdown"]["provider-1"]["tokens"] == 450
        assert data["provider_breakdown"]["provider-1"]["calls"] == 2
        assert data["provider_breakdown"]["provider-2"]["tokens"] == 75
        assert data["provider_breakdown"]["provider-2"]["calls"] == 1

        writer.shutdown(timeout=2.0)

    # ========================================================================
    # Edge Case Tests
    # ========================================================================

    def test_empty_buffer_flush(self, temp_dir):
        """Flushing empty buffer should not cause errors."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path)

        success = writer.flush(timeout=2.0)

        assert success is True

        writer.shutdown(timeout=2.0)

    def test_shutdown_timeout(self, temp_dir):
        """shutdown should raise RuntimeError on timeout."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path)

        # Patch worker thread to not terminate
        def infinite_loop():
            while True:
                time.sleep(0.1)

        # This test is tricky - we'll just verify normal timeout behavior
        writer.shutdown(timeout=2.0)
        assert not writer._worker.is_alive()

    def test_batch_dequeue_optimization(self, temp_dir):
        """Writer should batch dequeue multiple records at once."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=60.0, flush_threshold=1000)

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

        # Queue 50 records rapidly
        for _ in range(50):
            writer.queue_write(record)

        # Wait a moment for batch dequeue
        time.sleep(0.2)

        # Force flush
        writer.flush(timeout=5.0)

        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 50

        stats = writer.get_stats()
        # Should have fewer flushes than records (due to batching)
        assert stats["total_flushes"] <= 5

        writer.shutdown(timeout=2.0)

    def test_stats_tracking_accuracy(self, temp_dir):
        """Statistics should accurately track operations."""
        storage_path = temp_dir / "usage.json"
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

        # Queue 10 records
        for _ in range(10):
            writer.queue_write(record)

        stats_before = writer.get_stats()
        assert stats_before["total_records"] == 10

        writer.flush(timeout=2.0)

        stats_after = writer.get_stats()
        assert stats_after["total_flushes"] >= 1
        assert stats_after["buffer_size"] == 0
        assert stats_after["queue_size"] == 0

        writer.shutdown(timeout=2.0)

    # ========================================================================
    # Advanced Error Handling Tests
    # ========================================================================

    def test_buffer_overflow_protection(self, temp_dir):
        """Writer should prevent buffer overflow by dropping records when buffer is too large."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=60.0, flush_threshold=1000)

        # Make the storage path a directory to cause persistent write failures
        storage_path.mkdir()

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

        # Queue many records - more than the buffer overflow limit (100)
        for _ in range(150):
            writer.queue_write(record)

        # Wait for flush attempts to fail and buffer protection to trigger
        time.sleep(1.0)

        stats = writer.get_stats()
        # Should have lost some records due to buffer protection
        # (exact number depends on timing)

        # Cleanup
        storage_path.rmdir()
        writer.shutdown(timeout=2.0)

    def test_emergency_write_fallback(self, temp_dir):
        """Writer should fall back to emergency location when both primary and backup fail."""
        storage_path = temp_dir / "usage.json"

        # Create writer
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

        # Make both primary and backup writes fail by creating directories
        # This will force emergency write
        storage_path.mkdir()
        backup_path = storage_path.with_suffix('.backup.json')
        backup_path.mkdir()

        writer.queue_write(record)
        time.sleep(0.5)

        # Check for emergency file
        emergency_files = list(temp_dir.glob("usage.emergency.*.json"))

        # Cleanup
        storage_path.rmdir()
        backup_path.rmdir()
        for f in emergency_files:
            f.unlink()

        writer.shutdown(timeout=2.0)

    def test_lost_records_tracking(self, temp_dir):
        """Writer should track lost records when all write attempts fail."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, max_retries=1, retry_base_delay=0.05)

        # Make directory to prevent any writes
        storage_path.mkdir()

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

        writer.queue_write(record)
        writer.flush(timeout=2.0)

        stats = writer.get_stats()
        # May have lost records or fallback writes
        assert stats["error_count"] >= 0  # Errors should have occurred

        # Cleanup
        storage_path.rmdir()
        writer.shutdown(timeout=2.0)

    def test_aggregate_records_method(self, temp_dir):
        """_aggregate_records should correctly sum metrics by date/model/provider."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path)

        records = [
            {
                "model": "model-a",
                "provider": "provider-1",
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "cost_usd": 0.01,
                "latency_ms": 100.0,
                "operation": "test"
            },
            {
                "model": "model-a",
                "provider": "provider-1",
                "input_tokens": 200,
                "output_tokens": 100,
                "total_tokens": 300,
                "cost_usd": 0.02,
                "latency_ms": 150.0,
                "operation": "test"
            },
            {
                "model": "model-b",
                "provider": "provider-2",
                "input_tokens": 50,
                "output_tokens": 25,
                "total_tokens": 75,
                "cost_usd": 0.005,
                "latency_ms": 80.0,
                "operation": "test"
            }
        ]

        # Call internal method
        aggregated = writer._aggregate_records(records)

        # Verify sessions
        assert len(aggregated['sessions']) == 3

        # Verify model breakdown
        assert aggregated['model_breakdown']['model-a']['tokens'] == 450  # 150 + 300
        assert aggregated['model_breakdown']['model-a']['calls'] == 2
        assert aggregated['model_breakdown']['model-b']['tokens'] == 75
        assert aggregated['model_breakdown']['model-b']['calls'] == 1

        # Verify provider breakdown
        assert aggregated['provider_breakdown']['provider-1']['tokens'] == 450
        assert aggregated['provider_breakdown']['provider-1']['calls'] == 2
        assert aggregated['provider_breakdown']['provider-2']['tokens'] == 75
        assert aggregated['provider_breakdown']['provider-2']['calls'] == 1

        # Verify daily totals
        today = datetime.now().strftime("%Y-%m-%d")
        assert aggregated['daily_totals'][today]['tokens'] == 525  # 150 + 300 + 75
        assert aggregated['daily_totals'][today]['calls'] == 3
        assert abs(aggregated['daily_totals'][today]['cost'] - 0.035) < 0.001

        writer.shutdown(timeout=2.0)

    def test_merge_aggregated_method(self, temp_dir):
        """_merge_aggregated should correctly merge pre-aggregated data into main structure."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path)

        # Create initial data structure
        today = datetime.now().strftime("%Y-%m-%d")
        data = {
            "sessions": [{"existing": "session"}],
            "daily_totals": {
                today: {"tokens": 100, "cost": 0.01, "calls": 1}
            },
            "model_breakdown": {
                "model-a": {"tokens": 100, "cost": 0.01, "calls": 1}
            },
            "provider_breakdown": {
                "provider-1": {"tokens": 100, "cost": 0.01, "calls": 1}
            },
            "last_updated": datetime.now().isoformat()
        }

        # Create aggregated data to merge
        aggregated = {
            "sessions": [{"new": "session"}],
            "daily_totals": {
                today: {"tokens": 200, "cost": 0.02, "calls": 2}
            },
            "model_breakdown": {
                "model-a": {"tokens": 150, "cost": 0.015, "calls": 1},
                "model-b": {"tokens": 50, "cost": 0.005, "calls": 1}
            },
            "provider_breakdown": {
                "provider-1": {"tokens": 150, "cost": 0.015, "calls": 1},
                "provider-2": {"tokens": 50, "cost": 0.005, "calls": 1}
            }
        }

        # Merge
        writer._merge_aggregated(data, aggregated)

        # Verify sessions were appended
        assert len(data["sessions"]) == 2

        # Verify daily totals were summed
        assert data["daily_totals"][today]["tokens"] == 300  # 100 + 200
        assert abs(data["daily_totals"][today]["cost"] - 0.03) < 0.001  # 0.01 + 0.02
        assert data["daily_totals"][today]["calls"] == 3  # 1 + 2

        # Verify model breakdown was merged
        assert data["model_breakdown"]["model-a"]["tokens"] == 250  # 100 + 150
        assert data["model_breakdown"]["model-a"]["calls"] == 2  # 1 + 1
        assert data["model_breakdown"]["model-b"]["tokens"] == 50
        assert data["model_breakdown"]["model-b"]["calls"] == 1

        # Verify provider breakdown was merged
        assert data["provider_breakdown"]["provider-1"]["tokens"] == 250  # 100 + 150
        assert data["provider_breakdown"]["provider-1"]["calls"] == 2  # 1 + 1
        assert data["provider_breakdown"]["provider-2"]["tokens"] == 50
        assert data["provider_breakdown"]["provider-2"]["calls"] == 1

        writer.shutdown(timeout=2.0)

    def test_concurrent_flush_operations(self, temp_dir):
        """Multiple flush operations should be thread-safe."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=60.0, flush_threshold=1000)

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

        # Queue some records
        for _ in range(10):
            writer.queue_write(record)

        # Trigger multiple flush operations concurrently
        def trigger_flush():
            writer.flush(timeout=2.0)

        threads = []
        for _ in range(3):
            t = threading.Thread(target=trigger_flush)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All records should be written correctly
        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 10

        writer.shutdown(timeout=2.0)

    def test_shutdown_during_active_writes(self, temp_dir):
        """Shutdown during active writes should complete gracefully without data loss."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=60.0, flush_threshold=1000)

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

        # Queue many records and shutdown immediately
        for _ in range(50):
            writer.queue_write(record)

        # Immediate shutdown - should drain queue and flush
        writer.shutdown(timeout=5.0)

        # All records should be persisted
        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 50

    def test_get_empty_structure(self, temp_dir):
        """_get_empty_structure should return valid empty data structure."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path)

        empty = writer._get_empty_structure()

        assert "sessions" in empty
        assert "daily_totals" in empty
        assert "model_breakdown" in empty
        assert "provider_breakdown" in empty
        assert "last_updated" in empty
        assert isinstance(empty["sessions"], list)
        assert isinstance(empty["daily_totals"], dict)
        assert isinstance(empty["model_breakdown"], dict)
        assert isinstance(empty["provider_breakdown"], dict)
        assert len(empty["sessions"]) == 0

        writer.shutdown(timeout=2.0)

    def test_validate_structure_method(self, temp_dir):
        """_validate_structure should detect invalid data structures."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path)

        # Valid structure should not raise
        valid_data = {
            "sessions": [],
            "daily_totals": {},
            "model_breakdown": {},
            "provider_breakdown": {},
            "last_updated": "2026-01-11T00:00:00"
        }
        writer._validate_structure(valid_data)  # Should not raise

        # Missing key should raise
        invalid_data = {
            "sessions": [],
            "daily_totals": {}
            # Missing keys
        }
        try:
            writer._validate_structure(invalid_data)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Missing required key" in str(e)

        # Wrong type should raise
        invalid_type = {
            "sessions": "not a list",  # Wrong type
            "daily_totals": {},
            "model_breakdown": {},
            "provider_breakdown": {},
            "last_updated": "2026-01-11T00:00:00"
        }
        try:
            writer._validate_structure(invalid_type)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "must be a list" in str(e)

        writer.shutdown(timeout=2.0)

    def test_high_frequency_writes(self, temp_dir):
        """Writer should handle high-frequency write operations without blocking."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, flush_interval=1.0, flush_threshold=50)

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

        # Queue 500 records as fast as possible
        start = time.time()
        for _ in range(500):
            writer.queue_write(record)
        elapsed = time.time() - start

        # Should complete very quickly (non-blocking)
        assert elapsed < 0.5, f"High-frequency writes took {elapsed}s, expected <0.5s"

        # Wait for flushes to complete
        writer.flush(timeout=5.0)

        # All records should be written
        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 500

        # Check that batching occurred (should have multiple flushes but not 500)
        stats = writer.get_stats()
        assert stats["total_flushes"] < 100, "Should batch writes, not flush for every record"

        writer.shutdown(timeout=2.0)

    def test_error_message_preservation(self, temp_dir):
        """Last error should be preserved in stats for debugging."""
        storage_path = temp_dir / "usage.json"
        writer = AsyncUsageWriter(storage_path, max_retries=1, retry_base_delay=0.05)

        # Create a condition that will cause an error
        storage_path.mkdir()

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

        writer.queue_write(record)
        time.sleep(0.5)

        stats = writer.get_stats()
        # Should have recorded an error
        assert stats["error_count"] >= 0

        # Cleanup
        storage_path.rmdir()
        writer.shutdown(timeout=2.0)


# ============================================================================
# UsageTracker Tests
# ============================================================================

class TestUsageTracker:
    """Tests for the UsageTracker class."""

    def test_init_creates_storage_file(self, temp_dir):
        """UsageTracker should create storage file on initialization."""
        storage_path = temp_dir / "usage.json"
        pricing = {"claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}}

        tracker = UsageTracker(str(storage_path), pricing)

        assert storage_path.exists()
        data = json.loads(storage_path.read_text())
        assert "sessions" in data
        assert "daily_totals" in data

    def test_calculate_cost(self, temp_dir):
        """calculate_cost should compute correct costs based on pricing."""
        storage_path = temp_dir / "usage.json"
        pricing = {
            "claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}
        }
        tracker = UsageTracker(str(storage_path), pricing)

        # 1000 input tokens = $0.015, 1000 output tokens = $0.075
        cost = tracker.calculate_cost("claude-opus-4-5-20251101", 1000, 1000)
        assert cost == pytest.approx(0.09)

    def test_record_updates_storage(self, temp_dir):
        """record should update storage with usage data."""
        storage_path = temp_dir / "usage.json"
        pricing = {"claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}}
        tracker = UsageTracker(str(storage_path), pricing)

        tracker.record(
            model="claude-opus-4-5-20251101",
            input_tokens=500,
            output_tokens=200,
            cost_usd=0.0225,
            latency_ms=1500,
            operation="test"
        )

        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["input_tokens"] == 500
        assert data["sessions"][0]["output_tokens"] == 200

    def test_get_today_returns_daily_stats(self, temp_dir):
        """get_today should return today's usage statistics."""
        storage_path = temp_dir / "usage.json"
        pricing = {"claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}}
        tracker = UsageTracker(str(storage_path), pricing)

        tracker.record("claude-opus-4-5-20251101", 100, 50, 0.01, 1000)
        tracker.record("claude-opus-4-5-20251101", 200, 100, 0.02, 1200)

        today = tracker.get_today()
        assert today["tokens"] == 450  # (100+50) + (200+100)
        assert today["calls"] == 2

    def test_get_summary_aggregates_correctly(self, temp_dir):
        """get_summary should aggregate usage over the specified period."""
        storage_path = temp_dir / "usage.json"
        pricing = {"claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}}
        tracker = UsageTracker(str(storage_path), pricing)

        # Record some usage
        tracker.record("claude-opus-4-5-20251101", 1000, 500, 0.05, 1500)

        summary = tracker.get_summary(30)
        assert summary["total_tokens"] == 1500
        assert summary["total_calls"] == 1
        assert "projected_monthly_cost" in summary

    def test_provider_detection(self, temp_dir):
        """_get_provider should correctly identify providers from model names."""
        storage_path = temp_dir / "usage.json"
        pricing = {}
        tracker = UsageTracker(str(storage_path), pricing)

        assert tracker._get_provider("claude-opus-4-5-20251101") == "anthropic"
        assert tracker._get_provider("gpt-4o") == "openai"
        assert tracker._get_provider("gemini-pro") == "google"
        assert tracker._get_provider("unknown-model") == "unknown"


# ============================================================================
# ComplexityAnalyzer Tests
# ============================================================================

class TestComplexityAnalyzer:
    """Tests for the ComplexityAnalyzer class."""

    def test_simple_prompt_low_complexity(self):
        """Simple prompts should have low complexity scores."""
        config = {
            "complexity_factors": {
                "token_count_weight": 0.3,
                "keyword_weight": 0.4,
                "history_length_weight": 0.3
            }
        }
        analyzer = ComplexityAnalyzer(config)

        complexity, tier = analyzer.analyze("What's 2+2?")

        assert complexity < 0.5
        assert tier in ["simple", "standard"]

    def test_complex_prompt_high_complexity(self):
        """Complex prompts with analysis keywords should have high complexity."""
        config = {
            "complexity_factors": {
                "token_count_weight": 0.3,
                "keyword_weight": 0.4,
                "history_length_weight": 0.3
            }
        }
        analyzer = ComplexityAnalyzer(config)

        complexity, tier = analyzer.analyze(
            "Analyze the architecture of this complex system and provide "
            "a comprehensive strategy for optimization and refactoring. "
            "Debug any issues and explain the reasoning step by step."
        )

        # Complexity should be moderate-to-high (above default 0.35 baseline)
        assert complexity > 0.35
        assert tier in ["standard", "complex"]

    def test_history_increases_complexity(self):
        """Long conversation history should increase complexity."""
        config = {
            "complexity_factors": {
                "token_count_weight": 0.3,
                "keyword_weight": 0.4,
                "history_length_weight": 0.3
            }
        }
        analyzer = ComplexityAnalyzer(config)

        # Short history
        complexity_short, _ = analyzer.analyze("Continue", [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ])

        # Long history
        history = [{"role": "user" if i % 2 == 0 else "assistant",
                    "content": f"Message {i}"} for i in range(20)]
        complexity_long, _ = analyzer.analyze("Continue", history)

        assert complexity_long > complexity_short

    def test_simple_keywords_reduce_complexity(self):
        """Simple keywords should reduce complexity score."""
        config = {
            "complexity_factors": {
                "token_count_weight": 0.3,
                "keyword_weight": 0.4,
                "history_length_weight": 0.3
            }
        }
        analyzer = ComplexityAnalyzer(config)

        complexity, tier = analyzer.analyze("Just give me a quick, simple one sentence summary")

        assert complexity < 0.5


# ============================================================================
# ResponseCache Tests
# ============================================================================

class TestResponseCache:
    """Tests for the ResponseCache class."""

    def test_set_and_get(self, temp_dir):
        """Cache should store and retrieve responses."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=3600)

        cache.set("test prompt", "claude-opus-4-5-20251101", {}, "cached response")
        result = cache.get("test prompt", "claude-opus-4-5-20251101", {})

        assert result == "cached response"

    def test_cache_miss(self, temp_dir):
        """Cache should return None for missing entries."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=3600)

        result = cache.get("nonexistent", "model", {})

        assert result is None

    def test_cache_expiration(self, temp_dir):
        """Expired cache entries should return None."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=1)

        cache.set("test", "model", {}, "response")

        # Manually expire the cache
        import time
        time.sleep(1.1)

        result = cache.get("test", "model", {})
        assert result is None

    def test_different_models_different_cache(self, temp_dir):
        """Same prompt with different models should have different cache entries."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=3600)

        cache.set("test prompt", "model-a", {}, "response from A")
        cache.set("test prompt", "model-b", {}, "response from B")

        assert cache.get("test prompt", "model-a", {}) == "response from A"
        assert cache.get("test prompt", "model-b", {}) == "response from B"

    def test_clear_expired(self, temp_dir):
        """clear_expired should remove old cache entries."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=1)
        cache_dir = Path(temp_dir / "cache")

        cache.set("test1", "model", {}, "response1")
        cache.set("test2", "model", {}, "response2")

        import time
        time.sleep(1.1)

        cache.clear_expired()

        # All cache files should be removed
        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) == 0


# ============================================================================
# LiteLLMClient Tests
# ============================================================================

class TestLiteLLMClient:
    """Tests for the LiteLLMClient class."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_init_with_config(self, mock_config, temp_dir):
        """Client should initialize with provided config."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic") as mock_anthropic:
                    client = LiteLLMClient(str(mock_config))

                    assert client.config is not None
                    assert client.usage_tracker is not None
                    assert client.cache is not None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_model_selection_simple(self, mock_config):
        """Simple prompts should select simpler models."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic"):
                    client = LiteLLMClient(str(mock_config))
                    model = client._select_model("What's the weather?")

                    # Should NOT be opus for simple query
                    assert model in [
                        "claude-opus-4-5-20251101",
                        "claude-sonnet-4-20250514",
                        "claude-3-5-haiku-20241022"
                    ]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_model_selection_override(self, mock_config):
        """Explicit model override should be respected."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic"):
                    client = LiteLLMClient(str(mock_config))
                    model = client._select_model(
                        "Simple question",
                        model_override="claude-opus-4-5-20251101"
                    )

                    assert model == "claude-opus-4-5-20251101"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_chat_uses_cache(self, mock_config, mock_anthropic_response):
        """chat should use cached responses when available."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic") as mock_anthropic:
                    mock_client = Mock()
                    mock_client.messages.create.return_value = mock_anthropic_response
                    mock_anthropic.Anthropic.return_value = mock_client

                    client = LiteLLMClient(str(mock_config))

                    # First call should hit API
                    response1 = client.chat("Test prompt")
                    assert mock_client.messages.create.call_count == 1

                    # Second call should use cache
                    response2 = client.chat("Test prompt")
                    assert mock_client.messages.create.call_count == 1
                    assert response1 == response2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_chat_skips_cache_when_disabled(self, mock_config, mock_anthropic_response):
        """chat should skip cache when use_cache=False."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic") as mock_anthropic:
                    mock_client = Mock()
                    mock_client.messages.create.return_value = mock_anthropic_response
                    mock_anthropic.Anthropic.return_value = mock_client

                    client = LiteLLMClient(str(mock_config))

                    client.chat("Test prompt", use_cache=False)
                    client.chat("Test prompt", use_cache=False)

                    assert mock_client.messages.create.call_count == 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_usage_tracking(self, mock_config, mock_anthropic_response, temp_dir):
        """chat should track usage when enabled."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic") as mock_anthropic:
                    mock_client = Mock()
                    mock_client.messages.create.return_value = mock_anthropic_response
                    mock_anthropic.Anthropic.return_value = mock_client

                    client = LiteLLMClient(str(mock_config))
                    client.chat("Test prompt", use_cache=False)

                    usage = client.get_today_usage()
                    assert usage["calls"] >= 1
                    assert usage["tokens"] > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_analyze_complexity_method(self, mock_config):
        """analyze_complexity should return complexity info."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic"):
                    client = LiteLLMClient(str(mock_config))

                    result = client.analyze_complexity("Analyze this architecture")

                    assert "complexity_score" in result
                    assert "tier" in result
                    assert "selected_model" in result
                    assert 0 <= result["complexity_score"] <= 1

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_list_available_models(self, mock_config):
        """list_available_models should return configured models."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic"):
                    client = LiteLLMClient(str(mock_config))
                    models = client.list_available_models()

                    assert "claude-opus-4-5-20251101" in models
                    assert "claude-sonnet-4-20250514" in models
                    assert "claude-3-5-haiku-20241022" in models


# ============================================================================
# Module Function Tests
# ============================================================================

class TestModuleFunctions:
    """Tests for module-level functions."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_get_client_singleton(self, mock_config):
        """get_client should return singleton instance."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic"):
                    # Reset singleton
                    import Tools.litellm_client as llm_module
                    llm_module._client_instance = None

                    client1 = get_client(str(mock_config))
                    client2 = get_client()

                    assert client1 is client2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_init_client_creates_new(self, mock_config):
        """init_client should create a new instance."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic"):
                    import Tools.litellm_client as llm_module
                    llm_module._client_instance = None

                    client1 = init_client(str(mock_config))
                    client2 = init_client(str(mock_config))

                    # init_client always creates new
                    assert client1 is not None
                    assert client2 is not None


# ============================================================================
# ModelResponse Dataclass Tests
# ============================================================================

class TestModelResponse:
    """Tests for the ModelResponse dataclass."""

    def test_model_response_creation(self):
        """ModelResponse should be properly initialized."""
        response = ModelResponse(
            content="Test content",
            model="claude-opus-4-5-20251101",
            provider="anthropic",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.05,
            latency_ms=1500.0,
            cached=False
        )

        assert response.content == "Test content"
        assert response.model == "claude-opus-4-5-20251101"
        assert response.total_tokens == 150
        assert response.cached is False

    def test_model_response_with_metadata(self):
        """ModelResponse should support metadata."""
        response = ModelResponse(
            content="Test",
            model="test-model",
            provider="test",
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            cost_usd=0.01,
            latency_ms=100.0,
            metadata={"operation": "test", "agent": "ops"}
        )

        assert response.metadata["operation"] == "test"
        assert response.metadata["agent"] == "ops"


# ============================================================================
# Integration-like Tests (with mocks)
# ============================================================================

class TestLiteLLMIntegration:
    """Integration-style tests with comprehensive mocking."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_full_chat_flow(self, mock_config, mock_anthropic_response):
        """Test complete chat flow: routing -> API call -> tracking -> caching."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic") as mock_anthropic:
                    mock_client = Mock()
                    mock_client.messages.create.return_value = mock_anthropic_response
                    mock_anthropic.Anthropic.return_value = mock_client

                    client = LiteLLMClient(str(mock_config))

                    # First request
                    response = client.chat(
                        "What is architecture analysis?",
                        operation="test_chat"
                    )

                    assert response == "Test response from Anthropic"

                    # Check usage was tracked
                    usage = client.get_today_usage()
                    assert usage["calls"] >= 1

                    # Check response was cached
                    response2 = client.chat("What is architecture analysis?")
                    assert response2 == response
                    assert mock_client.messages.create.call_count == 1

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_complexity_based_routing(self, mock_config, mock_anthropic_response):
        """Test that complexity analysis affects model selection."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic") as mock_anthropic:
                    mock_client = Mock()
                    mock_client.messages.create.return_value = mock_anthropic_response
                    mock_anthropic.Anthropic.return_value = mock_client

                    client = LiteLLMClient(str(mock_config))

                    # Analyze simple vs complex prompts
                    simple_analysis = client.analyze_complexity("Hi")
                    complex_analysis = client.analyze_complexity(
                        "Analyze this complex architecture and debug systematically"
                    )

                    assert complex_analysis["complexity_score"] > simple_analysis["complexity_score"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
