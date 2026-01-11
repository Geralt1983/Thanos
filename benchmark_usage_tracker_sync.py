#!/usr/bin/env python3
"""
Performance benchmark for UsageTracker synchronous I/O operations.

This script measures the actual performance impact of the current synchronous
file I/O in UsageTracker.record() to establish baseline metrics before implementing
async write-behind buffer.
"""

import sys
import json
import time
import tempfile
import statistics
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from Tools.litellm_client import UsageTracker


def create_test_tracker(num_existing_records=0):
    """Create a temporary UsageTracker with existing data."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / "test_usage.json"

    # Create tracker
    pricing = {
        "claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075},
        "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
        "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005}
    }
    tracker = UsageTracker(str(temp_path), pricing)

    # Pre-populate with existing records
    if num_existing_records > 0:
        print(f"Pre-populating with {num_existing_records} records...")
        for i in range(num_existing_records):
            tracker.record(
                model="claude-sonnet-4-20250514",
                input_tokens=100 + i,
                output_tokens=50 + i,
                cost_usd=0.01,
                latency_ms=100.0,
                operation="test",
                metadata={"test_record": i}
            )

    return tracker, temp_path


def measure_single_record(tracker, trial_num):
    """Measure time for a single record() call."""
    start = time.perf_counter()

    tracker.record(
        model="claude-opus-4-5-20251101",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=0.05,
        latency_ms=250.0,
        operation="benchmark",
        metadata={"trial": trial_num}
    )

    end = time.perf_counter()
    return (end - start) * 1000  # Convert to milliseconds


def benchmark_record_performance(num_trials=100, existing_records=0):
    """Benchmark UsageTracker.record() performance."""
    print(f"\n{'='*70}")
    print(f"Benchmark: record() with {existing_records} existing records")
    print(f"{'='*70}")

    tracker, temp_path = create_test_tracker(existing_records)

    # Warm-up
    for _ in range(5):
        measure_single_record(tracker, -1)

    # Actual measurements
    timings = []
    print(f"Running {num_trials} trials...")
    for i in range(num_trials):
        elapsed_ms = measure_single_record(tracker, i)
        timings.append(elapsed_ms)

        if (i + 1) % 20 == 0:
            print(f"  Completed {i + 1}/{num_trials} trials")

    # Statistics
    mean = statistics.mean(timings)
    median = statistics.median(timings)
    stdev = statistics.stdev(timings) if len(timings) > 1 else 0
    min_time = min(timings)
    max_time = max(timings)
    p95 = sorted(timings)[int(len(timings) * 0.95)]
    p99 = sorted(timings)[int(len(timings) * 0.99)]

    # File size
    file_size = Path(temp_path).stat().st_size

    print(f"\nResults:")
    print(f"  Mean:       {mean:.2f} ms")
    print(f"  Median:     {median:.2f} ms")
    print(f"  Std Dev:    {stdev:.2f} ms")
    print(f"  Min:        {min_time:.2f} ms")
    print(f"  Max:        {max_time:.2f} ms")
    print(f"  P95:        {p95:.2f} ms")
    print(f"  P99:        {p99:.2f} ms")
    print(f"  File Size:  {file_size:,} bytes ({file_size / 1024:.1f} KB)")

    # Cleanup
    Path(temp_path).unlink()

    return {
        "existing_records": existing_records,
        "num_trials": num_trials,
        "mean_ms": mean,
        "median_ms": median,
        "stdev_ms": stdev,
        "min_ms": min_time,
        "max_ms": max_time,
        "p95_ms": p95,
        "p99_ms": p99,
        "file_size_bytes": file_size
    }


def simulate_streaming_scenario():
    """Simulate streaming response with multiple record() calls."""
    print(f"\n{'='*70}")
    print(f"Simulation: Streaming Response (10 incremental updates)")
    print(f"{'='*70}")

    tracker, temp_path = create_test_tracker(num_existing_records=100)

    # Simulate 10 streaming chunks, each triggering a record()
    chunk_timings = []
    total_start = time.perf_counter()

    for chunk_num in range(10):
        chunk_start = time.perf_counter()

        # Simulate receiving a chunk
        time.sleep(0.001)  # Simulate 1ms processing

        # Record usage (this blocks!)
        record_start = time.perf_counter()
        tracker.record(
            model="claude-opus-4-5-20251101",
            input_tokens=1000,
            output_tokens=50 * (chunk_num + 1),
            cost_usd=0.001 * (chunk_num + 1),
            latency_ms=10.0,
            operation="streaming_chunk",
            metadata={"chunk": chunk_num}
        )
        record_time = (time.perf_counter() - record_start) * 1000

        chunk_end = time.perf_counter()
        chunk_total = (chunk_end - chunk_start) * 1000

        chunk_timings.append({
            "chunk": chunk_num,
            "record_time_ms": record_time,
            "total_time_ms": chunk_total
        })

    total_end = time.perf_counter()
    total_time = (total_end - total_start) * 1000

    print(f"\nChunk-by-chunk breakdown:")
    print(f"  {'Chunk':<8} {'Record (ms)':<15} {'Total (ms)':<15} {'Blocked %'}")
    for ct in chunk_timings:
        blocked_pct = (ct['record_time_ms'] / ct['total_time_ms']) * 100
        print(f"  {ct['chunk']:<8} {ct['record_time_ms']:<15.2f} {ct['total_time_ms']:<15.2f} {blocked_pct:.1f}%")

    avg_record = statistics.mean([ct['record_time_ms'] for ct in chunk_timings])
    avg_total = statistics.mean([ct['total_time_ms'] for ct in chunk_timings])
    avg_blocked_pct = (avg_record / avg_total) * 100

    print(f"\nSummary:")
    print(f"  Total streaming time:     {total_time:.2f} ms")
    print(f"  Avg record() time:        {avg_record:.2f} ms")
    print(f"  Avg total chunk time:     {avg_total:.2f} ms")
    print(f"  Avg % time blocked:       {avg_blocked_pct:.1f}%")
    print(f"  Total time in record():   {sum([ct['record_time_ms'] for ct in chunk_timings]):.2f} ms")

    # Cleanup
    Path(temp_path).unlink()


def main():
    """Run all benchmarks."""
    print(f"\n{'='*70}")
    print(f"UsageTracker Synchronous I/O Performance Benchmark")
    print(f"{'='*70}")
    print(f"Purpose: Measure blocking impact of current synchronous file I/O")
    print(f"Platform: {sys.platform}")

    results = []

    # Test with different file sizes
    test_scenarios = [
        (0, "Empty file (initial state)"),
        (10, "Small file (10 records)"),
        (100, "Medium file (100 records)"),
        (500, "Large file (500 records)"),
        (1000, "Max file (1000 records)"),
    ]

    for num_records, description in test_scenarios:
        print(f"\n{description}")
        result = benchmark_record_performance(
            num_trials=50,
            existing_records=num_records
        )
        results.append(result)

    # Streaming simulation
    simulate_streaming_scenario()

    # Summary
    print(f"\n{'='*70}")
    print(f"Overall Summary")
    print(f"{'='*70}")
    print(f"\n{'Records':<12} {'Mean (ms)':<12} {'P95 (ms)':<12} {'File Size'}")
    for r in results:
        print(f"{r['existing_records']:<12} {r['mean_ms']:<12.2f} {r['p95_ms']:<12.2f} {r['file_size_bytes'] / 1024:.1f} KB")

    # Analysis
    print(f"\nKey Findings:")
    mean_times = [r['mean_ms'] for r in results]
    print(f"  - Blocking time range: {min(mean_times):.2f} - {max(mean_times):.2f} ms")
    print(f"  - Performance degrades with file size: {max(mean_times) / min(mean_times):.1f}x slower at max size")
    print(f"  - Every API call blocks for synchronous read + write")
    print(f"  - During streaming, {len([t for t in mean_times if t > 5])} out of {len(mean_times)} scenarios exceed 5ms blocking")
    print(f"\nConclusion:")
    print(f"  Current implementation causes {min(mean_times):.1f}-{max(mean_times):.1f}ms main thread blocking")
    print(f"  per API call, directly impacting streaming response fluidity.")
    print(f"  Async write-behind buffer could reduce this to <1ms (queue operation only).")


if __name__ == "__main__":
    main()
