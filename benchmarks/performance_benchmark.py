"""
Performance Benchmark for Batch Embedding Generation

This script benchmarks the performance improvement from using batch embeddings
instead of sequential individual embedding API calls.

Compares:
- Old approach: Sequential _generate_embedding calls (n API calls)
- New approach: Single _generate_embeddings_batch call (1 API call)

Measures latency for 10, 50, and 100 items to demonstrate performance gains.
"""

import time
from typing import List
from unittest.mock import MagicMock, Mock


# =============================================================================
# Mock OpenAI API Response Simulation
# =============================================================================

def simulate_openai_api_call(num_items: int = 1, latency_ms: float = 200) -> None:
    """
    Simulate OpenAI API call latency.

    Args:
        num_items: Number of items in the request (affects latency slightly)
        latency_ms: Base latency in milliseconds
    """
    # Base latency + slight increase for batch processing overhead
    total_latency = latency_ms + (num_items * 0.5)  # 0.5ms per item processing
    time.sleep(total_latency / 1000.0)  # Convert to seconds


def mock_generate_embedding_sequential(text: str) -> List[float]:
    """
    Mock sequential embedding generation (old approach).
    Simulates single API call with ~200ms latency.

    Args:
        text: Input text to generate embedding for

    Returns:
        Mock 1536-dimensional embedding vector
    """
    simulate_openai_api_call(num_items=1, latency_ms=200)
    return [0.1] * 1536


def mock_generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Mock batch embedding generation (new approach).
    Simulates single batch API call with ~200ms base latency + processing overhead.

    Args:
        texts: List of input texts to generate embeddings for

    Returns:
        List of mock 1536-dimensional embedding vectors
    """
    simulate_openai_api_call(num_items=len(texts), latency_ms=200)
    return [[0.1] * 1536 for _ in texts]


# =============================================================================
# Benchmark Functions
# =============================================================================

def benchmark_sequential_approach(num_items: int) -> float:
    """
    Benchmark the old sequential approach.

    Args:
        num_items: Number of items to process

    Returns:
        Total latency in milliseconds
    """
    texts = [f"item_{i}" for i in range(num_items)]

    start_time = time.time()

    # Sequential processing: one API call per item
    embeddings = []
    for text in texts:
        embedding = mock_generate_embedding_sequential(text)
        embeddings.append(embedding)

    end_time = time.time()
    latency_ms = (end_time - start_time) * 1000

    return latency_ms


def benchmark_batch_approach(num_items: int) -> float:
    """
    Benchmark the new batch approach.

    Args:
        num_items: Number of items to process

    Returns:
        Total latency in milliseconds
    """
    texts = [f"item_{i}" for i in range(num_items)]

    start_time = time.time()

    # Batch processing: single API call for all items
    embeddings = mock_generate_embeddings_batch(texts)

    end_time = time.time()
    latency_ms = (end_time - start_time) * 1000

    return latency_ms


def run_benchmark_comparison(num_items: int, num_runs: int = 3) -> dict:
    """
    Run benchmark comparison for a given number of items.

    Args:
        num_items: Number of items to process
        num_runs: Number of benchmark runs to average

    Returns:
        Dictionary with benchmark results
    """
    print(f"\n{'='*70}")
    print(f"Benchmarking {num_items} items (averaging {num_runs} runs)")
    print(f"{'='*70}")

    # Run sequential benchmarks
    sequential_latencies = []
    for run in range(num_runs):
        latency = benchmark_sequential_approach(num_items)
        sequential_latencies.append(latency)
        print(f"  Sequential approach - Run {run+1}: {latency:.1f}ms")

    avg_sequential = sum(sequential_latencies) / len(sequential_latencies)

    print()

    # Run batch benchmarks
    batch_latencies = []
    for run in range(num_runs):
        latency = benchmark_batch_approach(num_items)
        batch_latencies.append(latency)
        print(f"  Batch approach - Run {run+1}: {latency:.1f}ms")

    avg_batch = sum(batch_latencies) / len(batch_latencies)

    # Calculate improvements
    latency_reduction = avg_sequential - avg_batch
    reduction_percentage = (latency_reduction / avg_sequential) * 100
    api_calls_before = num_items
    api_calls_after = 1
    api_call_reduction = ((api_calls_before - api_calls_after) / api_calls_before) * 100

    # Display results
    print(f"\n  Results:")
    print(f"  --------")
    print(f"  Sequential (old): {avg_sequential:.1f}ms ({api_calls_before} API calls)")
    print(f"  Batch (new):      {avg_batch:.1f}ms ({api_calls_after} API call)")
    print(f"  Improvement:      {latency_reduction:.1f}ms ({reduction_percentage:.1f}% reduction)")
    print(f"  API calls:        {api_calls_before} → {api_calls_after} ({api_call_reduction:.1f}% reduction)")

    return {
        "num_items": num_items,
        "sequential_ms": avg_sequential,
        "batch_ms": avg_batch,
        "latency_reduction_ms": latency_reduction,
        "latency_reduction_pct": reduction_percentage,
        "api_calls_before": api_calls_before,
        "api_calls_after": api_calls_after,
        "api_call_reduction_pct": api_call_reduction
    }


# =============================================================================
# Main Benchmark Execution
# =============================================================================

def main():
    """
    Run comprehensive performance benchmarks.
    """
    print("\n" + "="*70)
    print("PERFORMANCE BENCHMARK: Batch Embedding Generation")
    print("="*70)
    print("\nThis benchmark compares:")
    print("  • OLD: Sequential _generate_embedding calls (n API calls)")
    print("  • NEW: Single _generate_embeddings_batch call (1 API call)")
    print("\nSimulated API latency: ~200ms per call")
    print("="*70)

    # Run benchmarks for different batch sizes
    batch_sizes = [10, 50, 100]
    results = []

    for size in batch_sizes:
        result = run_benchmark_comparison(size, num_runs=3)
        results.append(result)

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"\n{'Items':<10} {'Sequential':<15} {'Batch':<15} {'Improvement':<20} {'API Calls':<15}")
    print(f"{'-'*10} {'-'*15} {'-'*15} {'-'*20} {'-'*15}")

    for result in results:
        items = result['num_items']
        sequential = f"{result['sequential_ms']:.0f}ms"
        batch = f"{result['batch_ms']:.0f}ms"
        improvement = f"{result['latency_reduction_pct']:.1f}%"
        api_calls = f"{result['api_calls_before']} → {result['api_calls_after']}"

        print(f"{items:<10} {sequential:<15} {batch:<15} {improvement:<20} {api_calls:<15}")

    print(f"\n{'='*70}")
    print("KEY FINDINGS:")
    print(f"{'='*70}")
    for result in results:
        print(f"\n{result['num_items']} items:")
        print(f"  • Latency: {result['sequential_ms']:.0f}ms → {result['batch_ms']:.0f}ms")
        print(f"  • Reduction: {result['latency_reduction_pct']:.1f}%")
        print(f"  • API calls: {result['api_calls_before']} → {result['api_calls_after']}")

    print(f"\n{'='*70}")
    print("CONCLUSION:")
    print(f"{'='*70}")
    print(f"Batch embedding generation provides:")
    print(f"  • {results[0]['latency_reduction_pct']:.0f}%-{results[-1]['latency_reduction_pct']:.0f}% latency reduction")
    print(f"  • {results[0]['api_call_reduction_pct']:.0f}% reduction in API calls")
    print(f"  • Linear scaling: More items = greater absolute time savings")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
