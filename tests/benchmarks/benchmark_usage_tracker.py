#!/usr/bin/env python3
"""
Performance Benchmark: Synchronous vs Async File I/O for UsageTracker

This benchmark compares the performance of the original synchronous file I/O
implementation against the new async write-behind buffer implementation.

Metrics measured:
1. Latency of record() calls (sync vs async)
2. Impact on streaming response simulation
3. Throughput for high-frequency calls
4. I/O operation count

Target: <1ms blocking time for async implementation (vs 5-20ms for sync)
"""

import json
import os
import sys
import time
import statistics
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.litellm_client import UsageTracker, AsyncUsageWriter


class SyncUsageTracker:
    """
    Synchronous version of UsageTracker for baseline comparison.

    This mimics the original blocking implementation before async optimization.
    """

    def __init__(self, storage_path: str, pricing: Dict[str, Dict[str, float]]):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.pricing = pricing
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Initialize storage file if it doesn't exist."""
        if not self.storage_path.exists():
            self.storage_path.write_text(json.dumps({
                "sessions": [],
                "daily_totals": {},
                "model_breakdown": {},
                "provider_breakdown": {},
                "last_updated": datetime.now().isoformat()
            }, indent=2))

    def _get_provider(self, model: str) -> str:
        """Determine provider from model name."""
        if "claude" in model.lower():
            return "anthropic"
        elif "gpt" in model.lower():
            return "openai"
        elif "gemini" in model.lower():
            return "google"
        else:
            return "unknown"

    def record(self, model: str, input_tokens: int, output_tokens: int,
               cost_usd: float, latency_ms: float, operation: str = "chat",
               metadata: Optional[Dict] = None) -> Dict:
        """
        Record a single API call's usage (BLOCKING - synchronous I/O).

        This method performs:
        1. Read entire JSON file from disk
        2. Parse JSON
        3. Update data structure
        4. Serialize JSON
        5. Write entire JSON file to disk

        All operations block the calling thread.
        """
        provider = self._get_provider(model)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "operation": operation,
            "metadata": metadata or {}
        }

        # BLOCKING SYNCHRONOUS I/O
        data = json.loads(self.storage_path.read_text())

        # Update sessions
        data["sessions"].append(entry)
        if len(data["sessions"]) > 1000:
            data["sessions"] = data["sessions"][-1000:]

        # Update daily totals
        date = datetime.fromisoformat(entry["timestamp"]).strftime("%Y-%m-%d")
        if date not in data["daily_totals"]:
            data["daily_totals"][date] = {"tokens": 0, "cost": 0.0, "calls": 0}
        data["daily_totals"][date]["tokens"] += entry["total_tokens"]
        data["daily_totals"][date]["cost"] += entry["cost_usd"]
        data["daily_totals"][date]["calls"] += 1

        # Update model breakdown
        if model not in data["model_breakdown"]:
            data["model_breakdown"][model] = {"tokens": 0, "cost": 0.0, "calls": 0}
        data["model_breakdown"][model]["tokens"] += entry["total_tokens"]
        data["model_breakdown"][model]["cost"] += entry["cost_usd"]
        data["model_breakdown"][model]["calls"] += 1

        # Update provider breakdown
        if provider not in data["provider_breakdown"]:
            data["provider_breakdown"][provider] = {"tokens": 0, "cost": 0.0, "calls": 0}
        data["provider_breakdown"][provider]["tokens"] += entry["total_tokens"]
        data["provider_breakdown"][provider]["cost"] += entry["cost_usd"]
        data["provider_breakdown"][provider]["calls"] += 1

        data["last_updated"] = datetime.now().isoformat()

        # BLOCKING WRITE
        self.storage_path.write_text(json.dumps(data, indent=2))

        return entry


