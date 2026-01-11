# UsageTracker Performance Benchmarks

This directory contains performance benchmarks comparing synchronous vs asynchronous file I/O for the UsageTracker implementation.

## Overview

The benchmark suite measures the performance improvement achieved by replacing blocking synchronous file I/O with a write-behind async buffer implementation.

### Problem Being Solved

The original `UsageTracker.record()` method performed synchronous JSON file operations on every API call:
1. Read entire JSON file from disk (blocking)
2. Parse JSON (blocking)
3. Update data structure
4. Serialize JSON (blocking)
5. Write entire JSON file to disk (blocking)

This caused 5-20ms blocking time per call, creating visible stuttering during streaming responses.

### Solution

The new `AsyncUsageWriter` implementation:
- Queues records in memory (non-blocking)
- Processes writes in a background thread
- Batches multiple records into single write operations
- Returns from `record()` in <1ms

## Running the Benchmarks

### Quick Start

```bash
# Run all benchmarks
python tests/benchmarks/benchmark_usage_tracker.py
```

### Requirements

- Python 3.8+
- Tools/litellm_client.py (the module being benchmarked)
- No external dependencies required

### Output

The benchmark script will:
1. Run 4 different benchmark scenarios
2. Print detailed results to console
3. Save results to `tests/benchmarks/benchmark_output/benchmark_results.json`

## Benchmark Scenarios

### 1. Record Latency (100 calls)

**What it measures:** Time taken for individual `record()` calls

**Metrics:**
- Mean, median, min, max latency
- P95, P99 percentiles
- Standard deviation

**Target:** <1ms mean latency for async implementation

**Expected improvement:** 5-20x faster

### 2. Streaming Response Simulation (100 chunks)

**What it measures:** Impact on streaming response performance

**Simulates:** Incremental token updates during streaming (like real-time chat)

**Metrics:**
- Total time for all chunks
- Mean time per chunk
- Maximum stutter time
- Number of stutters >10ms

**Target:** Zero stutters >10ms

**Expected improvement:** Eliminate visible stuttering

### 3. Maximum Throughput (5 second test)

**What it measures:** Maximum calls/second achievable

**Metrics:**
- Total calls in time window
- Calls per second
- Throughput increase

**Target:** 2000+ calls/sec for async (vs 50-85 for sync)

**Expected improvement:** 23-40x throughput increase

### 4. Concurrent Access (5 threads × 20 calls)

**What it measures:** Performance under concurrent load from multiple threads

**Metrics:**
- Total time for all threads
- Mean time per call
- Maximum call time

**Target:** Thread-safe with minimal contention

**Expected improvement:** 5-20x faster total time

## Interpreting Results

### Sample Output

```
SUMMARY REPORT
======================================================================

1. Record Latency:
   Sync:  12.456 ms (mean)
   Async: 0.234 ms (mean)
   Improvement: 53.2x faster

2. Streaming Performance:
   Sync:  1245.6 ms total
   Async: 23.4 ms total
   Improvement: 53.2x faster

3. Throughput:
   Sync:  80.3 calls/sec
   Async: 4273.5 calls/sec
   Improvement: 53.2x increase

4. Concurrent Access:
   Sync:  623.4 ms total
   Async: 11.7 ms total
   Improvement: 53.3x faster

OVERALL ASSESSMENT
======================================================================

✓ Target: <1ms blocking time
  Result: 0.234 ms - PASS

✓ Target: 5-20x performance improvement
  Result: 53.2x - PASS

✓ Streaming stutter elimination:
  Sync stutters >10ms:  87
  Async stutters >10ms: 0
  Result: PASS
```

### Success Criteria

The benchmark suite passes if:
- [ ] Async mean latency <1ms
- [ ] Performance improvement ≥5x
- [ ] Async stutters >10ms = 0
- [ ] Async throughput >2000 calls/sec

## Implementation Details

### SyncUsageTracker

A reference implementation mimicking the original blocking behavior for baseline comparison.

### BenchmarkRunner

Orchestrates all benchmark scenarios and collects results.

Key features:
- Separate storage files for each benchmark
- Statistical analysis (mean, median, percentiles)
- Automatic cleanup and result saving
- Thread-safe concurrent testing

## Files Generated

After running benchmarks, the following files are created in `benchmark_output/`:

- `benchmark_results.json` - Complete results in JSON format
- `sync_latency.json` - Sync latency test data
- `async_latency.json` - Async latency test data
- `sync_streaming.json` - Sync streaming test data
- `async_streaming.json` - Async streaming test data
- `sync_throughput.json` - Sync throughput test data
- `async_throughput.json` - Async throughput test data
- `sync_concurrent.json` - Sync concurrent test data
- `async_concurrent.json` - Async concurrent test data

## Customization

You can customize the benchmarks by modifying parameters in `main()`:

```python
# More calls for better statistical accuracy
runner.benchmark_record_latency(num_calls=500)

# Longer streaming simulation
runner.benchmark_streaming_scenario(num_chunks=200)

# Longer throughput test
runner.benchmark_throughput(duration_seconds=10.0)

# More concurrent threads
runner.benchmark_concurrent_access(num_threads=10, calls_per_thread=50)
```

## Performance Baseline

Based on design expectations:

| Metric | Sync (Before) | Async (After) | Improvement |
|--------|---------------|---------------|-------------|
| record() latency | 5-20ms | <1ms | 5-20x |
| Throughput | 50-85 calls/sec | 2000+ calls/sec | 23-40x |
| I/O operations | 100 per 100 calls | 10-20 per 100 calls | 5-10x reduction |
| Streaming stutter | Visible | None | Qualitative |

## Troubleshooting

### Benchmark runs too slowly

This is expected for the sync implementation - that's what we're fixing!

### Results show minimal improvement

Check if your filesystem has very fast I/O (SSD with cache). Try increasing `num_calls` to make the difference more visible.

### Concurrent test fails

Ensure you're not hitting OS thread limits. Try reducing `num_threads`.

### Results not saved

Check write permissions for `tests/benchmarks/benchmark_output/`.

## Related Files

- `Tools/litellm_client.py` - AsyncUsageWriter and UsageTracker implementations
- `.auto-claude/specs/025-*/design.md` - Architecture design document
- `.auto-claude/specs/025-*/implementation_plan.json` - Implementation plan

## Contributing

When adding new benchmarks:
1. Follow the existing pattern in `BenchmarkRunner`
2. Include both sync and async variants
3. Calculate improvement metrics
4. Print detailed results
5. Update this README with the new benchmark description
