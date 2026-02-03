#!/usr/bin/env python3
"""
Performance Benchmark for UsageTracker synchronous I/O operations.

This script measures the actual performance impact of the synchronous file I/O
in the UsageTracker.record() method to quantify the blocking time.

Usage:
    python benchmark_usage_tracker.py
"""

import time
import json
import tempfile
import statistics
from pathlib import Path
from typing import List, Dict

# Import UsageTracker
import sys
sys.path.insert(0, str(Path(__file__).parent))
from Tools.litellm_client import UsageTracker


def create_test_tracker(file_size: str = "small") -> UsageTracker:
    """Create a test UsageTracker with controlled file size."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_path = temp_file.name

    # Create initial data with varying sizes
    initial_data = {
        "sessions": [],
        "daily_totals": {},
        "model_breakdown": {},
        "provider_breakdown": {},
        "last_updated": "2026-01-01T00:00:00"
    }

    if file_size == "small":
        # ~1KB file
        pass
    elif file_size == "medium":
        # ~50KB file - add 100 session entries
        for i in range(100):
            initial_data["sessions"].append({
                "timestamp": f"2026-01-{(i % 30) + 1:02d}T12:00:00",
                "model": "anthropic/claude-opus-4-5",
                "provider": "anthropic",
                "input_tokens": 1000,
                "output_tokens": 500,
                "total_tokens": 1500,
                "cost_usd": 0.05,
                "latency_ms": 1500.0,
                "operation": "chat",
                "metadata": {}
            })
    elif file_size == "large":
        # ~500KB file - add 1000 session entries
        for i in range(1000):
            initial_data["sessions"].append({
                "timestamp": f"2026-01-{(i % 30) + 1:02d}T12:00:00",
                "model": "anthropic/claude-opus-4-5",
                "provider": "anthropic",
                "input_tokens": 1000,
                "output_tokens": 500,
                "total_tokens": 1500,
                "cost_usd": 0.05,
                "latency_ms": 1500.0,
                "operation": "chat",
                "metadata": {}
            })

    # Write initial data
    with open(temp_path, 'w') as f:
        json.dump(initial_data, f, indent=2)

    # Create tracker
    pricing = {
        "anthropic/claude-opus-4-5": {"input": 0.015, "output": 0.075},
        "anthropic/claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
        "anthropic/claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005}
    }

    tracker = UsageTracker(temp_path, pricing)
    return tracker


def measure_single_record(tracker: UsageTracker) -> float:
    """Measure the time taken for a single record() call in milliseconds."""
    start = time.perf_counter()

    tracker.record(
        model="anthropic/claude-opus-4-5",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=0.05,
        latency_ms=1500.0,
        operation="benchmark"
    )

    end = time.perf_counter()
    return (end - start) * 1000  # Convert to milliseconds


def benchmark_record_performance(file_size: str, num_iterations: int = 50) -> Dict:
    """Run benchmark for record() method with specified file size."""
    print(f"\n{'=' * 60}")
    print(f"Benchmarking UsageTracker.record() - File Size: {file_size.upper()}")
    print(f"{'=' * 60}")

    tracker = create_test_tracker(file_size)

    # Warm up
    for _ in range(5):
        measure_single_record(tracker)

    # Measure
    times: List[float] = []
    for i in range(num_iterations):
        elapsed_ms = measure_single_record(tracker)
        times.append(elapsed_ms)

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{num_iterations} calls completed...")

    # Calculate statistics
    results = {
        "file_size": file_size,
        "iterations": num_iterations,
        "min_ms": min(times),
        "max_ms": max(times),
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
        "p95_ms": sorted(times)[int(len(times) * 0.95)],
        "p99_ms": sorted(times)[int(len(times) * 0.99)]
    }

    # Clean up
    Path(tracker.storage_path).unlink()

    return results


def print_results(results: Dict):
    """Print benchmark results in a formatted table."""
    print(f"\nResults for {results['file_size'].upper()} file size:")
    print(f"  Iterations:    {results['iterations']}")
    print(f"  Min:           {results['min_ms']:.2f} ms")
    print(f"  Max:           {results['max_ms']:.2f} ms")
    print(f"  Mean:          {results['mean_ms']:.2f} ms")
    print(f"  Median:        {results['median_ms']:.2f} ms")
    print(f"  Std Dev:       {results['stdev_ms']:.2f} ms")
    print(f"  95th %ile:     {results['p95_ms']:.2f} ms")
    print(f"  99th %ile:     {results['p99_ms']:.2f} ms")


def benchmark_concurrent_impact(num_concurrent: int = 10):
    """Measure the impact of multiple concurrent record() calls."""
    print(f"\n{'=' * 60}")
    print(f"Benchmarking Concurrent Impact - {num_concurrent} rapid calls")
    print(f"{'=' * 60}")

    tracker = create_test_tracker("medium")

    start = time.perf_counter()

    for i in range(num_concurrent):
        tracker.record(
            model="anthropic/claude-opus-4-5",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.05,
            latency_ms=1500.0,
            operation="concurrent_test"
        )

    end = time.perf_counter()
    total_ms = (end - start) * 1000

    print(f"\n  Total time for {num_concurrent} calls: {total_ms:.2f} ms")
    print(f"  Average per call: {total_ms / num_concurrent:.2f} ms")
    print(f"  Blocking time per second (at 10 calls/sec): {(total_ms / num_concurrent) * 10:.2f} ms")

    # Clean up
    Path(tracker.storage_path).unlink()

    return {
        "num_calls": num_concurrent,
        "total_ms": total_ms,
        "avg_per_call_ms": total_ms / num_concurrent
    }


def measure_operation_breakdown():
    """Measure the breakdown of operations within record()."""
    print(f"\n{'=' * 60}")
    print(f"Operation Breakdown Analysis")
    print(f"{'=' * 60}")

    tracker = create_test_tracker("medium")

    # Measure read
    start = time.perf_counter()
    data = json.loads(tracker.storage_path.read_text())
    read_time = (time.perf_counter() - start) * 1000

    # Measure JSON parse (already included in read_time, but isolate it)
    json_text = tracker.storage_path.read_text()
    start = time.perf_counter()
    data = json.loads(json_text)
    parse_time = (time.perf_counter() - start) * 1000

    # Measure JSON serialize
    start = time.perf_counter()
    json_str = json.dumps(data, indent=2)
    serialize_time = (time.perf_counter() - start) * 1000

    # Measure write
    start = time.perf_counter()
    tracker.storage_path.write_text(json_str)
    write_time = (time.perf_counter() - start) * 1000

    print(f"\n  File read (read_text):    {read_time:.2f} ms")
    print(f"  JSON parse (loads):        {parse_time:.2f} ms")
    print(f"  JSON serialize (dumps):    {serialize_time:.2f} ms")
    print(f"  File write (write_text):   {write_time:.2f} ms")
    print(f"  {'─' * 40}")
    print(f"  Total (estimated):         {read_time + serialize_time + write_time:.2f} ms")

    # Clean up
    Path(tracker.storage_path).unlink()


def main():
    """Run all benchmarks."""
    print("\n" + "=" * 60)
    print("UsageTracker Performance Benchmark")
    print("Measuring synchronous I/O impact on main thread")
    print("=" * 60)

    # Benchmark different file sizes
    small_results = benchmark_record_performance("small", num_iterations=50)
    print_results(small_results)

    medium_results = benchmark_record_performance("medium", num_iterations=50)
    print_results(medium_results)

    large_results = benchmark_record_performance("large", num_iterations=50)
    print_results(large_results)

    # Benchmark concurrent impact
    concurrent_results = benchmark_concurrent_impact(num_concurrent=10)

    # Operation breakdown
    measure_operation_breakdown()

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print("\nPerformance Impact by File Size:")
    print(f"  Small (~1KB):   {small_results['mean_ms']:.2f} ms avg (p95: {small_results['p95_ms']:.2f} ms)")
    print(f"  Medium (~50KB): {medium_results['mean_ms']:.2f} ms avg (p95: {medium_results['p95_ms']:.2f} ms)")
    print(f"  Large (~500KB): {large_results['mean_ms']:.2f} ms avg (p95: {large_results['p95_ms']:.2f} ms)")

    print(f"\nConcurrent Impact:")
    print(f"  {concurrent_results['num_calls']} rapid calls: {concurrent_results['total_ms']:.2f} ms total")
    print(f"  Average blocking time: {concurrent_results['avg_per_call_ms']:.2f} ms per call")

    print(f"\n{'=' * 60}")
    print("CONCLUSION")
    print(f"{'=' * 60}")

    avg_blocking = medium_results['mean_ms']
    if avg_blocking < 5:
        severity = "LOW"
        impact = "Minimal impact on streaming responses."
    elif avg_blocking < 10:
        severity = "MEDIUM"
        impact = "Noticeable stutter at end of streaming."
    else:
        severity = "HIGH"
        impact = "Significant blocking, visible performance degradation."

    print(f"\nSeverity: {severity}")
    print(f"Average blocking time: {avg_blocking:.2f} ms per API call")
    print(f"Impact: {impact}")
    print(f"\nRecommendation: Implement async write-behind buffer to reduce")
    print(f"blocking time from {avg_blocking:.2f} ms to <1 ms (target).")
    print()


if __name__ == "__main__":
    main()