class BenchmarkRunner:
    """Orchestrates all benchmark scenarios and collects results."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pricing = {
            "anthropic/claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gemini-pro": {"input": 0.001, "output": 0.002}
        }
        self.results = {}

    def benchmark_record_latency(self, num_calls: int = 100) -> Dict:
        """
        Benchmark 1: Measure latency of individual record() calls.

        Target: <1ms for async (vs 5-20ms for sync)
        """
        print(f"\n{'='*70}")
        print(f"BENCHMARK 1: record() Latency ({num_calls} calls)")
        print(f"{'='*70}")

        # Sync benchmark
        sync_path = self.output_dir / "sync_latency.json"
        sync_tracker = SyncUsageTracker(str(sync_path), self.pricing)
        sync_times = []

        print("\nMeasuring synchronous record() latency...")
        for i in range(num_calls):
            start = time.perf_counter()
            sync_tracker.record(
                model="anthropic/claude-sonnet-4-5",
                input_tokens=100 + i,
                output_tokens=50 + i,
                cost_usd=0.001,
                latency_ms=100.0
            )
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            sync_times.append(elapsed)

        # Async benchmark
        async_path = self.output_dir / "async_latency.json"
        async_tracker = UsageTracker(str(async_path), self.pricing)
        async_times = []

        print("Measuring asynchronous record() latency...")
        for i in range(num_calls):
            start = time.perf_counter()
            async_tracker.record(
                model="anthropic/claude-sonnet-4-5",
                input_tokens=100 + i,
                output_tokens=50 + i,
                cost_usd=0.001,
                latency_ms=100.0
            )
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            async_times.append(elapsed)

        # Wait for async writes to complete
        async_tracker._async_writer.flush(timeout=10.0)

        # Calculate statistics
        results = {
            "num_calls": num_calls,
            "sync": {
                "mean_ms": statistics.mean(sync_times),
                "median_ms": statistics.median(sync_times),
                "min_ms": min(sync_times),
                "max_ms": max(sync_times),
                "stddev_ms": statistics.stdev(sync_times) if len(sync_times) > 1 else 0,
                "p95_ms": statistics.quantiles(sync_times, n=20)[18] if len(sync_times) >= 20 else max(sync_times),
                "p99_ms": statistics.quantiles(sync_times, n=100)[98] if len(sync_times) >= 100 else max(sync_times),
            },
            "async": {
                "mean_ms": statistics.mean(async_times),
                "median_ms": statistics.median(async_times),
                "min_ms": min(async_times),
                "max_ms": max(async_times),
                "stddev_ms": statistics.stdev(async_times) if len(async_times) > 1 else 0,
                "p95_ms": statistics.quantiles(async_times, n=20)[18] if len(async_times) >= 20 else max(async_times),
                "p99_ms": statistics.quantiles(async_times, n=100)[98] if len(async_times) >= 100 else max(async_times),
            },
            "improvement": {
                "speedup_mean": statistics.mean(sync_times) / statistics.mean(async_times),
                "speedup_median": statistics.median(sync_times) / statistics.median(async_times),
                "speedup_p95": (statistics.quantiles(sync_times, n=20)[18] if len(sync_times) >= 20 else max(sync_times)) /
                               (statistics.quantiles(async_times, n=20)[18] if len(async_times) >= 20 else max(async_times)),
            }
        }

        # Print results
        print(f"\nSynchronous (Blocking I/O):")
        print(f"  Mean:   {results['sync']['mean_ms']:.3f} ms")
        print(f"  Median: {results['sync']['median_ms']:.3f} ms")
        print(f"  Min:    {results['sync']['min_ms']:.3f} ms")
        print(f"  Max:    {results['sync']['max_ms']:.3f} ms")
        print(f"  P95:    {results['sync']['p95_ms']:.3f} ms")
        print(f"  P99:    {results['sync']['p99_ms']:.3f} ms")

        print(f"\nAsynchronous (Write-Behind Buffer):")
        print(f"  Mean:   {results['async']['mean_ms']:.3f} ms")
        print(f"  Median: {results['async']['median_ms']:.3f} ms")
        print(f"  Min:    {results['async']['min_ms']:.3f} ms")
        print(f"  Max:    {results['async']['max_ms']:.3f} ms")
        print(f"  P95:    {results['async']['p95_ms']:.3f} ms")
        print(f"  P99:    {results['async']['p99_ms']:.3f} ms")

        print(f"\nPerformance Improvement:")
        print(f"  Mean speedup:   {results['improvement']['speedup_mean']:.1f}x")
        print(f"  Median speedup: {results['improvement']['speedup_median']:.1f}x")
        print(f"  P95 speedup:    {results['improvement']['speedup_p95']:.1f}x")

        # Check target
        target_met = results['async']['mean_ms'] < 1.0
        print(f"\n✓ Target (<1ms): {'PASS' if target_met else 'FAIL'} ({results['async']['mean_ms']:.3f} ms)")

        return results

    def benchmark_streaming_scenario(self, num_chunks: int = 100) -> Dict:
        """
        Benchmark 2: Simulate streaming response with incremental token updates.

        Measures impact on streaming stuttering.
        """
        print(f"\n{'='*70}")
        print(f"BENCHMARK 2: Streaming Response Simulation ({num_chunks} chunks)")
        print(f"{'='*70}")

        # Sync benchmark
        sync_path = self.output_dir / "sync_streaming.json"
        sync_tracker = SyncUsageTracker(str(sync_path), self.pricing)

        print("\nSimulating streaming with synchronous I/O...")
        sync_start = time.perf_counter()
        sync_stutter_times = []

        for i in range(num_chunks):
            chunk_start = time.perf_counter()
            sync_tracker.record(
                model="anthropic/claude-sonnet-4-5",
                input_tokens=500,  # Fixed input
                output_tokens=i + 1,  # Incremental output
                cost_usd=0.001,
                latency_ms=50.0
            )
            chunk_elapsed = (time.perf_counter() - chunk_start) * 1000
            sync_stutter_times.append(chunk_elapsed)

        sync_total = (time.perf_counter() - sync_start) * 1000

        # Async benchmark
        async_path = self.output_dir / "async_streaming.json"
        async_tracker = UsageTracker(str(async_path), self.pricing)

        print("Simulating streaming with asynchronous I/O...")
        async_start = time.perf_counter()
        async_stutter_times = []

        for i in range(num_chunks):
            chunk_start = time.perf_counter()
            async_tracker.record(
                model="anthropic/claude-sonnet-4-5",
                input_tokens=500,  # Fixed input
                output_tokens=i + 1,  # Incremental output
                cost_usd=0.001,
                latency_ms=50.0
            )
            chunk_elapsed = (time.perf_counter() - chunk_start) * 1000
            async_stutter_times.append(chunk_elapsed)

        async_total = (time.perf_counter() - async_start) * 1000

        # Wait for async writes
        async_tracker._async_writer.flush(timeout=10.0)

        results = {
            "num_chunks": num_chunks,
            "sync": {
                "total_ms": sync_total,
                "mean_chunk_ms": statistics.mean(sync_stutter_times),
                "max_stutter_ms": max(sync_stutter_times),
                "stutters_over_10ms": sum(1 for t in sync_stutter_times if t > 10.0),
            },
            "async": {
                "total_ms": async_total,
                "mean_chunk_ms": statistics.mean(async_stutter_times),
                "max_stutter_ms": max(async_stutter_times),
                "stutters_over_10ms": sum(1 for t in async_stutter_times if t > 10.0),
            },
            "improvement": {
                "speedup_total": sync_total / async_total,
                "speedup_chunk": statistics.mean(sync_stutter_times) / statistics.mean(async_stutter_times),
                "stutter_reduction": sync_total - async_total,
            }
        }

        print(f"\nSynchronous (Blocking I/O):")
        print(f"  Total time:     {results['sync']['total_ms']:.1f} ms")
        print(f"  Per chunk:      {results['sync']['mean_chunk_ms']:.3f} ms")
        print(f"  Max stutter:    {results['sync']['max_stutter_ms']:.3f} ms")
        print(f"  Stutters >10ms: {results['sync']['stutters_over_10ms']}")

        print(f"\nAsynchronous (Write-Behind Buffer):")
        print(f"  Total time:     {results['async']['total_ms']:.1f} ms")
        print(f"  Per chunk:      {results['async']['mean_chunk_ms']:.3f} ms")
        print(f"  Max stutter:    {results['async']['max_stutter_ms']:.3f} ms")
        print(f"  Stutters >10ms: {results['async']['stutters_over_10ms']}")

        print(f"\nPerformance Improvement:")
        print(f"  Total speedup:      {results['improvement']['speedup_total']:.1f}x")
        print(f"  Per-chunk speedup:  {results['improvement']['speedup_chunk']:.1f}x")
        print(f"  Stutter reduction:  {results['improvement']['stutter_reduction']:.1f} ms")

        stutter_eliminated = results['async']['stutters_over_10ms'] == 0
        print(f"\n✓ Stutter elimination: {'PASS' if stutter_eliminated else 'IMPROVED'}")

        return results

    def benchmark_throughput(self, duration_seconds: float = 5.0) -> Dict:
        """
        Benchmark 3: Measure maximum throughput (calls/second).

        Tests how many record() calls can be made in a fixed time period.
        """
        print(f"\n{'='*70}")
        print(f"BENCHMARK 3: Maximum Throughput ({duration_seconds}s test)")
        print(f"{'='*70}")

        # Sync benchmark
        sync_path = self.output_dir / "sync_throughput.json"
        sync_tracker = SyncUsageTracker(str(sync_path), self.pricing)

        print("\nMeasuring synchronous throughput...")
        sync_count = 0
        sync_start = time.perf_counter()

        while (time.perf_counter() - sync_start) < duration_seconds:
            sync_tracker.record(
                model="gpt-4",
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.005,
                latency_ms=200.0
            )
            sync_count += 1

        sync_elapsed = time.perf_counter() - sync_start
        sync_throughput = sync_count / sync_elapsed

        # Async benchmark
        async_path = self.output_dir / "async_throughput.json"
        async_tracker = UsageTracker(str(async_path), self.pricing)

        print("Measuring asynchronous throughput...")
        async_count = 0
        async_start = time.perf_counter()

        while (time.perf_counter() - async_start) < duration_seconds:
            async_tracker.record(
                model="gpt-4",
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.005,
                latency_ms=200.0
            )
            async_count += 1

        async_elapsed = time.perf_counter() - async_start
        async_throughput = async_count / async_elapsed

        # Wait for async writes
        async_tracker._async_writer.flush(timeout=10.0)

        results = {
            "duration_seconds": duration_seconds,
            "sync": {
                "total_calls": sync_count,
                "calls_per_second": sync_throughput,
            },
            "async": {
                "total_calls": async_count,
                "calls_per_second": async_throughput,
            },
            "improvement": {
                "throughput_increase": async_throughput / sync_throughput,
                "additional_calls": async_count - sync_count,
            }
        }

        print(f"\nSynchronous (Blocking I/O):")
        print(f"  Total calls:      {results['sync']['total_calls']:,}")
        print(f"  Calls/second:     {results['sync']['calls_per_second']:.1f}")

        print(f"\nAsynchronous (Write-Behind Buffer):")
        print(f"  Total calls:      {results['async']['total_calls']:,}")
        print(f"  Calls/second:     {results['async']['calls_per_second']:.1f}")

        print(f"\nPerformance Improvement:")
        print(f"  Throughput increase: {results['improvement']['throughput_increase']:.1f}x")
        print(f"  Additional calls:    {results['improvement']['additional_calls']:,}")

        return results

    def benchmark_concurrent_access(self, num_threads: int = 5, calls_per_thread: int = 20) -> Dict:
        """
        Benchmark 4: Concurrent access from multiple threads.

        Tests thread safety and performance under concurrent load.
        """
        print(f"\n{'='*70}")
        print(f"BENCHMARK 4: Concurrent Access ({num_threads} threads x {calls_per_thread} calls)")
        print(f"{'='*70}")

        # Sync benchmark
        sync_path = self.output_dir / "sync_concurrent.json"
        sync_tracker = SyncUsageTracker(str(sync_path), self.pricing)

        def sync_worker(thread_id: int, times: List[float]):
            for i in range(calls_per_thread):
                start = time.perf_counter()
                sync_tracker.record(
                    model="gemini-pro",
                    input_tokens=100 + thread_id,
                    output_tokens=50 + i,
                    cost_usd=0.0002,
                    latency_ms=80.0
                )
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)

        print("\nRunning concurrent sync threads...")
        sync_times = []
        sync_thread_times = [[] for _ in range(num_threads)]
        sync_threads = []
        sync_start = time.perf_counter()

        for i in range(num_threads):
            thread = threading.Thread(target=sync_worker, args=(i, sync_thread_times[i]))
            sync_threads.append(thread)
            thread.start()

        for thread in sync_threads:
            thread.join()

        sync_total = (time.perf_counter() - sync_start) * 1000
        for times in sync_thread_times:
            sync_times.extend(times)

        # Async benchmark
        async_path = self.output_dir / "async_concurrent.json"
        async_tracker = UsageTracker(str(async_path), self.pricing)

        def async_worker(thread_id: int, times: List[float]):
            for i in range(calls_per_thread):
                start = time.perf_counter()
                async_tracker.record(
                    model="gemini-pro",
                    input_tokens=100 + thread_id,
                    output_tokens=50 + i,
                    cost_usd=0.0002,
                    latency_ms=80.0
                )
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)

        print("Running concurrent async threads...")
        async_times = []
        async_thread_times = [[] for _ in range(num_threads)]
        async_threads = []
        async_start = time.perf_counter()

        for i in range(num_threads):
            thread = threading.Thread(target=async_worker, args=(i, async_thread_times[i]))
            async_threads.append(thread)
            thread.start()

        for thread in async_threads:
            thread.join()

        async_total = (time.perf_counter() - async_start) * 1000
        for times in async_thread_times:
            async_times.extend(times)

        # Wait for async writes
        async_tracker._async_writer.flush(timeout=10.0)

        results = {
            "num_threads": num_threads,
            "calls_per_thread": calls_per_thread,
            "total_calls": num_threads * calls_per_thread,
            "sync": {
                "total_time_ms": sync_total,
                "mean_call_ms": statistics.mean(sync_times),
                "max_call_ms": max(sync_times),
            },
            "async": {
                "total_time_ms": async_total,
                "mean_call_ms": statistics.mean(async_times),
                "max_call_ms": max(async_times),
            },
            "improvement": {
                "speedup_total": sync_total / async_total,
                "speedup_mean": statistics.mean(sync_times) / statistics.mean(async_times),
            }
        }

        print(f"\nSynchronous (Blocking I/O):")
        print(f"  Total time:   {results['sync']['total_time_ms']:.1f} ms")
        print(f"  Mean per call: {results['sync']['mean_call_ms']:.3f} ms")
        print(f"  Max call time: {results['sync']['max_call_ms']:.3f} ms")

        print(f"\nAsynchronous (Write-Behind Buffer):")
        print(f"  Total time:    {results['async']['total_time_ms']:.1f} ms")
        print(f"  Mean per call: {results['async']['mean_call_ms']:.3f} ms")
        print(f"  Max call time: {results['async']['max_call_ms']:.3f} ms")

        print(f"\nPerformance Improvement:")
        print(f"  Total speedup:    {results['improvement']['speedup_total']:.1f}x")
        print(f"  Per-call speedup: {results['improvement']['speedup_mean']:.1f}x")

        return results

    def run_all_benchmarks(self):
        """Run all benchmarks and generate summary report."""
        print(f"\n{'#'*70}")
        print("# UsageTracker Performance Benchmark Suite")
        print("# Synchronous vs Asynchronous File I/O")
        print(f"{'#'*70}")

        # Run all benchmarks
        self.results['latency'] = self.benchmark_record_latency(num_calls=100)
        self.results['streaming'] = self.benchmark_streaming_scenario(num_chunks=100)
        self.results['throughput'] = self.benchmark_throughput(duration_seconds=5.0)
        self.results['concurrent'] = self.benchmark_concurrent_access(num_threads=5, calls_per_thread=20)

        # Generate summary report
        self._generate_summary_report()

        # Save results to JSON
        results_file = self.output_dir / "benchmark_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\n✓ Results saved to: {results_file}")

    def _generate_summary_report(self):
        """Generate a summary report of all benchmarks."""
        print(f"\n{'='*70}")
        print("SUMMARY REPORT")
        print(f"{'='*70}")

        print("\n1. Record Latency:")
        print(f"   Sync:  {self.results['latency']['sync']['mean_ms']:.3f} ms (mean)")
        print(f"   Async: {self.results['latency']['async']['mean_ms']:.3f} ms (mean)")
        print(f"   Improvement: {self.results['latency']['improvement']['speedup_mean']:.1f}x faster")

        print("\n2. Streaming Performance:")
        print(f"   Sync:  {self.results['streaming']['sync']['total_ms']:.1f} ms total")
        print(f"   Async: {self.results['streaming']['async']['total_ms']:.1f} ms total")
        print(f"   Improvement: {self.results['streaming']['improvement']['speedup_total']:.1f}x faster")

        print("\n3. Throughput:")
        print(f"   Sync:  {self.results['throughput']['sync']['calls_per_second']:.1f} calls/sec")
        print(f"   Async: {self.results['throughput']['async']['calls_per_second']:.1f} calls/sec")
        print(f"   Improvement: {self.results['throughput']['improvement']['throughput_increase']:.1f}x increase")

        print("\n4. Concurrent Access:")
        print(f"   Sync:  {self.results['concurrent']['sync']['total_time_ms']:.1f} ms total")
        print(f"   Async: {self.results['concurrent']['async']['total_time_ms']:.1f} ms total")
        print(f"   Improvement: {self.results['concurrent']['improvement']['speedup_total']:.1f}x faster")

        # Overall assessment
        print("\n" + "="*70)
        print("OVERALL ASSESSMENT")
        print("="*70)

        target_met = self.results['latency']['async']['mean_ms'] < 1.0
        target_improvement = self.results['latency']['improvement']['speedup_mean']

        print(f"\n✓ Target: <1ms blocking time")
        print(f"  Result: {self.results['latency']['async']['mean_ms']:.3f} ms - {'PASS' if target_met else 'FAIL'}")

        print(f"\n✓ Target: 5-20x performance improvement")
        print(f"  Result: {target_improvement:.1f}x - {'PASS' if target_improvement >= 5 else 'PARTIAL'}")

        print(f"\n✓ Streaming stutter elimination:")
        print(f"  Sync stutters >10ms:  {self.results['streaming']['sync']['stutters_over_10ms']}")
        print(f"  Async stutters >10ms: {self.results['streaming']['async']['stutters_over_10ms']}")
        print(f"  Result: {'PASS' if self.results['streaming']['async']['stutters_over_10ms'] == 0 else 'IMPROVED'}")

        print("\n" + "="*70)


def main():
    """Main entry point for benchmark script."""
    # Create output directory
    output_dir = Path(__file__).parent / "benchmark_output"
    output_dir.mkdir(exist_ok=True)

    # Run benchmarks
    runner = BenchmarkRunner(output_dir)
    runner.run_all_benchmarks()

    print("\n✓ Benchmark suite completed successfully!")


if __name__ == "__main__":
    main()
