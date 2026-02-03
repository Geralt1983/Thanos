#!/usr/bin/env python3
"""
Debug test for UsageTracker async functionality.
"""
import json
import time
import tempfile
from pathlib import Path
from Tools.litellm_client import UsageTracker

# Create a fixed temp directory for inspection
tmpdir = "/tmp/test_usage_tracker"
Path(tmpdir).mkdir(exist_ok=True)
storage_path = Path(tmpdir) / "test_usage.json"

# Remove old file if exists
if storage_path.exists():
    storage_path.unlink()

# Initialize tracker
pricing = {"claude": {"input": 0.015, "output": 0.075}}
tracker = UsageTracker(str(storage_path), pricing)

print("✓ UsageTracker initialized")
print(f"Storage path: {storage_path}")

# Record a few entries
for i in range(3):
    tracker.record(
        model="anthropic/claude-sonnet-4-5",
        input_tokens=100,
        output_tokens=200,
        cost_usd=0.01,
        latency_ms=50.0,
        operation="test",
        metadata={"test_id": i}
    )
    print(f"  Recorded entry {i}")

# Check stats before flush
stats = tracker.get_writer_stats()
print(f"\nStats before flush:")
print(f"  Queue size: {stats['queue_size']}")
print(f"  Buffer size: {stats['buffer_size']}")
print(f"  Total records: {stats['total_records']}")
print(f"  Total flushes: {stats['total_flushes']}")

# Wait a moment for background thread to process
time.sleep(0.5)

# Check stats after wait
stats = tracker.get_writer_stats()
print(f"\nStats after 0.5s wait:")
print(f"  Queue size: {stats['queue_size']}")
print(f"  Buffer size: {stats['buffer_size']}")
print(f"  Total records: {stats['total_records']}")
print(f"  Total flushes: {stats['total_flushes']}")

# List files in directory
print(f"\nFiles in {tmpdir}:")
for f in Path(tmpdir).glob("*"):
    print(f"  {f.name} ({f.stat().st_size} bytes)")

# Force flush
print("\nForcing flush...")
success = tracker.flush(timeout=5.0)
print(f"  Flush result: {success}")

# Wait a bit more
time.sleep(0.5)

# Check stats after flush
stats = tracker.get_writer_stats()
print(f"\nStats after flush:")
print(f"  Queue size: {stats['queue_size']}")
print(f"  Buffer size: {stats['buffer_size']}")
print(f"  Total records: {stats['total_records']}")
print(f"  Total flushes: {stats['total_flushes']}")

# List files again
print(f"\nFiles in {tmpdir} after flush:")
for f in Path(tmpdir).glob("*"):
    print(f"  {f.name} ({f.stat().st_size} bytes)")

# Read the file
if storage_path.exists():
    print(f"\nReading {storage_path}:")
    data = json.loads(storage_path.read_text())
    print(f"  Sessions: {len(data.get('sessions', []))}")
    print(f"  Daily totals: {data.get('daily_totals', {})}")
    print(f"  Model breakdown: {data.get('model_breakdown', {})}")
else:
    print(f"\n✗ {storage_path} does not exist!")

# Cleanup
print("\nShutting down...")
tracker._shutdown()
print("✓ Shutdown complete")
