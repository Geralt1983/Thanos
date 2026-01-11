#!/usr/bin/env python3
"""
Test script to verify the aggregation optimization in AsyncUsageWriter.

This test verifies that:
1. Multiple records are correctly aggregated
2. Data integrity is preserved
3. The optimization reduces I/O operations
"""

import os
import sys
import json
import time
import tempfile
from pathlib import Path
from datetime import datetime

# Add Tools to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from Tools.litellm_client import AsyncUsageWriter


def test_aggregation_optimization():
    """Test that aggregation optimization works correctly."""
    print("=" * 80)
    print("Testing Aggregation Optimization")
    print("=" * 80)

    # Create temporary storage file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        storage_path = Path(f.name)
        # Initialize with empty structure
        json.dump({
            "sessions": [],
            "daily_totals": {},
            "model_breakdown": {},
            "provider_breakdown": {},
            "last_updated": datetime.now().isoformat()
        }, f)

    try:
        # Create AsyncUsageWriter with small threshold for testing
        writer = AsyncUsageWriter(
            storage_path=storage_path,
            flush_interval=1.0,
            flush_threshold=5  # Small threshold to test batching
        )

        print(f"✓ AsyncUsageWriter initialized")
        print(f"  Storage: {storage_path}")
        print()

        # Test Case 1: Multiple records with same model/provider
        print("Test 1: Aggregating 10 records with same model/provider")
        print("-" * 80)

        records = []
        for i in range(10):
            record = {
                "timestamp": datetime.now().isoformat(),
                "model": "gpt-4",
                "provider": "openai",
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
                "cost_usd": 0.01,
                "session_id": f"test-session-{i}"
            }
            writer.queue_write(record)
            records.append(record)

        print(f"✓ Queued 10 records")

        # Wait for auto-flush (threshold=5, so should flush at 5 and then at 10)
        time.sleep(2.0)

        # Force flush to ensure all records are written
        flush_success = writer.flush(timeout=5.0)
        print(f"✓ Flush completed: {flush_success}")

        # Read and verify the data
        data = json.loads(storage_path.read_text())

        # Verify sessions
        assert len(data["sessions"]) == 10, f"Expected 10 sessions, got {len(data['sessions'])}"
        print(f"✓ Sessions: {len(data['sessions'])} records")

        # Verify daily totals (all records are from today)
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in data["daily_totals"], f"Missing today's data: {today}"
        daily = data["daily_totals"][today]
        assert daily["calls"] == 10, f"Expected 10 calls, got {daily['calls']}"
        assert daily["tokens"] == 3000, f"Expected 3000 tokens, got {daily['tokens']}"
        assert abs(daily["cost"] - 0.10) < 0.001, f"Expected $0.10, got ${daily['cost']}"
        print(f"✓ Daily totals: {daily['calls']} calls, {daily['tokens']} tokens, ${daily['cost']:.2f}")

        # Verify model breakdown
        assert "gpt-4" in data["model_breakdown"], "Missing gpt-4 in model breakdown"
        model = data["model_breakdown"]["gpt-4"]
        assert model["calls"] == 10, f"Expected 10 calls for gpt-4, got {model['calls']}"
        assert model["tokens"] == 3000, f"Expected 3000 tokens for gpt-4, got {model['tokens']}"
        assert abs(model["cost"] - 0.10) < 0.001, f"Expected $0.10 for gpt-4, got ${model['cost']}"
        print(f"✓ Model breakdown (gpt-4): {model['calls']} calls, {model['tokens']} tokens, ${model['cost']:.2f}")

        # Verify provider breakdown
        assert "openai" in data["provider_breakdown"], "Missing openai in provider breakdown"
        provider = data["provider_breakdown"]["openai"]
        assert provider["calls"] == 10, f"Expected 10 calls for openai, got {provider['calls']}"
        assert provider["tokens"] == 3000, f"Expected 3000 tokens for openai, got {provider['tokens']}"
        assert abs(provider["cost"] - 0.10) < 0.001, f"Expected $0.10 for openai, got ${provider['cost']}"
        print(f"✓ Provider breakdown (openai): {provider['calls']} calls, {provider['tokens']} tokens, ${provider['cost']:.2f}")

        print()

        # Test Case 2: Multiple models and providers
        print("Test 2: Aggregating records with different models and providers")
        print("-" * 80)

        # Add 5 more gpt-4 records and 5 claude records
        for i in range(5):
            writer.queue_write({
                "timestamp": datetime.now().isoformat(),
                "model": "gpt-4",
                "provider": "openai",
                "prompt_tokens": 50,
                "completion_tokens": 100,
                "total_tokens": 150,
                "cost_usd": 0.005,
                "session_id": f"test-session-gpt4-{i}"
            })

        for i in range(5):
            writer.queue_write({
                "timestamp": datetime.now().isoformat(),
                "model": "claude-3-sonnet",
                "provider": "anthropic",
                "prompt_tokens": 80,
                "completion_tokens": 120,
                "total_tokens": 200,
                "cost_usd": 0.008,
                "session_id": f"test-session-claude-{i}"
            })

        print(f"✓ Queued 5 gpt-4 + 5 claude-3-sonnet records")

        # Flush and verify
        time.sleep(2.0)
        writer.flush(timeout=5.0)

        data = json.loads(storage_path.read_text())

        # Should now have 20 total sessions
        assert len(data["sessions"]) == 20, f"Expected 20 sessions, got {len(data['sessions'])}"
        print(f"✓ Total sessions: {len(data['sessions'])} records")

        # Verify gpt-4 now has 15 calls total
        assert data["model_breakdown"]["gpt-4"]["calls"] == 15, \
            f"Expected 15 calls for gpt-4, got {data['model_breakdown']['gpt-4']['calls']}"
        print(f"✓ gpt-4: {data['model_breakdown']['gpt-4']['calls']} calls")

        # Verify claude has 5 calls
        assert "claude-3-sonnet" in data["model_breakdown"], "Missing claude-3-sonnet in model breakdown"
        assert data["model_breakdown"]["claude-3-sonnet"]["calls"] == 5, \
            f"Expected 5 calls for claude-3-sonnet, got {data['model_breakdown']['claude-3-sonnet']['calls']}"
        print(f"✓ claude-3-sonnet: {data['model_breakdown']['claude-3-sonnet']['calls']} calls")

        # Verify provider breakdown
        assert data["provider_breakdown"]["openai"]["calls"] == 15, \
            f"Expected 15 calls for openai, got {data['provider_breakdown']['openai']['calls']}"
        assert "anthropic" in data["provider_breakdown"], "Missing anthropic in provider breakdown"
        assert data["provider_breakdown"]["anthropic"]["calls"] == 5, \
            f"Expected 5 calls for anthropic, got {data['provider_breakdown']['anthropic']['calls']}"
        print(f"✓ openai: {data['provider_breakdown']['openai']['calls']} calls")
        print(f"✓ anthropic: {data['provider_breakdown']['anthropic']['calls']} calls")

        print()

        # Get statistics
        stats = writer.get_stats()
        print("Writer Statistics:")
        print(f"  Total flushes: {stats['total_flushes']}")
        print(f"  Total records: {stats['total_records']}")
        print(f"  Buffer size: {stats['buffer_size']}")
        print(f"  Queue size: {stats['queue_size']}")
        print()

        # Verify I/O efficiency: Should have much fewer flushes than records
        # With 20 records and threshold=5, we expect around 4 flushes
        assert stats['total_flushes'] <= 6, \
            f"Expected <= 6 flushes for 20 records (threshold=5), got {stats['total_flushes']}"
        print(f"✓ I/O efficiency: {stats['total_records']} records in {stats['total_flushes']} flushes")
        print(f"  Batching ratio: {stats['total_records'] / max(stats['total_flushes'], 1):.1f} records/flush")

        print()

        # Shutdown gracefully
        writer.shutdown(timeout=5.0)
        print("✓ Writer shutdown successfully")

        print()
        print("=" * 80)
        print("✅ All aggregation optimization tests passed!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        try:
            if storage_path.exists():
                storage_path.unlink()
            # Clean up backup files
            for suffix in ['.backup.json', '.backup.old.json', '.tmp']:
                backup = storage_path.with_suffix(suffix)
                if backup.exists():
                    backup.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    success = test_aggregation_optimization()
    sys.exit(0 if success else 1)
